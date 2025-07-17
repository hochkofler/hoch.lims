# -*- coding: utf-8 -*-

from bika.lims import api
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from senaite.app.listing.utils import add_column
from zope.component import adapter
from zope.interface import implementer
from bika.lims.utils import get_link
from hoch.lims import messageFactory as _

ADD_COLUMNS = [
    ("APIURL", {
        "title": _("API URL"),
        "sortable": False,
    }),
    ("ProductionBatchNumber", {
        "title": _("Production batch number"),
        "sortable": False,
    }),
]

@implementer(IListingViewAdapter)
@adapter(IListingView)
class SampleListingViewAdapter(object):

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def before_render(self):
        # Add new column for all available states
        states = map(lambda r: r["id"], self.listing.review_states)
        for column_id, column_values in ADD_COLUMNS:
            add_column(
                listing=self.listing,
                column_id=column_id,
                column_values=column_values,
                review_states=states)

        review_states = [self.listing.review_states[0]]
        for review_state in review_states:
            review_state.update({"columns": self.listing.columns.keys()})

    def folder_item(self, obj, item, index):
        obj = api.get_object(obj)
        uid = api.get_uid(obj)
        portal = api.get_portal()
        portal_url = api.get_url(portal)
        api_url = "{}/@@API/senaite/v1/{}".format(portal_url, uid)
        item["APIURL"] = get_link(api_url, value=api.get_id(obj))
        item["ProductionBatchNumber"] = obj.getProductionBatchNumber()
        return item
