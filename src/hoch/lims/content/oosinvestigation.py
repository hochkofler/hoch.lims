# -*- coding: utf-8 -*-
from AccessControl import ClassSecurityInfo
from plone.autoform import directives
from Products.CMFCore import permissions
from plone.supermodel import model
import zope.schema as schema
from hoch.lims import messageFactory as _
from hoch.lims.content.fields import DatetimeField, DatetimeWidget
from senaite.core.content.base import Container
from hoch.lims.interfaces import IOOSInvestigation
from hoch.lims.catalog import HOCHLIMS_CATALOG
from zope.interface import implementer
from bika.lims import api as bika_api


class IOOSInvestigationSchema(model.Schema):
    """OOS Investigation Schema"""

    directives.omitted("title")
    title = schema.TextLine(
        title=u"Title",
        required=False,
    )

    directives.omitted("description")
    description = schema.Text(
        title=u"Description",
        required=False,
    )

    # --- Relationship (single field, all other data derived) ---

    directives.mode(analysis_uid="display")
    analysis_uid = schema.TextLine(
        title=_(
            u"label_oos_analysis_uid",
            default=u"Analysis UID",
        ),
        description=_(
            u"description_oos_analysis_uid",
            default=u"UID of the affected analysis",
        ),
        required=True,
    )

    # --- Snapshots (captured at detection time) ---

    directives.mode(result_value="display")
    result_value = schema.TextLine(
        title=_(
            u"label_oos_result_value",
            default=u"OOS Result Value",
        ),
        description=_(
            u"description_oos_result_value",
            default=u"The result value that was out of specification",
        ),
        required=False,
    )

    directives.mode(specification_range="display")
    specification_range = schema.TextLine(
        title=_(
            u"label_oos_specification_range",
            default=u"Specification Range",
        ),
        description=_(
            u"description_oos_specification_range",
            default=u"The specification range at the time of detection",
        ),
        required=False,
    )

    directives.mode(analysis_service_title="display")
    analysis_service_title = schema.TextLine(
        title=_(
            u"label_oos_analysis_service_title",
            default=u"Analysis Service",
        ),
        description=_(
            u"description_oos_analysis_service_title",
            default=u"The name of the analysis service",
        ),
        required=False,
    )

    # --- Dates ---

    directives.widget("detection_date", DatetimeWidget, show_time=False)
    detection_date = DatetimeField(
        title=_(
            u"label_oos_detection_date",
            default=u"Detection Date",
        ),
        description=_(
            u"description_oos_detection_date",
            default=u"Date when the OOS was first detected",
        ),
        required=True,
    )

    directives.widget("investigation_start_date",
                      DatetimeWidget, show_time=False)
    investigation_start_date = DatetimeField(
        title=_(
            u"label_oos_investigation_start_date",
            default=u"Investigation Start Date",
        ),
        description=_(
            u"description_oos_investigation_start_date",
            default=u"Date when Phase I investigation started",
        ),
        required=False,
    )

    directives.widget("phase2_start_date", DatetimeWidget, show_time=False)
    phase2_start_date = DatetimeField(
        title=_(
            u"label_oos_phase2_start_date",
            default=u"Phase II Start Date",
        ),
        description=_(
            u"description_oos_phase2_start_date",
            default=u"Date when Phase II investigation started",
        ),
        required=False,
    )

    directives.widget("due_date", DatetimeWidget, show_time=False)
    due_date = DatetimeField(
        title=_(
            u"label_oos_due_date",
            default=u"Due Date",
        ),
        description=_(
            u"description_oos_due_date",
            default=u"Investigation due date (30 calendar days per FDA)",
        ),
        required=False,
    )

    directives.widget("completion_date", DatetimeWidget, show_time=False)
    completion_date = DatetimeField(
        title=_(
            u"label_oos_completion_date",
            default=u"Completion Date",
        ),
        description=_(
            u"description_oos_completion_date",
            default=u"Date when investigation was completed",
        ),
        required=False,
    )

    # --- Classification ---

    oos_category = schema.Choice(
        title=_(
            u"label_oos_category",
            default=u"OOS Category",
        ),
        description=_(
            u"description_oos_category",
            default=u"Classification of the OOS result",
        ),
        source="hoch.lims.vocabularies.oos_categories",
        required=False,
    )

    investigation_phase = schema.Choice(
        title=_(
            u"label_oos_investigation_phase",
            default=u"Investigation Phase",
        ),
        description=_(
            u"description_oos_investigation_phase",
            default=u"Current phase of the investigation",
        ),
        source="hoch.lims.vocabularies.oos_investigation_phases",
        required=False,
    )

    root_cause = schema.Choice(
        title=_(
            u"label_oos_root_cause",
            default=u"Root Cause",
        ),
        description=_(
            u"description_oos_root_cause",
            default=u"Identified root cause of the OOS result",
        ),
        source="hoch.lims.vocabularies.oos_root_causes",
        required=False,
    )

    # --- Investigation narrative fields ---

    root_cause_description = schema.Text(
        title=_(
            u"label_oos_root_cause_description",
            default=u"Root Cause Description",
        ),
        description=_(
            u"description_oos_root_cause_description",
            default=u"Detailed description of the root cause analysis",
        ),
        required=False,
    )

    phase1_summary = schema.Text(
        title=_(
            u"label_oos_phase1_summary",
            default=u"Phase I Summary",
        ),
        description=_(
            u"description_oos_phase1_summary",
            default=u"Summary of the Phase I laboratory investigation",
        ),
        required=False,
    )

    capa_description = schema.Text(
        title=_(
            u"label_oos_capa_description",
            default=u"CAPA Description",
        ),
        description=_(
            u"description_oos_capa_description",
            default=u"Corrective and Preventive Actions",
        ),
        required=False,
    )

    impact_assessment = schema.Text(
        title=_(
            u"label_oos_impact_assessment",
            default=u"Impact Assessment",
        ),
        description=_(
            u"description_oos_impact_assessment",
            default=u"Assessment of impact on other batches or products",
        ),
        required=False,
    )

    disposition = schema.Choice(
        title=_(
            u"label_oos_disposition",
            default=u"Disposition",
        ),
        description=_(
            u"description_oos_disposition",
            default=u"Final disposition of the batch",
        ),
        source="hoch.lims.vocabularies.oos_dispositions",
        required=False,
    )

    conclusion = schema.Text(
        title=_(
            u"label_oos_conclusion",
            default=u"Conclusion",
        ),
        description=_(
            u"description_oos_conclusion",
            default=u"Final conclusion of the investigation",
        ),
        required=False,
    )

    # --- People ---

    responsible_analyst = schema.TextLine(
        title=_(
            u"label_oos_responsible_analyst",
            default=u"Responsible Analyst",
        ),
        description=_(
            u"description_oos_responsible_analyst",
            default=u"Analyst who performed the original analysis",
        ),
        required=False,
    )

    investigator = schema.TextLine(
        title=_(
            u"label_oos_investigator",
            default=u"Investigator",
        ),
        description=_(
            u"description_oos_investigator",
            default=u"Person conducting the OOS investigation",
        ),
        required=False,
    )

    reviewer = schema.TextLine(
        title=_(
            u"label_oos_reviewer",
            default=u"Reviewer",
        ),
        description=_(
            u"description_oos_reviewer",
            default=u"QA reviewer who approved or rejected the investigation",
        ),
        required=False,
    )


@implementer(IOOSInvestigation, IOOSInvestigationSchema)
class OOSInvestigation(Container):
    """OOS Investigation content type"""
    _catalogs = [HOCHLIMS_CATALOG]
    security = ClassSecurityInfo()

    # --- Navigation methods (derive data from analysis) ---

    @security.protected(permissions.View)
    def getAnalysis(self):
        """Returns the linked Analysis object"""
        uid = self.getAnalysisUid()
        if uid:
            try:
                return bika_api.get_object_by_uid(uid)
            except Exception:
                return None
        return None

    @security.protected(permissions.View)
    def getSample(self):
        """Returns the Sample (AnalysisRequest) derived from the analysis"""
        analysis = self.getAnalysis()
        if analysis and hasattr(analysis, "getRequest"):
            return analysis.getRequest()
        return None

    @security.protected(permissions.View)
    def getBatch(self):
        """Returns the Batch derived from the sample"""
        sample = self.getSample()
        if sample and hasattr(sample, "getBatch"):
            return sample.getBatch()
        return None

    # --- Title and Description ---

    @security.protected(permissions.View)
    def Title(self):
        return bika_api.safe_unicode(bika_api.get_id(self))

    @security.protected(permissions.View)
    def Description(self):
        service = bika_api.safe_unicode(self.getAnalysisServiceTitle() or u"")
        result = bika_api.safe_unicode(self.getResultValue() or u"")
        batch = self.getBatch()
        batch_id = bika_api.safe_unicode(
            bika_api.get_id(batch)) if batch else u""
        parts = filter(None, [service, result, batch_id])
        return u" - ".join(parts)

    # --- Schema field accessors ---

    @security.protected(permissions.View)
    def getAnalysisUid(self):
        accessor = self.accessor("analysis_uid")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getResultValue(self):
        accessor = self.accessor("result_value")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getSpecificationRange(self):
        accessor = self.accessor("specification_range")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getAnalysisServiceTitle(self):
        accessor = self.accessor("analysis_service_title")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getDetectionDate(self):
        accessor = self.accessor("detection_date")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getInvestigationStartDate(self):
        accessor = self.accessor("investigation_start_date")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getPhase2StartDate(self):
        accessor = self.accessor("phase2_start_date")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getDueDate(self):
        accessor = self.accessor("due_date")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getCompletionDate(self):
        accessor = self.accessor("completion_date")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getOosCategory(self):
        accessor = self.accessor("oos_category")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getInvestigationPhase(self):
        accessor = self.accessor("investigation_phase")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getRootCause(self):
        accessor = self.accessor("root_cause")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getRootCauseDescription(self):
        accessor = self.accessor("root_cause_description")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getPhase1Summary(self):
        accessor = self.accessor("phase1_summary")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getCapaDescription(self):
        accessor = self.accessor("capa_description")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getImpactAssessment(self):
        accessor = self.accessor("impact_assessment")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getDisposition(self):
        accessor = self.accessor("disposition")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getConclusion(self):
        accessor = self.accessor("conclusion")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getResponsibleAnalyst(self):
        accessor = self.accessor("responsible_analyst")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getInvestigator(self):
        accessor = self.accessor("investigator")
        return accessor(self) if accessor else None

    @security.protected(permissions.View)
    def getReviewer(self):
        accessor = self.accessor("reviewer")
        return accessor(self) if accessor else None
