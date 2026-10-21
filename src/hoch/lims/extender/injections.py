# -*- coding: utf-8 -*-
"""Schema extenders for HPLC injections stored inside an analysis.

Not browser-layer aware on purpose: instrument imports and scripts must see
the fields even without the hoch.lims browser layer.
"""

from archetypes.schemaextender.interfaces import ISchemaExtender
from bika.lims.browser.widgets import RecordsWidget
from bika.lims.interfaces import IAnalysisService
from bika.lims.interfaces import IRoutineAnalysis
from hoch.lims import messageFactory as _
from hoch.lims.content.fields import ExtBooleanFieldAT
from hoch.lims.content.fields import ExtRecordFieldAT
from hoch.lims.injections import COLUMNS
from hoch.lims.injections import INJECTIONS_FIELD
from hoch.lims.injections import RECEIVES_FIELD
from Products.Archetypes.Widget import BooleanWidget
from Products.CMFCore.permissions import View
from senaite.core.permissions import FieldEditAnalysisResult
from zope.component import adapts
from zope.interface import implements


class RoutineAnalysisInjectionsSchemaExtender(object):
    """Adds the Injections table to routine analyses
    """
    implements(ISchemaExtender)
    adapts(IRoutineAnalysis)

    fields = [
        ExtRecordFieldAT(
            INJECTIONS_FIELD,
            read_permission=View,
            write_permission=FieldEditAnalysisResult,
            schemata="Result",
            required=0,
            subfields=COLUMNS,
            subfield_labels={
                "type": _("Type"),
                "number": _("Injection"),
                "conc": _("Conc."),
                "std_conc": _("Std. Conc."),
                "ret_time": _("Ret. time"),
                "area": _("Area"),
                "ntp_usp": _("NTP (USP)"),
                "vial_number": _("Vial"),
                "weight": _("Weight"),
                "acquired": _("Acquired"),
                "sample_name": _("Sample name"),
                "data_file": _("Data file"),
                "peak": _("Peak"),
            },
            widget=RecordsWidget(
                label=_("Injections"),
                visible=False,
            ),
        ),
    ]

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields


class AnalysisServiceInjectionsSchemaExtender(object):
    """Adds the "Receives injections" flag to analysis services
    """
    implements(ISchemaExtender)
    adapts(IAnalysisService)

    fields = [
        ExtBooleanFieldAT(
            RECEIVES_FIELD,
            schemata="Method",
            default=False,
            widget=BooleanWidget(
                label=_("Receives HPLC injections"),
                description=_(
                    "Instrument imports store the injections of the run as "
                    "a table inside this analysis instead of one analysis "
                    "per injection. Other analyses of the same sample, such "
                    "as content uniformity, read the injections from it."),
            ),
        ),
    ]

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields
