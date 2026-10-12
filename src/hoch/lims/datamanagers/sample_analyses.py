# -*- coding: utf-8 -*-
"""Sample analyses data manager with Dynamic Calculation support.

senaite.core's data manager adds the dependencies of each service from the
*service* Calculation and removes every analysis that is not in that list.
With Dynamic Calculations an analysis may use another Calculation, with other
dependencies, so this subclass:

1. adds the dependencies of the Calculation each analysis will effectively
   use *before* the base class decides what to remove, so that dependencies
   (and their unsubmitted results) required by a dynamic Calculation are
   never dropped,
2. once the analyses exist, evaluates the rules again with the analyses
   themselves (rules may depend on analysis fields or conditions), links
   them to their dynamic Calculation and adds missing dependencies, and
3. removes the empty dependency analyses no Calculation needs anymore.

It also leaves out the services whose category excludes them for the
sample (see ``hoch.lims.dynamiccalculation.is_excluded``), unless their
analysis already has data, and remembers the services requested for the
primary sample so that excluded ones can come back later.

The analyses of the whole lineage (partitions included) are handled.
When no Calculation declares dynamic rules and no analysis uses a dynamic
Calculation, the result is the same as with the base class.
"""

from bika.lims import api
from bika.lims import logger
from bika.lims.interfaces import ISubmitted
from hoch.lims.dynamiccalculation import MatchContext
from hoch.lims.dynamiccalculation import get_calculation_dependencies
from hoch.lims.dynamiccalculation import get_dynamic_calculations
from hoch.lims.dynamiccalculation import is_excluded
from hoch.lims.dynamiccalculation import resolve_calculation
from hoch.lims.dynamiccalculation import set_requested_services
from senaite.core.datamanagers.field.sample_analyses import DETACHED_STATES
from senaite.core.datamanagers.field.sample_analyses import \
    SampleAnalysesFieldDataManager

# Max number of passes to settle calculations whose rules depend on
# analyses created by a previous pass
MAX_PASSES = 3


def has_data(analysis):
    """Returns whether the analysis has a result or was submitted
    """
    if ISubmitted.providedBy(analysis):
        return True
    return analysis.getResult() not in (None, "")


def is_detached(analysis):
    return api.get_review_status(analysis) in DETACHED_STATES


def get_raw_calculation(obj):
    """Returns the UID of the calculation linked to an analysis or service
    """
    calculation = obj and obj.getCalculation()
    return calculation and api.get_uid(calculation) or ""


def is_resolvable(analysis):
    """Returns whether the calculation of the analysis can still change

    The calculation is frozen once the analysis or any of its dependencies
    has a result, so captured data never changes of calculation.
    """
    if has_data(analysis):
        return False
    return not any(map(has_data, analysis.getDependencies()))


class HochSampleAnalysesFieldDataManager(SampleAnalysesFieldDataManager):
    """Sample analyses data manager aware of Dynamic Calculations
    """

    def set(self, items, prices, specs, hidden, **kw):
        if not isinstance(items, (list, tuple)):
            # let the base class raise the proper error
            return super(HochSampleAnalysesFieldDataManager, self).set(
                items, prices, specs, hidden, **kw)

        # Note that even without dynamic rules the analyses might be linked
        # to a dynamic calculation from a rule that no longer exists, so the
        # dependencies are always resolved from the analyses calculations
        calculations = get_dynamic_calculations()
        services = filter(None, map(self._to_service, items))

        # Remember what was requested for the primary sample, before the
        # category exclusions are applied
        if not self.context.getParentAnalysisRequest():
            set_requested_services(self.context, map(api.get_uid, services))

        # Leave out the services whose category excludes them
        performed = filter(lambda s: not self.is_excluded(s), services)
        if len(performed) != len(services):
            items = map(api.get_uid, performed)
            services = performed
        requested = set(map(api.get_uid, services))

        def base_set(extra):
            return super(HochSampleAnalysesFieldDataManager, self).set(
                list(items) + list(extra), prices, specs, hidden, **kw)

        # 1st pass: service level, analyses might not exist yet
        extra = self.get_needed_dependencies(services, calculations)
        result = base_set(extra)

        # Next passes: evaluate the rules against the analyses
        for i in range(MAX_PASSES):
            self.link_dynamic_calculations(requested, calculations)
            needed = self.get_needed_dependencies(services, calculations)
            missing = self.get_missing(needed)
            if not missing:
                break
            extra = needed
            result = base_set(extra)

        self.remove_unneeded_dependencies(requested, calculations)
        return result

    def is_excluded(self, service):
        """Returns whether the service is not performed in this sample

        Services whose analysis already has data are always performed
        """
        analyses = self.find_analyses(service)
        if any(map(has_data, analyses)):
            return False
        analysis = analyses and analyses[0] or None
        sample = analysis.getRequest() if analysis else self.context
        context = MatchContext(sample, analysis=analysis)
        if not is_excluded(service, context):
            return False
        logger.info("Dynamic category: {} not performed in {}".format(
            service.getKeyword(), api.get_id(self.context)))
        return True

    def get_lineage_analyses(self):
        """Returns the analyses of the sample and its partitions
        """
        analyses = self.context.objectValues("Analysis")
        analyses.extend(self.get_analyses_from_descendants(self.context))
        return filter(lambda an: not is_detached(an), analyses)

    def find_analyses(self, service):
        """Returns the non-detached analyses of the service in the lineage
        """
        analyses = self.get_from_instance(self.context, service)
        analyses.extend(self.get_from_ancestor(self.context, service))
        analyses.extend(self.get_from_descendant(self.context, service))
        return filter(lambda an: not is_detached(an), analyses)

    def get_effective_calculation(self, service, analysis, calculations):
        """Returns the calculation the analysis of the service has to use

        :param analysis: the analysis or None if it does not exist yet
        """
        if analysis is not None and not is_resolvable(analysis):
            return analysis.getCalculation()
        sample = analysis.getRequest() if analysis else self.context
        context = MatchContext(sample, analysis=analysis)
        calculation = resolve_calculation(
            service.getKeyword(), context, calculations=calculations)
        return calculation or service.getCalculation()

    def get_needed_dependencies(self, services, calculations):
        """Returns the dependencies of the effective calculations
        """
        needed = []
        for service in services:
            analyses = self.find_analyses(service) or [None]
            for analysis in analyses:
                calculation = self.get_effective_calculation(
                    service, analysis, calculations)
                needed.extend(get_calculation_dependencies(calculation))
        return needed

    def get_missing(self, services):
        """Returns the services without analysis in the lineage
        """
        return filter(lambda service: not self.find_analyses(service),
                      services)

    def link_dynamic_calculations(self, requested, calculations):
        """Links the requested analyses to their effective calculation
        """
        for analysis in self.get_lineage_analyses():
            if analysis.getServiceUID() not in requested:
                continue
            if not is_resolvable(analysis):
                continue
            service = analysis.getAnalysisService()
            calculation = self.get_effective_calculation(
                service, analysis, calculations)
            uid = calculation and api.get_uid(calculation) or ""
            if get_raw_calculation(analysis) == uid:
                continue
            # Values the analyst already entered for interims
            entered = dict((i.get("keyword"), i.get("value"))
                           for i in analysis.getInterimFields()
                           if i.get("value") not in (None, ""))
            # Start from the service interims, so the interims of the
            # previous calculation do not linger on the analysis
            analysis.setInterimFields(service.getInterimFields())
            analysis.setCalculation(calculation)
            interims = analysis.getInterimFields()
            for interim in interims:
                if interim.get("keyword") in entered:
                    interim["value"] = entered[interim.get("keyword")]
            analysis.setInterimFields(interims)
            analysis.reindexObject()
            logger.info("Dynamic calculation: {} of {} uses '{}'".format(
                analysis.getKeyword(), api.get_id(analysis.getRequest()),
                calculation and api.get_title(calculation) or "-"))

    def remove_unneeded_dependencies(self, requested, calculations):
        """Removes the empty dependency analyses no calculation needs

        Candidates are the dependencies of the dynamic calculations and of the
        service calculations of the analyses. Requested analyses, analyses
        with data and detached analyses are never removed.
        """
        analyses = self.get_lineage_analyses()

        candidates = set()
        for calculation in calculations:
            candidates.update(map(
                api.get_uid, get_calculation_dependencies(calculation)))
        for analysis in analyses:
            service_calc = analysis.getAnalysisService().getCalculation()
            candidates.update(map(
                api.get_uid, get_calculation_dependencies(service_calc)))

        needed = set()
        for analysis in analyses:
            needed.update(map(api.get_uid, get_calculation_dependencies(
                analysis.getCalculation())))

        for analysis in analyses:
            uid = analysis.getServiceUID()
            if uid in requested or uid in needed or uid not in candidates:
                continue
            if has_data(analysis):
                continue
            logger.info("Dynamic calculation: removing unneeded {} from {}"
                        .format(analysis.getKeyword(),
                                api.get_id(analysis.getRequest())))
            self.remove_analysis(analysis)
