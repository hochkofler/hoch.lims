# -*- coding: utf-8 -*-
import collections
from bika.lims import api
from bika.lims.utils import get_link_for
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
            self.portal_url, "senaite_theme/icon/hoch_lims_marketingauthorizations")

        self.title = _("Marketing Authorizations")
        self.description = self.context.Description()
        self.show_select_column = True
        self.pagesize = 25

        self.columns = collections.OrderedDict((
             ("Title", {
                "title": _("Title"),
                "index": "sortable_title",
                "toggle": False}),
            ("Issuing_organization", {
                "title": _("Issuing organization"),
                "index": "mktauth_issuing_organization"}),
            ("Reg_number", {
                "title": _("Registration Number"),
                "index": "mktauth_registration_number"}),
            ("Trade_name", {
                "title": _("Trade Name (Brand)"),
                "index": "mktauth_trade_name"}),
            ("Generic_name", {
                "title": _("Generic name"),
                "index": "mktauth_generic_name"}),
            ("Dosage_form", {
                "title": _("Dosage Form"),
                "index": "mktauth_dosage_form"}),
            ("Product_line", {
                "title": _("Product line"),
                "index": "mktauth_product_line",
                "toggle": False}),
            ("Registered_presentations", {
                "title": _("Presentations"),
                "index": "mktauth_registered_presentations",
                "toggle": False}),
            ("Therapeutic_actions", {
                "title": _("Therapeutic Indications"),
                "index": "mktauth_therapeutic_actions",
                "toggle": False}),
            ("Atq_code", {
                "title": _("A.T.Q. Code"),
                "index": "mktauth_atq_code",
                "toggle": False}),
            ("Medicine_code", {
                "title": _("Medicine clasification"),
                "index": "mktauth_medicine_code",
                "toggle": False}),
            ("Sale_condition", {
                "title": _("Sale Condition"),
                "index": "mktauth_sale_condition",
                "toggle": False}),
            ("Storage_conditions", {
                "title": _("Storage Conditions"),
                "index": "mktauth_storage_conditions",
                "toggle": False}),
            ("Administration_route", {
                "title": _("Route of Administration"),
                "index": "mktauth_administration_route",
                "toggle": False}),
            ("Issue_date", {
                "title": _("Issue Date"),
                "index": "mktauth_issue_date",
                "toggle": False}),
            ("Expiration_date", {
                "title": _("Expiration Date"),
                "index": "mktauth_expiration_date",
                "sortable": True}),
            ("Shelf_life", {
                "title": _("Shelf Life (months)"),
                "index": "mktauth_shelf_life"}),
            ("Holder", {
                "title": _("Marketing Authorization Holder"),
                "index": "mktauth_holder",
                "toggle": False}),
            ("Manufacturer", {
                "title": _("Manufacturer"),
                "index": "mktauth_manufacturer",
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

        item["Title"] = obj.Title()
        item["replace"]["Title"] = get_link_for(obj)
        item["Reg_number"] = obj.getRegistrationNumber()
        item["replace"]["Reg_number"] = get_link(url, value=obj.getRegistrationNumber())
        item["Trade_name"] = obj.getTradeName()
        item["Generic_name"] = obj.getGenericName()
        item["Issuing_organization"] = obj.getIssuingOrganization()
        item["Dosage_form"] = obj.getDosageForm()
        item["Therapeutic_actions"] = ", ".join(obj.getTherapeuticActions())
        item["Atq_code"] = obj.getAtqCode()
        item["Sale_condition"] = obj.getSaleCondition()
        item["Storage_conditions"] = obj.getStorageConditions()
        item["Administration_route"] = obj.getAdministrationRoute()
        item["Issue_date"] = obj.getLocalizedIssueDate()
        item["Expiration_date"] = obj.getLocalizedExpirationDate()
        item["Shelf_life"] = obj.getShelfLife()
        item["Holder"] = obj.getHolder()
        item["Manufacturer"] = obj.getManufacturer()
        item["Description"] = obj.Description()
        item["Registered_presentations"] = obj.getRegisteredPresentations()
        item["Medicine_code"] = obj.getMedicineCode()

        return item
