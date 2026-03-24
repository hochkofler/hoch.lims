# -*- coding: utf-8 -*-
import copy

from AccessControl import ClassSecurityInfo
from bika.lims import api
from bika.lims import bikaMessageFactory as _
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.interfaces import IAnalysis
from Products.Archetypes.public import DisplayList
from Products.Archetypes.Registry import registerField
from senaite.core.browser.fields.records import RecordsField


class ConsumableFieldsField(RecordsField):
    """Field for configuring and storing consumable fields on services and analyses"""
    _properties = RecordsField._properties.copy()
    _properties.update({
        "fixedSize": 0,
        "minimalSize": 0,
        "maximalSize": 9999,
        "type": "ConsumableFields",
        "subfields": (
            "keyword",
            "allow_empty",
        ),
        "subfield_labels": {
            "keyword": _("Keyword"),
            "allow_empty": _("Allow empty"),
        },
        "subfield_types": {
            "keyword": "string",
            "allow_empty": "boolean",
        },
        "subfield_sizes": {
            "keyword": 1,
        },
        "subfield_vocabularies": {
            "keyword": "_consumables_vocabulary",
        },
    })
    security = ClassSecurityInfo()

    def get(self, instance, **kwargs):
        consumables = RecordsField.get(self, instance, **kwargs) or []
        return copy.deepcopy(consumables)

    def set(self, instance, value, **kwargs):
        # When setting consumables on a routine analysis, sync missing
        # entries from the service definition (field access, no method call)
        if IAnalysis.providedBy(instance):
            service = instance.getAnalysisService()
            if service:
                service_field = service.getField("ConsumablesFields")
                if service_field:
                    service_consumables = service_field.get(service) or []
                    existing_keys = [v.get("keyword") for v in value]
                    for entry in service_consumables:
                        if entry.get("keyword") not in existing_keys:
                            value.append(entry)

        RecordsField.set(self, instance, value, **kwargs)

    def query_available_consumables(self):
        """Return all active ReferenceDefinition brains"""
        catalog = api.get_tool(SETUP_CATALOG)
        query = {
            "portal_type": "ReferenceDefinition",
            "is_active": True,
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }
        return catalog(query)

    def _consumables_vocabulary(self, *args, **kwargs):
        """Vocabulary for the keyword subfield — looked up on the field instance"""
        consumables = self.query_available_consumables()
        items = [("", _(""))] + [(api.get_uid(i), api.get_title(i)) for i in consumables]
        return DisplayList(items)


registerField(
    ConsumableFieldsField,
    title="Consumable Fields",
    description="Used for storing consumable field definitions and analysis results")
