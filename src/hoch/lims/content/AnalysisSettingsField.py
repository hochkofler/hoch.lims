from senaite.core.browser.fields.records import RecordsField
from Products.Archetypes import DisplayList
from hoch.lims import messageFactory as _
from Products.Archetypes.Registry import registerField
from bika.lims.vocabularies import AnalysisServiceVocabulary
from zope import schema
from plone.supermodel import model

class AnalysisSettingsField(RecordsField):
    """Field for storing analysis settings in AnalysisRequest and Analysis.
    """
    _properties = RecordsField._properties.copy()
    _properties.update({
        "fixedSize": 0,
        "minimalSize": 0,
        "maximalSize": 9999,
        "type": "AnalysisSettings",
        "subfields": (
            "analysis",
            "parameter",
            "value"
        ),
        "required_subfields": ("analysis", "parameter", "value"),
        "subfield_labels": {
            "analysis": _("Analysis Keyword"),
            "parameter": _("Parameter"),
            "value": _("Value"),
        },
        "subfield_types": {
            "value": "string",
            "analysis": "selection",
            "parameter": "selection",
        },
        "subfield_sizes": {
            "analysis": 20,
            "parameter": 20,
            "value": 10,
        },
        "subfield_vocabularies": {
            "analysis": AnalysisServiceVocabulary,
            "parameter": DisplayList((
                ("", _("-- Select --")),
                ("concentration", _("Concentration")),
                ("dilution", _("Dilution")),
                ("buffer", _("Buffer")),
                ("ph", _("pH")),
                ("temperature", _("Temperature")),
            )),
        },
    })
    
    def get(self, instance):
        """Get the value of the field from the instance.
        """
        value = instance.getField(self.getName()).getRaw(instance)
        if value is None:
            return {}
        return value
    
registerField(
    AnalysisSettingsField,
    title="Analysis Settings Field",
    description="Used for storing Analysis Settings in Sample Matrix")

class IVariableRow(model.Schema):
    name = schema.TextLine(title=u"Variable name")
    value = schema.Float(title=u"Value")
    unit = schema.TextLine(title=u"Unit", required=False)