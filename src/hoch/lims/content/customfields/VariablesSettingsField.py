# -*- coding: utf-8 -*-
import copy
from AccessControl import ClassSecurityInfo
from hoch.lims import messageFactory as _
from Products.Archetypes import DisplayList
from Products.Archetypes.Registry import registerField
from senaite.core.browser.fields.records import RecordsField
from zope.component import queryAdapter
from hoch.lims.interfaces import IVariablesSettingsVocabularyProvider
from hoch.lims import logger

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
            "keyword": "getVariablesSettingsFieldVocabulary",
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
        vocab = self.getVariablesSettingsFieldVocabulary(instance)
        filled_items = []
        if vocab and isinstance(vocab, DisplayList):
            display_map = dict(vocab.items())
            for record in value:
                keyword = record.get("keyword")
                if keyword in display_map:
                    record["title"] = display_map[keyword]
                    filled_items.append(record)
        if value and not filled_items:
            logger.info("No data to set in variables field, valid kewords are: '%s'", vocab)
        RecordsField.set(self, instance, filled_items, **kwargs)
        
    def getVariablesSettingsFieldVocabulary(self, instance=None, **kwargs):
        if not instance:
            return DisplayList((('', ''),))
        
        provider = queryAdapter(instance, IVariablesSettingsVocabularyProvider)
        if not provider:
            # fallback genérico
            return DisplayList((('', ''), ('notdefined', 'Not Defined')))
        
        return provider.getVocabulary()


registerField(
    VariablesSettingsField,
    title="Variables Settings Record Fields",
    description="Used for storing Variables Settings")
