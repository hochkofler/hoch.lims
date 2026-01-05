# -*- coding: utf-8 -*-

from senaite.impress.analysisrequest.reportview import \
    MultiReportView as BaseMultiReportView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile as PT
from bika.lims import api
from senaite.core.api.dtime import to_DT
from hoch.lims.utils import get_formatted_interim
from bika.lims.idserver import generateUniqueId
from hoch.lims import messageFactory as _
from hoch.lims import check_installed, logger
from bika.lims.api import to_float, float_to_string
from bika.lims.api.analysis import is_out_of_range
from bika.lims.config import MAX_OPERATORS
from bika.lims.config import MIN_OPERATORS
from bika.lims.utils import formatDecimalMark
from bika.lims.utils.analysis import _format_decimal_or_sci
import json
import cgi
from collections import OrderedDict
from senaite.core.api import dtime
from senaite.core.i18n import get_dt_format
from senaite.core.i18n import translate as t
from senaite.impress.analysisrequest.reportview import ReportView as view
from senaite.impress.analysisrequest.model import SuperModel

class MultiReportView(BaseMultiReportView):
    """Controller view for multi-reports
    """
    JS_TEMPLATE = PT("templates/js.pt")
    CSS_TEMPLATE = PT("templates/css.pt")
    CONTROLS_TEMPLATE = PT("templates/controls.pt")
    HEADER_TEMPLATE = PT("templates/header.pt")
    INFO_TEMPLATE = PT("templates/info.pt")
    ALERTS_TEMPLATE = PT("templates/alerts.pt")
    SUMMARY_TEMPLATE = PT("templates/summary.pt")
    RESULTS_TEMPLATE = PT("templates/results.pt")
    RESULTS_TRANSPOSED_TEMPLATE = PT("templates/results_transposed.pt")
    INTERPRETATIONS_TEMPLATE = PT("templates/interpretations.pt")
    REMARKS_TEMPLATE = PT("templates/remarks.pt")
    ATTACHMENTS_TEMPLATE = PT("templates/attachments.pt")
    SIGNATURE_TEMPLATE = PT("templates/signatures.pt")
    DISCREETER_TEMPLATE = PT("templates/discreeter.pt")
    FOOTER_TEMPLATE = PT("templates/footer.pt")
    BATCH_DATA_TEMPLATE = PT("templates/batch_data.pt")
    SAMPLE_DATA_TEMPLATE = PT("templates/sample_data.pt")
    INSTRUMENT_DATA_TEMPLATE = PT("templates/instrument_data.pt")
    REFERENCE_SAMPLE_DATA_TEMPLATE = PT("templates/reference_samples_data.pt")
    STERILITY_REPORT_TEMPLATE = PT("templates/sterility_report.pt")
    LAL_REPORT_TEMPLATE = PT("templates/lal_report.pt")
    MICROBIAL_TITRATION_REPORT_TEMPLATE = PT("templates/microbial_titration_report.pt")
    CONCLUSIONS_TEMPLATE = PT("templates/conclusions.pt")

    def __init__(self, context, collection, request):
        super(MultiReportView, self).__init__(collection, request)
        
    def get_coa_number(self):
        kwargs = {"portal_type": "ARReport", "dry_run": True}
        coa_num = generateUniqueId(self.context, **kwargs)
        increment = 0 if int(coa_num.split("-")[-1]) == 1 else 1
        num = "{:05d}".format(int(coa_num.split("-")[-1]) + increment)
        dry_run = coa_num.replace(coa_num.split("-")[-1], num)
        return dry_run

    @property
    def primary_sample(self):
        """Primary sample of the collection
        """
        if len(self.collection) == 0:
            raise ValueError("No reports in collection!")
        return self.collection[0]
    
    def to_date(self, value):
        """Convert a value to a date string
        """
        return to_DT(value)
    
    def render_template(self, context, template_name, **kw):
        """Render a template with the given context and options
        """
        template = PT("templates/%s.pt" % template_name)
        if template is None:
            raise ValueError("Template '%s' not found!" % template_name)
        return template(context, **kw)
    
    def render_batch_data(self, context, **kw):
        """Render the batch data template with the given context and options
        """
        return self.BATCH_DATA_TEMPLATE(context, **kw)
    
    def render_sample_data(self, context, **kw):
        """Render the sample data template with the given context and options
        """
        return self.SAMPLE_DATA_TEMPLATE(context, **kw)
    
    def render_instrument_data(self, context, **kw):
        """Render the instrument data template with the given context and options
        """
        return self.INSTRUMENT_DATA_TEMPLATE(context, **kw)
    
    def render_reference_sample_data(self, context, **kw):
        """Render the reference sample data template with the given context and options
        """
        return self.REFERENCE_SAMPLE_DATA_TEMPLATE(context, **kw)
    
    def render_sterility_report(self, context, **kw):
        """Render the sterility report template with the given context and options
        """
        return self.STERILITY_REPORT_TEMPLATE(context, **kw)
    
    def render_lal_report(self, context, **kw):
        """Render the lal report template"""
        return self.LAL_REPORT_TEMPLATE(context, **kw)
    
    def render_microbial_titration_report(self, context, **kw):
        """Render microbial titration report"""
        return self.MICROBIAL_TITRATION_REPORT_TEMPLATE(context, **kw)
    
    def render_conclusions(self, context, **kw):
        """Render the conclusions template with the given context and options
        """
        return self.CONCLUSIONS_TEMPLATE(context, **kw)

    def formatted_interim(self, interim, dmk="."):
        return get_formatted_interim(interim, dmk)

    def get_decimal_mark(self):
        """Returns the decimal mark
        """
        setup = api.get_setup()
        return setup.getDecimalMark()
        
    def getFormattedResultForService(self, analyses, specs=None, decimalmark='.', sciformat=1, html=True, is_max_date=True):
        """
        Evaluates a set of analyses for the same analysis service and provides:
        - Formatted results
        - Final result interpretation
        - Out-of-range evaluation

        Rules:
        0. If analyses are not from the same service, return None.
        1. If the result type is string/text → concat unique results.
        2. If the result type has choices → concat results and interpretation=True 
        only if ALL results belong to the valid specification options.
        3. If the result type is date → return max or min date (based on is_max_date).
        4. If the result type is numeric (floatable):
            - All or mean < LDL → "<LDL"
            - All or mean > UDL → ">UDL"
            - Otherwise → formatted mean numeric value.
        5. Out-of-range interpretation is False if ANY result is out of shoulder.

        Returns:
            dict with keys:
                results,interpretations, result_types, formatted_results,
                result, interpretation
        """

        result_dict = {}

        # Collect raw results, result types and pre-formatted values
        results = [a.getResult() for a in analyses]
        result_types = [a.getResultType() for a in analyses]
        out_of_range_flags = [is_out_of_range(a) for a in analyses]
        formatted_results = [a.getFormattedResult(specs=a.getResultsRange(), decimalmark=decimalmark,sciformat=sciformat, html=html) for a in analyses]

        result_dict["results"] = results
        result_dict["result_types"] = result_types
        result_dict["interpretations"] = [(not x, not y) for (x, y) in out_of_range_flags]
        result_dict["formatted_results"] = formatted_results

        # Default interpretation: True only if all in range
        interpretation = all(not(flag[0]) for flag in out_of_range_flags), all(not(flag[1]) for flag in out_of_range_flags)

        # Case 1: String / Text
        if all(rt in ["string", "text"] for rt in result_types):
            result_dict["result"] = ",".join(set(formatted_results))
            result_dict["interpretation"] = interpretation
            result_dict["mean_interpretation"] = interpretation
            return result_dict

        # Case 2: Choices (select, multiselect, multiselect_duplicates, multichoice)
        if all(rt in ["select", "multiselect", "multiselect_duplicates", "multichoice"] for rt in result_types):
            concat = ",".join(set(formatted_results))
            # Validate all results against the allowed options (from ResultRange)
            result_dict["result"] = concat
            result_dict["interpretation"] = interpretation
            result_dict["mean_interpretation"] = interpretation
            return result_dict

        # Case 3: Date
        if all(rt == "date" for rt in result_types):
            dates = [r for r in results if r]
            if not dates:
                result_dict["result"] = None
                result_dict["interpretation"] = (False, False)
                result_dict["mean_interpretation"] = (False, False)
            else:
                result_dict["result"] = max(dates) if is_max_date else min(dates)
                result_dict["interpretation"] = (True, True)
                result_dict["mean_interpretation"] = (True, True)
            return result_dict

        # Case 4: Numeric (floatable)
        try:
            numeric_results = [float(r) for r in results if r is not None]
        except Exception:
            numeric_results = []

        if numeric_results:
            mean_value = sum(numeric_results) / len(numeric_results)
            result_dict["interpretation"] = interpretation

            # Get detection/spec limits from first valid analysis
            analysis = next((a for a in analyses if a is not None), None)
            
            result_dict["mean_interpretation"] =tuple(not x for x in is_out_of_range(analysis, result=mean_value))
            ldl = analysis.getLowerDetectionLimit() if hasattr(analysis, "getLowerDetectionLimit") else None
            udl = analysis.getUpperDetectionLimit() if hasattr(analysis, "getUpperDetectionLimit") else None
            spec = specs if specs else analysis.getResultsRange()

            # Spec limits and flags
            min_value = spec.get("min") if spec else None
            max_value = spec.get("max") if spec else None
            hidemin = spec.get("hidemin", False) if spec else False
            hidemax = spec.get("hidemax", False) if spec else False
            
            
            try:
                belowmin = hidemin and mean_value < float(hidemin) or False
            except (TypeError, ValueError):
                belowmin = False
            try:
                abovemax = hidemax and mean_value > float(hidemax) or False
            except (TypeError, ValueError):
                abovemax = False
                
            # If below min and hidemin enabled, return '<min'
            if belowmin:
                fdm = formatDecimalMark('< %s' % hidemin, decimalmark)
                result_dict["result"] = fdm.replace('< ', '&lt; ', 1) if html else fdm
                return result_dict
            # If above max and hidemax enabled, return '>max'
            if abovemax:
                fdm = formatDecimalMark('> %s' % hidemax, decimalmark)
                result_dict["result"] = fdm.replace('> ', '&gt; ', 1) if html else fdm
                return result_dict
            
            # Lower Limits of Detection and Quantification (LLOD and LLOQ)
            llod = to_float(analysis.getLowerDetectionLimit())
            lloq = to_float(analysis.getLowerLimitOfQuantification())
            if mean_value < llod:
                if llod != lloq:
                    # Display "Not detected"
                    result_str = t(_("result_below_llod", default="Not detected"))
                    result_dict["result"] = cgi.escape(result_str) if html else result_str
                    return result_dict

                # Display < LLOD
                ldl = float_to_string(llod)
                result_str = formatDecimalMark("< %s" % ldl, decimalmark)
                result_dict["result"] = cgi.escape(result_str) if html else result_str
                return result_dict

            if mean_value < lloq:
                lloq = float_to_string(lloq)
                lloq = formatDecimalMark(lloq, decimalmark)
                result_str = t(_("result_below_lloq", default="Detected but < ${LLOQ}",
                            mapping={"LLOQ": lloq}))
                result_dict["result"] = cgi.escape(result_str) if html else result_str
                return result_dict

            # Upper Limit of Quantification (ULOQ)
            uloq = to_float(analysis.getUpperLimitOfQuantification())
            if mean_value > uloq:
                uloq = float_to_string(uloq)
                result_str = formatDecimalMark('> %s' % uloq, decimalmark)
                result_dict["result"] = cgi.escape(result_str) if html else result_str
                return result_dict

            # Render numerical values
            threshold = analysis.getExponentialFormatPrecision()
            precision = analysis.getPrecision()
            mean_formatted = _format_decimal_or_sci(mean_value, precision, threshold, sciformat)
            mean_str_with_decimal = formatDecimalMark(mean_formatted, decimalmark)
            result_dict["result"] = mean_str_with_decimal
            return result_dict

        # Fallback: just return unique formatted results
        result_dict["result"] = ",".join(set(formatted_results))
        result_dict["interpretation"] = interpretation
        result_dict["mean_interpretation"] = interpretation
        
        return result_dict
        
    def getFormattedResultForServices(
        self,
        hidden=False,
        retracted=False,
        rejected=False,
        specs=None,
        decimalmark=".",
        sciformat=1,
        html=True,
        is_max_date=True,
    ):
        """Groups analyses by category and then by service, formatting
        the results with our custom getFormattedResultForService.
        """

        analyses = self.get_analyses_by(
            model_or_collection=self.collection,
            hidden=hidden,
            retracted=retracted,
            rejected=rejected,
        )
        logger.info("Formatting results for %d analyses." % len(analyses))
        logger.info("analyses are:'%s'", analyses)
        analysis_by_category_and_service = OrderedDict()
        
        categories = self.group_items_by("Category", analyses)
        logger.info("categories are: '%s'", categories)
        for category in categories:
            services = self.group_items_by('AnalysisService',categories[category])
            analysis_by_category_and_service[category] = OrderedDict()
            for service in services:
                    formatted = self.getFormattedResultForService(
                        analyses=services[service], decimalmark=decimalmark, specs=specs, sciformat=sciformat, html=html, is_max_date=is_max_date
                    )
                    analysis_by_category_and_service[category][service] = {}
                    analysis_by_category_and_service[category][service]["analyses"] = services[service]
                    analysis_by_category_and_service[category][service]["results_formatted"] = formatted

        logger.info("analysis by category: '%s'", analysis_by_category_and_service)
        return analysis_by_category_and_service

    def generateId(self):
        import uuid
        return uuid.uuid4()

    def get_formatted_specs(self, analysis, with_shoulder_range=False,
                            lt_operator=None, leq_operator=None, 
                            gt_operator=None, geq_operator=None):
        specs = analysis.getResultsRange()

        # Get possible choice options (for choice-type results)
        choices = analysis.getResultOptions()
        values_texts = {}
        if choices:
            # Map: ResultValue -> ResultText (both as strings for easier comparison)
            values_texts = dict(map(
                lambda c: (str(c["ResultValue"]), c["ResultText"]),
                choices
            ))

        result_type = analysis.getResultType()
        is_choice_type = result_type in [
            "select", "multiselect", "multiselect_duplicates", "multichoice"
        ]
        
        OPERATORS = {}
        OPERATORS["gt"] = gt_operator or MAX_OPERATORS.getValue("gt", ">")
        OPERATORS["geq"] = geq_operator or MAX_OPERATORS.getValue("geq", ">=")
        OPERATORS["lt"] = lt_operator or MIN_OPERATORS.getValue("lt", "<")
        OPERATORS["leq"] = leq_operator or MIN_OPERATORS.getValue("leq", "<=")
        # Get min and max operators (default values if missing)
        min_operator = specs.get("min_operator") or ""
        min_operator = OPERATORS.get(min_operator, ">=")
        max_operator = specs.get("max_operator") or ""
        max_operator = OPERATORS.get(max_operator, "<=")

        # Helper function to evaluate the operator condition
        def matches_operator(value, limit, operator):
            value = float(value)
            limit = float(limit)
            if operator == OPERATORS["geq"]:
                return value >= limit
            elif operator == OPERATORS["gt"]:
                return value > limit
            elif operator == OPERATORS["leq"]:
                return value <= limit
            elif operator == OPERATORS["lt"]:
                return value < limit
            elif operator == "==":
                return value == limit
            elif operator == "!=":
                return value != limit
            return False

        specs_min = specs.get("min")
        specs_max = specs.get("max")
        # --- If it's a choice type, filter by range and return the matching texts ---
        if with_shoulder_range:
            specs_min = specs.get("warn_min")
            specs_max = specs.get("warn_max")
        
        valid_min_specs = specs_min or specs_min == "0" or specs_min == 0
        valid_max_specs = specs_max or specs_max == "0" or specs_max == 0
        
        if (is_choice_type or values_texts) and (valid_min_specs or valid_max_specs):
            filtered_texts = []
            for num, text in values_texts.items():
                if (not valid_min_specs or matches_operator(num, specs_min, min_operator)) and \
                (not valid_max_specs or matches_operator(num, specs_max, max_operator)):
                    filtered_texts.append(text)

            # Optional: if all choices are included, return a single label
            # if len(filtered_texts) == len(values_texts):
            #     return "All"

            return ", ".join(filtered_texts)

        # --- Default numeric range case ---
        fs = ""
        threshold = analysis.getExponentialFormatPrecision()
        precision = analysis.getPrecision()
        formated_max = ""
        formated_min = ""
        if specs_min:
            formated_min = _format_decimal_or_sci(specs_min, precision, threshold, 1)
        
        if specs_max:
            formated_max = _format_decimal_or_sci(specs_max, precision, threshold, 1)
        if specs_min and specs_max:
            fs = "%s - %s" % (formated_min, formated_max)
        elif specs_min:
            fs = "%s %s" % (min_operator, formated_min)
        elif specs_max:
            fs = "%s %s" % (max_operator, formated_max)

        return formatDecimalMark(fs, self.get_decimal_mark())

class SingleReportView(MultiReportView):
    """Controller view for single-reports
    """
    def __init__(self, context, model, request):
        super(SingleReportView, self).__init__(context, [model], request)
