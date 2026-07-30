# -*- coding: utf-8 -*-

"""HOCH-specific analysis edit modal compatibility."""

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.core.browser.modals.analysis.form import EditAnalysisForm


class HochEditAnalysisForm(EditAnalysisForm):
    """Analysis modal with controls for time-valued results."""

    template = ViewPageTemplateFile("templates/edit_analysis.pt")

    def _synchronize_time_interims(self):
        """Copy visible time controls to the fields persisted by SENAITE."""
        form = self.request.form
        for interim in self.analysis.getInterimFields() or []:
            if interim.get("result_type") != "time":
                continue
            keyword = interim.get("keyword")
            visible_name = "{}-time".format(keyword)
            if keyword and visible_name in form:
                form[keyword] = form.get(visible_name, "")

    def handle_submit(self):
        self._synchronize_time_interims()
        return super(HochEditAnalysisForm, self).handle_submit()
