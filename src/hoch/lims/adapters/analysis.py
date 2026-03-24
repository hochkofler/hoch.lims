# -*- coding: utf-8 -*-

from bika.lims import api
from bika.lims.interfaces import IGuardAdapter
from bika.lims.interfaces import IRoutineAnalysis
from zope.component import adapts
from zope.interface import implementer


@implementer(IGuardAdapter)
class AnalysisGuardAdapter(object):
    """Guard adapter for Analysis workflow transitions.

    Validates consumable fields before the 'submit' transition:
    any consumable with allow_empty=False must have a value set.
    """

    adapts(IRoutineAnalysis)

    def __init__(self, context):
        self.context = context

    def guard(self, transition):
        if transition == "submit":
            return self._guard_submit()
        return True

    def _guard_submit(self):
        """Returns False if any required consumable is missing a value."""
        fields = api.get_fields(self.context)
        consumable_field = fields.get("ConsumablesFields")
        if not consumable_field:
            return True

        true_values = ("true", "1", "on", "True", True, 1)
        for consumable in consumable_field.get(self.context):
            if consumable.get("allow_empty", False) in true_values:
                continue
            if not consumable.get("value", ""):
                return False

        return True
