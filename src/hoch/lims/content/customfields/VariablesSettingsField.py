# -*- coding: utf-8 -*-
import copy
from AccessControl import ClassSecurityInfo
from hoch.lims import messageFactory as _
from Products.Archetypes import DisplayList
from Products.Archetypes.Registry import registerField
from senaite.core.browser.fields.records import RecordsField

class VariablesSettingsField(RecordsField):
    """a list of VariablesSettingsField for calculations """
    _properties = RecordsField._properties.copy()
    _properties.update({
        "fixedSize": 0,
        "minimalSize": 0,
        "maximalSize": 10,
        "type": "VariablesSettingsField",
        "subfields": (
            "keyword",
            "value",
            "unit",
        ),
        "required_subfields": ("keyword", "value"),
        "subfield_labels": {
            "keyword": _("Keyword"),
            "value": _("Value"),
            "unit": _("Unit"),
        },

        "subfield_types": {
            "value": "string",
        },
        
        "subfield_validators": {
            "keyword": "VariablesSettingsFieldsValidator",
            "value": "VariablesSettingsFieldsValidator",
            "unit": "VariablesSettingsFieldsValidator",
        },
        
        "subfield_sizes": {
            "keyword": 1,
            "value": 10,
            "unit": 10,
        },
        "subfield_vocabularies": {
            "keyword": DisplayList((
                    ('', ''),
                    ('concentration', _('Concentration')),
                    ('sensitivity', _('Sensitivity')),
                    ('other', _('Other')),
                )),
        },
    })
    security = ClassSecurityInfo()

    def get(self, instance, **kwargs):
        value = super(VariablesSettingsField, self).get(instance, **kwargs)
        if value is None:
            return []
        return copy.deepcopy(value)

    def set(self, instance, value, **kwargs):
        """Override setter to auto-fill title/unit"""
        vocab = self._properties.get("subfield_vocabularies", {}).get("keyword", None)
        if vocab and isinstance(vocab, DisplayList):
            display_map = dict(vocab.items())
            for record in value:
                keyword = record.get("keyword")
                if keyword in display_map:
                    record["title"] = display_map[keyword]
        RecordsField.set(self, instance, value, **kwargs)


registerField(
    VariablesSettingsField,
    title="Variables Settings Record Fields",
    description="Used for storing Variables Settings")
