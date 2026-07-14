# -*- coding: utf-8 -*-
from bika.lims.interfaces import IGuardAdapter
from hoch.lims.workflow.oos import guards
from zope.interface import implementer


@implementer(IGuardAdapter)
class OOSInvestigationGuardAdapter(object):
    """Guard adapter for OOS Investigation workflow transitions."""

    def __init__(self, context):
        self.context = context

    def guard(self, transition):
        """Return False to block the transition, True to allow."""
        func_name = "guard_{}".format(transition)
        func = getattr(guards, func_name, None)
        if func:
            return func(self.context)
        return True
