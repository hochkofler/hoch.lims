# -*- coding: utf-8 -*-

from archetypes.schemaextender.interfaces import IBrowserLayerAwareExtender
from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from bika.lims.interfaces import IAnalysisRequest
from Products.Archetypes.Widget import IntegerWidget
from Products.CMFCore.permissions import View, ModifyPortalContent
from bika.lims.browser.widgets import SelectionWidget as BikaSelectionWidget
from senaite.core.permissions import FieldEditSampleType
from zope.component import adapts
from zope.interface import implements
from hoch.lims import messageFactory as _
from hoch.lims.content.fields import ExtIntegerFieldAT, ExtStringFieldAT
from hoch.lims.interfaces import IHochLims
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory
from Products.Archetypes.public import DisplayList

def getDestinations(self):
    factory = getUtility(
        IVocabularyFactory,
        name='hoch.lims.vocabularies.destinations'
    )
    vocab = factory(self.context)

    pairs = [(t.value, t.title) for t in vocab]
    return DisplayList(pairs)

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
        
        ExtStringFieldAT(
            "Destination",
            mode="rw",
            read_permission=View,
            write_permission=FieldEditSampleType,
            default='ipc',
            vocabulary='getDestinationsVocabulary',
            widget=BikaSelectionWidget(
                format='select',
                label=_("Destination"),
                description=_("Destination"),
                visible={
                    "add": "edit",
                    'header_table': 'prominent',
                    "secondary": "disabled",
                },
                render_own_label=True,
            ),
        ),

        ExtStringFieldAT(
            "Processes",
            mode="rw",
            read_permission=View,
            write_permission=FieldEditSampleType,
            vocabulary='getProcessesVocabulary',
            widget=BikaSelectionWidget(
                format='select',
                multipleSelection=True,
                label=_("Processes"),
                description=_("Selected processes for this sample"),
                visible={
                    "add": "edit",
                    'header_table': 'prominent',
                    "secondary": "disabled",
                },
                render_own_label=True,
            ),
        )

    ]

    def __init__(self, context):
        self.context = context

    def getProcessesVocabulary(self):
        """Return the processes for the linked product's process group"""
        batch = self.context.getBatch()
        if not batch:
            return DisplayList()

        product = batch.getProduct()
        if not product:
            return DisplayList()

        process_group = product.getProcessGroup()
        if not process_group:
            return DisplayList()

        processes = process_group.getProcesses()
        pairs = [(p, p) for p in processes]
        return DisplayList(pairs)

    def getFields(self):
        return self.fields

    def getOrder(self, original):
        """Change the order of the extended fields
        """
        # get the fields of the default schemata
        default = original["default"]

        base_index = default.index("SubGroup")
        # remove any existing field
        default.remove("SampleType")
        default.remove("SampledUnits")
        default.remove("Destination")
        default.remove("Processes")
        # add the field below the reference index
        default.insert(base_index + 1, "Destination")
        default.insert(base_index + 2, "Processes")
        default.insert(base_index + 3, "SampleType")
        default.insert(base_index + 4, "SampledUnits")

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