# -*- coding: utf-8 -*-
import collections
from bika.lims import api
from bika.lims.utils import get_link_for
from bika.lims.utils import get_link
from senaite.app.listing.view import ListingView
from hoch.lims import messageFactory as _
from hoch.lims.catalog import HOCHLIMS_CATALOG
#from senaite.patient.i18n import translate as t
from hoch.lims.permissions import AddMarketingAuthorization
from bika.lims.utils import safe_unicode

class PharmaceuticalProductsView(ListingView):
    """Global Folder View
    """

    def __init__(self, context, request):
        super(PharmaceuticalProductsView, self).__init__(context, request)

        self.catalog = HOCHLIMS_CATALOG

        self.contentFilter = {
            "portal_type": "PharmaceuticalProduct",
            "sort_on": "created",
            "sort_order": "descending",
        }

        self.context_actions = {
            _("Add"): {
                "url": "++add++PharmaceuticalProduct",
                "permission": AddMarketingAuthorization,
                "icon": "++resource++bika.lims.images/add.png"}
            }

        self.icon = "{}/{}".format(
            self.portal_url, "senaite_theme/icon/hoch_lims_product")

        self.title = self.context.translate(_("Products"))
        self.description = self.context.Description()
        self.show_select_column = True
        self.pagesize = 25

        self.columns = collections.OrderedDict((
             ("Code", {
                "title": _(u"label_product_code",
                            default=u"Code"),
                "index": "sortable_title",
                "toggle": True}),
            ("Name", {
                "title": _(u"label_product_name",
                            default=u"Name"),
                "index": "sortable_title",
                "toggle": True}),

            ("MarketingAuthorization", {
                "title": _(u"label_product_marketingauthorization",
                            default=u"Marketing Authorization"),
                "toggle": True}),

            ("DosageForm", {
                "title": _(u"label_product_dosageform",
                            default=u"Dosage form"),
                "toggle": True}),
            ("APIURL", {
                "title": _(u"label_product_api",
                            default=u"API URL"),
                "toggle": True}),
            ("Title", {
                "title": _(u"label_product_title",
                            default=u"Title"),
                "index": "sortable_title",
                "toggle": False}),
            ("Description", {
                "title": _(u"label_product_description",
                            default=u"Description"),
                "toggle": False}),
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
            }, 
            {
                "id": "all",
                "title": _("All"),
                "contentFilter": {},
                "columns": self.columns.keys(),
            },
        ]

    def update(self):
        """Update hook
        """
        super(PharmaceuticalProductsView, self).update()

    def before_render(self):
        """Before template render hook
        """
        super(PharmaceuticalProductsView, self).before_render()

    def to_utf8(self, s):
        """Ensure UTF8 encoded string
        """
        return api.safe_unicode(s).encode("utf8")

    def folderitem(self, obj, item, index):
        obj = api.get_object(obj)
        uid = api.get_uid(obj)
        url = api.get_url(obj)
        portal = api.get_portal()
        portal_url = api.get_url(portal)
        api_url = "{}/@@API/senaite/v1/{}".format(portal_url, uid)
        item["APIURL"] = get_link(api_url, value=api.get_id(obj))
        item["Code"] = obj.getCode()
        item["replace"]["Code"] = get_link(url, value=obj.getCode())
        item["Name"] = obj.getName()
        reg = api.get_object(obj.getMarketingAuthorization())
        item["MarketingAuthorization"] = obj.getMarketingAuthorization()
        reg_url = api.get_url(reg)
        reg_num = reg.getRegistrationNumber()
        item["replace"]["MarketingAuthorization"] = get_link(reg_url, value=api.safe_unicode(reg_num))
        item["DosageForm"] = reg.getDosageForm()
        item["Reg"] = reg_num
        item["Title"] = safe_unicode(obj.Title())
        item["Description"] = safe_unicode(obj.Description())
        return item
