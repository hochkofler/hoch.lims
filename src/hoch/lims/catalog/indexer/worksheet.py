# -*- coding: utf-8 -*-

from bika.lims import api
from bika.lims.interfaces import IListingSearchableTextProvider
from senaite.core.interfaces import IWorksheet
from senaite.core.interfaces import IWorksheetCatalog
from zope.interface import implementer


@implementer(IListingSearchableTextProvider)
class WorksheetSamplesSearchableText(object):
    """Provides sample IDs and client sample IDs for worksheet full-text search
    """

    def __init__(self, context, request, catalog):
        self.context = context
        self.request = request
        self.catalog = catalog

    def __call__(self):
        tokens = []
        seen = set()
        for analysis in self.context.getRegularAnalyses():
            uid = api.safe_getattr(analysis, "getRequestUID", None)
            if callable(uid):
                uid = uid()
            if not uid or uid in seen:
                continue
            seen.add(uid)
            sample = api.get_object_by_uid(uid, default=None)
            if not sample:
                continue
            sample_id = api.get_id(sample)
            if sample_id:
                tokens.append(sample_id)
            client_sample_id = api.safe_getattr(sample, "getClientSampleID", None)
            if callable(client_sample_id):
                client_sample_id = client_sample_id()
            if client_sample_id:
                tokens.append(client_sample_id)
        return list(set(tokens))
