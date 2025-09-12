from archetypes.schemaextender.interfaces import IBrowserLayerAwareExtender
from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from zope.component import adapts
from zope.interface import implements
from bika.lims.interfaces import IReferenceSample
from hoch.lims.content.fields import ExtFloatFieldAT, ExtStringFieldAT
from hoch.lims.interfaces import IHochLims
from Products.Archetypes.Widget import StringWidget
from Products.Archetypes.Widget import DecimalWidget
from hoch.lims import messageFactory as _
from hoch.lims import logger

class ReferenceSampleSchemaExtender(object):
    """Extend Schema Fields for Reference Sample content type."""
    layer = IHochLims
    implements(
        ISchemaExtender,
        IBrowserLayerAwareExtender,
        IOrderableSchemaExtender)
    adapts(IReferenceSample)
    
    fields = [
        ExtFloatFieldAT(
            "Concentration",
            schemata = 'Description',
            required=0,
            widget=DecimalWidget(
              label=_(
                u"label_referencesample_concentration",
                default=u"Concentration",),  
            ),
        ),
        ExtStringFieldAT(
            "ConcentrationUnit",
            schemata = 'Description',
            required=0,
            widget=StringWidget(
              label=_(
                u"label_referencesample_concentrationunit",
                default=u"Concentration Unit",),  
            ),
        ),
        ExtFloatFieldAT(
            "Sensitivity",
            schemata = 'Description',
            required=0,
            widget=DecimalWidget(
              label=_(
                u"label_referencesample_sensitivity",
                default=u"Sensitivity",),  
            ),
        ),
        ExtStringFieldAT(
            "SensitivityUnit",
            schemata = 'Description',
            required=0,
            widget=StringWidget(
              label=_(
                u"label_referencesample_sensitivityunit",
                default=u"Sensitivity Unit",),  
            ),
        ),
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

        # move  Order Number 
        index = default.index("ReferenceDefinitionUID")
        # remove any existing field
        if "Concentration" in default:
            default.remove("Concentration")
        # add the field below the reference index
        default.insert(index - 1, "Concentration")

        return original

class ReferenceSampleSchemaModifier(object):
    """Modify Reference Sample Schema Fields
    """
    layer = IHochLims
    implements(
        ISchemaModifier,
        IBrowserLayerAwareExtender)
    adapts(IReferenceSample)

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        # Make the profiles field required
        # profiles = schema.get("Profiles")
        # profiles.required = True

        return schema