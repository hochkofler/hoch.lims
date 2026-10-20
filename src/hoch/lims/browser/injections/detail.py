# -*- coding: utf-8 -*-
"""Step by step detail of the HPLC model calculation of an analysis."""

from bika.lims import api
from hoch.lims import hplcanalysis as ha
from hoch.lims import messageFactory as _
from hoch.lims.browser.injections.view import format_number
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

ORIGINS = {
    ha.PRODUCT: _(u"Product"),
    ha.ASSAY: _(u"Assay of the sample"),
    ha.RUN: _(u"Run data"),
    ha.ANALYSIS: _(u"Other analysis"),
    ha.DERIVED: _(u"Derived"),
}

AGGREGATES = {
    "mean": _(u"Mean (assay)"),
    "uniformity": _(u"Content uniformity (acceptance value)"),
    "dissolution": _(u"Dissolution (per vessel, S1)"),
}


class HPLCDetailView(BrowserView):
    """Detail of the HPLC calculation (``<analysis>/hplc_detail``)
    """
    template = ViewPageTemplateFile("templates/hplc_detail.pt")

    def __call__(self):
        return self.template()

    def get_title(self):
        sample = self.context.getRequest()
        return u"{} · {}".format(api.get_id(sample),
                                 safe_unicode(api.get_title(self.context)))

    def get_sample_url(self):
        return api.get_url(self.context.getRequest())

    def get_injections_url(self):
        from hoch.lims import injections as inj
        source = inj.get_source_analysis(self.context)
        return source and "{}/injections".format(api.get_url(source)) or None

    def get_trace(self):
        return ha.get_trace(self.context) or {}

    def get_model(self):
        return ha.get_model(self.context) or {}

    def num(self, value, decimals=None):
        if isinstance(value, float) and decimals is not None:
            value = round(value, decimals)
        return format_number(value)

    def origin(self, key):
        return ORIGINS.get(key, key)

    def aggregate(self, key):
        return AGGREGATES.get(key, key)

    def get_variables(self):
        trace = self.get_trace()
        items = []
        for name, (value, origin) in sorted((trace.get("variables") or {}).items()):
            items.append({"name": name, "value": value, "origin": origin})
        return items

    def get_derived(self):
        return sorted((self.get_model().get("derived") or {}).items())
