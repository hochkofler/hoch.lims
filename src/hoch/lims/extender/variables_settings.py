# -*- coding: utf-8 -*-
from archetypes.schemaextender.interfaces import IBrowserLayerAwareExtender
from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from zope.component import adapts
from zope.interface import implements
from hoch.lims.interfaces import IHochLims
from hoch.lims import messageFactory as _
from bika.lims.browser.widgets.recordswidget import RecordsWidget
from hoch.lims.content.fields import ExtVariablesSettingsFieldAT
from bika.lims.interfaces import IInstrument, IReferenceSample

class VariablesSettingsSchemaExtender(object):
    """Extend Schema Fields for Reference Sample content type."""
    layer = IHochLims
    implements(
        ISchemaExtender,
        IBrowserLayerAwareExtender,
        IOrderableSchemaExtender)
    adapts(IReferenceSample, IInstrument)
    
    fields = [
        ExtVariablesSettingsFieldAT(
            "VariablesSettings",
            schemata=_("Variables"),
            required=0,
            subfield_vocabularies={
                "keyword": "getVariablesSettingsFieldVocabulary",
            },
            widget=RecordsWidget(
                label=_("Extra Variable Fields"),
                description=_("Extra variable fields that can be used."),
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
        return original

class VariablesSettingsSchemaModifier(object):
    """Modify Reference Sample Schema Fields
    """
    layer = IHochLims
    implements(
        ISchemaModifier,
        IBrowserLayerAwareExtender)
    adapts(IReferenceSample, IInstrument)

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        # Make the profiles field required
        # profiles = schema.get("Profiles")
        # profiles.required = True

        return schema