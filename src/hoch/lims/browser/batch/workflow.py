# -*- coding: utf-8 -*-

from Products.Five.browser import BrowserView
from hoch.lims.workflow.batch import events


class BatchAfterRelease(BrowserView):
    """After-script handler for batch release transition"""
    
    def __call__(self):
        """Execute after release actions"""
        events.after_release(self.context)
        return "OK"
