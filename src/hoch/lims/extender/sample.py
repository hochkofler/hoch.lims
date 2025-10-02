# -*- coding: utf-8 -*-

from archetypes.schemaextender.interfaces import IBrowserLayerAwareExtender
from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from bika.lims.interfaces import IAnalysisRequest
from Products.Archetypes.Widget import IntegerWidget
from Products.CMFCore.permissions import View
from zope.component import adapts
from zope.interface import implements
from hoch.lims import messageFactory as _
from hoch.lims.content.fields import ExtIntegerFieldAT
from hoch.lims.interfaces import IHochLims


class SampleSchemaExtender(object):
    """Extend Schema Fields for Samples
    """
    layer = IHochLims
    implements(
        ISchemaExtender,
        IBrowserLayerAwareExtender,
        IOrderableSchemaExtender)
    adapts(IAnalysisRequest)

    fields = [
        ExtIntegerFieldAT(
            "SampledUnits",
            mode="rw",
            read_permission=View,
            required=1,
            default=1,
            widget=IntegerWidget(
                label=_("Sampled Units"),
                visible={
                    "add": "edit",
                },
                description=_("Number of units sampled"),
                render_own_label=True,
                i18n_domain="hoch.lims",
            )),
    ]

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields

    def getOrder(self, original):
        """Change the order of the extended fields
        """
        # get the fields of the default schemata
        default = original["default"]

        # move  Order Number before Batch
        index = default.index("SampleType")
        # remove any existing field
        default.remove("SampledUnits")
        # add the field below the reference index
        default.insert(index + 1, "SampledUnits")

        return original


class SampleSchemaModifier(object):
    """Modify Sample Schema Fields
    """
    layer = IHochLims
    implements(
        ISchemaModifier,
        IBrowserLayerAwareExtender)
    adapts(IAnalysisRequest)

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        sample_point = schema.get("SamplePoint")
        sample_point.required = 1
        specification = schema.get("Specification")
        specification.required = True
        return schema