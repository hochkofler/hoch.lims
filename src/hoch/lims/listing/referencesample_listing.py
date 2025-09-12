# -*- coding: utf-8 -*-

from bika.lims import api
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from senaite.app.listing.utils import add_column
from bika.lims.browser.referencesample import ReferenceSamplesView
from zope.component import adapter
from zope.interface import implementer
from bika.lims.utils import get_link
from hoch.lims import messageFactory as _
from hoch.lims import logger
from zope.interface import providedBy

ADD_COLUMNS = [
    ("Concentration", {
        "title": _("Concentration"),
        "sortable": True,
    }),
    ("Sensitivity", {
        "title": _("Sensitivity"),
        "sortable": True,
    }),
]

@implementer(IListingViewAdapter)
@adapter(ReferenceSamplesView)
class ReferenceSampleListingViewAdapter(object):

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def before_render(self):
        # Add new column for all available states
        logger.info(">>> before_render called for ReferenceSampleListingViewAdapter")
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
        concentration = getattr(obj, "Concentration", "")
        sensitivity = getattr(obj, "Sensitivity", "")
        concentration_unit = getattr(obj, "ConcentrationUnit", "")
        sensitivity_unit = getattr(obj, "SensitivityUnit", "")
        item["Concentration"] = str(concentration) + " " + concentration_unit if concentration else "-"
        item["Sensitivity"] = str(sensitivity) + " " + sensitivity_unit if sensitivity else "-"
        return item