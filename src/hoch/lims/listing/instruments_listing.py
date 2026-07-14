# -*- coding: utf-8 -*-
from DateTime import DateTime
from bika.lims.controlpanel.bika_instruments import InstrumentsView
from bika.lims.interfaces import IInstruments
from hoch.lims import messageFactory as _
from senaite.app.listing.interfaces import IListingViewAdapter
from zope.component import adapter
from zope.interface import implementer


@implementer(IListingViewAdapter)
@adapter(InstrumentsView, IInstruments)
class InstrumentsListingViewAdapter(object):

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def before_render(self):
        today = DateTime()
        soon = today + 30

        expired_filter = {
            "query": today,
            "range": "max",
        }
        expiring_filter = {
            "query": [today, soon],
            "range": "min:max",
        }

        self.listing.review_states.extend([
            {
                "id": "expiring_soon",
                "title": _("Expiring Soon"),
                "contentFilter": dict(
                    portal_type="Instrument",
                    is_active=True,
                    instrument_certificate_expiry_date=expiring_filter,
                    sort_on="sortable_title",
                    sort_order="ascending",
                ),
                "transitions": [{"id": "deactivate"}],
                "columns": self.listing.columns.keys(),
            },
            {
                "id": "expired",
                "title": _("Expired"),
                "contentFilter": dict(
                    portal_type="Instrument",
                    is_active=True,
                    instrument_certificate_expiry_date=expired_filter,
                    sort_on="sortable_title",
                    sort_order="ascending",
                ),
                "transitions": [{"id": "deactivate"}],
                "columns": self.listing.columns.keys(),
            },
        ])

    def folder_item(self, obj, item, index):
        return item
