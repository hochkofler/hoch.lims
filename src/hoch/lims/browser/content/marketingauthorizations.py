import collections
from bika.lims import api
from bika.lims.utils import get_email_link
from bika.lims.utils import get_image
from bika.lims.utils import get_link
from senaite.app.listing.view import ListingView
from hoch.lims import messageFactory as _
#from senaite.patient.api import to_identifier_type_name
#from senaite.patient.api import tuplify_identifiers
from hoch.lims.catalog import HOCHLIMS_CATALOG
#from senaite.patient.i18n import translate as t
from hoch.lims.permissions import AddMarketingAuthorization


class MarketingAuthorizationsView(ListingView):
    """Global Folder View
    """

    def __init__(self, context, request):
        super(MarketingAuthorizationsView, self).__init__(context, request)

        self.catalog = HOCHLIMS_CATALOG

        self.contentFilter = {
            "portal_type": "MarketingAuthorization",
            "sort_on": "created",
            "sort_order": "descending",
        }

        self.context_actions = {
            _("Add"): {
                "url": "++add++MarketingAuthorization",
                "permission": AddMarketingAuthorization,
                "icon": "++resource++bika.lims.images/add.png"}
            }

        self.icon = "{}/{}".format(
            self.portal_url, "senaite_theme/icon/marketingauthorizations")

        self.title = _("Marketing Authorizations")
        self.description = self.context.Description()
        self.show_select_column = True
        self.pagesize = 25

        self.columns = collections.OrderedDict((
            # ("Title", {
            #     "title": _("Title"),
            #     "index": "sortable_title"}),
            ("Description", {
                "title": _("Description"),
                }),
            # ("Reg_number", {
            #     "title": _("Registration Number"),
            #     "index": "mktauth_reg_number"}),
            # ("Expiration_date", {
            #     "title": _("Expiration Date"),
            #     "index": "mktauth_expiration_date",
            #     "sortable": True}),
        ))

        self.review_states = [
            {
                "id": "default",
                "title": _("Active"),
                "contentFilter": {"is_active": True},
                "columns": self.columns.keys(),
            }, {
                "id": "inactive",
                "title": _("Inactive"),
                "contentFilter": {'is_active': False},
                "columns": self.columns.keys(),
            }, {
                "id": "all",
                "title": _("All"),
                "contentFilter": {},
                "columns": self.columns.keys(),
            },
        ]

    def update(self):
        """Update hook
        """
        super(MarketingAuthorizationsView, self).update()

    def before_render(self):
        """Before template render hook
        """
        super(MarketingAuthorizationsView, self).before_render()

    def to_utf8(self, s):
        """Ensure UTF8 encoded string
        """
        return api.safe_unicode(s).encode("utf8")

    def folderitem(self, obj, item, index):
        obj = api.get_object(obj)
        url = api.get_url(obj)

        #item["Title"] = obj.Title()
        #item["replace"]["Title"] = get_link_for(obj)

        #item["Reg_number"] = obj.getRegNumber()
        #item["replace"]["Reg_number"] = get_link_for(obj)
        item["Description"] = obj.Description()
        #item["Expiration_date"] = obj.getLocalizedExpirationDate()

        return item
    
    def get_item_info(self, item):
        """Safe handling of missing values"""
        item_info = super(MarketingAuthorizationsView, self).get_item_info(item)
        
        # Handle missing values safely
        for key in item_info:
            if item_info[key] is None or api.is_missing_value(item_info[key]):
                item_info[key] = "Error"  # Convert to empty string
        
        return item_info
