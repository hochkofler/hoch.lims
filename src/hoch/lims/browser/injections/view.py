# -*- coding: utf-8 -*-
"""View and correct the HPLC injections stored in an analysis."""

from bika.lims import api
from bika.lims.api.security import check_permission
from bika.lims.interfaces import ISubmitted
from hoch.lims import messageFactory as _
from hoch.lims import injections as inj
from plone.protect import CheckAuthenticator
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from senaite.core.permissions import FieldEditAnalysisResult

# Editable columns, in display order
EDITABLE = ("type", "number", "conc", "ret_time", "area", "ntp_usp",
            "vial_number")


class InjectionsView(BrowserView):
    """Injections table of an analysis (``<analysis>/injections``)
    """
    template = ViewPageTemplateFile("templates/injections.pt")

    def __call__(self):
        form = self.request.form
        if form.get("form.button.save"):
            CheckAuthenticator(self.request)
            if not self.can_edit():
                return self.redirect(
                    _("You are not allowed to change these injections"),
                    "error")
            self.save(self.get_form_rows())
            return self.redirect(_("Injections saved and results recalculated"))
        return self.template()

    @property
    def analysis(self):
        return self.context

    def get_title(self):
        sample = self.analysis.getRequest()
        return u"{} · {}".format(api.get_id(sample),
                                 safe_unicode(api.get_title(self.analysis)))

    def get_sample_url(self):
        return api.get_url(self.analysis.getRequest())

    def receives_injections(self):
        return inj.receives_injections(self.analysis)

    def can_edit(self):
        if ISubmitted.providedBy(self.analysis):
            return False
        if not self.receives_injections():
            return False
        return check_permission(FieldEditAnalysisResult, self.analysis)

    def get_rows(self):
        return inj.sort_rows(inj.get_injections(self.analysis))

    def get_columns(self):
        return EDITABLE

    def get_summary(self):
        rows = self.get_rows()
        unk = len([r for r in rows if r.get("type") == inj.SAMPLE])
        st = len([r for r in rows if r.get("type") == inj.STANDARD])
        return {"unk": unk, "st": st}

    def format_value(self, value):
        if value is None:
            return u""
        if isinstance(value, float):
            return u"{:g}".format(value)
        return safe_unicode(value)

    def get_form_rows(self):
        """Returns the rows posted by the form, without the deleted ones
        """
        form = self.request.form
        count = int(form.get("count", 0) or 0)
        existing = self.get_rows()
        rows = []
        for index in range(count):
            prefix = "row-{}-".format(index)
            if form.get(prefix + "delete"):
                continue
            row = {}
            # keep the columns that are not editable (acquisition, file...)
            if index < len(existing):
                row.update(existing[index])
            for column in EDITABLE:
                row[column] = form.get(prefix + column, u"")
            if not row.get("number"):
                continue
            rows.append(row)
        return rows

    def save(self, rows):
        inj.set_injections(self.analysis, rows)
        inj.recalculate(self.analysis.getRequest())
        self.analysis.reindexObject()

    def redirect(self, message, level="info"):
        IStatusMessage(self.request).addStatusMessage(message, level)
        url = "{}/injections".format(api.get_url(self.analysis))
        return self.request.response.redirect(url)
