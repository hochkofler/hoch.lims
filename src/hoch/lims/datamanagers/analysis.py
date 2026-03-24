# -*- coding: utf-8 -*-
"""Custom data manager for RoutineAnalysis that handles consumable fields.

Registers as an adapter for IRoutineAnalysis, overriding senaite.core's
RoutineAnalysisDataManager to add consumables support without modifying core.
"""

import copy
import json

from bika.lims import api
from bika.lims.interfaces import IRoutineAnalysis
from senaite.core.datamanagers.content.analysis import RoutineAnalysisDataManager
from senaite.core.interfaces.datamanager import IDataManager
from six import string_types
from zope.component import adapter
from zope.interface import implementer


@adapter(IRoutineAnalysis)
@implementer(IDataManager)
class HochRoutineAnalysisDataManager(RoutineAnalysisDataManager):
    """Extends RoutineAnalysisDataManager to support consumable fields.

    Consumables are identified by keyword and stored via the ConsumablesFields
    schema field (added by schemaextender). Field access is used directly
    instead of calling methods on the content object.
    """

    def _get_consumable_field(self):
        """Returns the ConsumablesFields schema field or None."""
        return api.get_fields(self.context).get("ConsumablesFields")

    def _get_consumables(self):
        """Returns the current consumables list from the field."""
        field = self._get_consumable_field()
        if field is None:
            return []
        return field.get(self.context) or []

    def _get_consumable_keywords(self):
        return [c.get("keyword") for c in self._get_consumables()]

    def _set_consumable_value(self, keyword, value):
        """Stores a value for a consumable keyword."""
        if value is None:
            value = ""
        elif isinstance(value, string_types):
            value = value.strip()
        elif isinstance(value, (list, tuple, set, dict)):
            value = json.dumps(value)

        consumables = copy.deepcopy(self._get_consumables())
        for consumable in consumables:
            if consumable.get("keyword") == keyword:
                consumable["value"] = str(value)

        field = self._get_consumable_field()
        if field is not None:
            field.set(self.context, consumables)

    def set(self, name, value):
        """Set analysis field, interim or consumable value."""
        consumable_keys = self._get_consumable_keywords()

        if name in consumable_keys:
            consumable_field = self._get_consumable_field()
            if not self.is_field_writeable(consumable_field):
                return []
            self._set_consumable_value(name, value)
            return [self.context]

        return super(HochRoutineAnalysisDataManager, self).set(name, value)
