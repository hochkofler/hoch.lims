# -*- coding: utf-8 -*-

from bika.lims.interfaces import IBatch
from bika.lims.interfaces import IGuardAdapter
from hoch.lims.workflow.batch import guards
from zope.interface import implementer


@implementer(IGuardAdapter)
class BatchGuardAdapter(object):
    """Guard adapter for Batch workflow transitions.
    
    This adapter is consulted by SENAITE's guard_handler before
    looking up guard functions in modules. It receives the Batch
    object directly as context, avoiding Acquisition context issues.
    """

    def __init__(self, context):
        self.context = context

    def guard(self, transition):
        """Return False to block the transition, True/None to allow.
        
        Only blocks transitions that have explicit guard logic.
        Returns None (not False) for transitions without specific guards,
        allowing the default behavior.
        """
        if transition == "release":
            return guards.guard_release(self.context)
        # For other transitions, return True (allow)
        return True
