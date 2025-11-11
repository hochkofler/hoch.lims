# -*- coding: utf-8 -*-

from bika.lims import api
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from senaite.app.listing.utils import add_column
from zope.component import queryAdapter
from hoch.lims.interfaces import IVariablesSettingsVocabularyProvider
from zope.component import adapter
from zope.interface import implementer
from hoch.lims import messageFactory as _
from hoch.lims import logger
from Products.Archetypes import DisplayList

@implementer(IListingViewAdapter)
@adapter(IListingView)
class VariablesSettingsListingsViewAdapter(object):

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context
        provider = queryAdapter(context, IVariablesSettingsVocabularyProvider)
        vocab_terms = provider.getVocabulary() if provider else DisplayList((('', '')))
        self.ADD_COLUMNS = [
            (key, {"title": title,
                   "sortable": True})
            for key, title in vocab_terms.items()
            if key  # omitimos las vacías
        ]
        # self.ADD_COLUMNS = [
        #     (term[0], {"title": term[1], "sortable": False}) for term in vocab_terms
        # ]

    def before_render(self):
        # Add new column for all available states
        logger.info(">>> before_render called for ReferenceSampleListingViewAdapter")
        states = map(lambda r: r["id"], self.listing.review_states)
        
        for column_id, column_values in self.ADD_COLUMNS:
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
        variables_settings = getattr(obj, "VariablesSettings", []) or []

        # Convierte lista de records a diccionario: {keyword: "value unit"}
        variables_settings_dict = {
            s.get("keyword"): "{} {}".format(s.get("value", ""), s.get("unit", "")).strip()
            for s in variables_settings if s.get("keyword")
        }

        for column_id, _ in self.ADD_COLUMNS:
            item[column_id] = variables_settings_dict.get(column_id, "-")

        return item