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
from bika.lims.utils import safe_unicode


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

        self.title = self.context.translate(_("Marketing authorizations"))
        self.description = self.context.Description()
        self.show_select_column = True
        self.pagesize = 25

        self.columns = collections.OrderedDict((
             ("Title", {
                "title": _(u"label_marketingauthorization_title",
                            default=u"Title"),
                "index": "sortable_title",
                "toggle": False}),
            ("Issuing_organization", {
                "title": _(
                    u"label_marketingauthorization_issuing_organization",
                    default=u"Issuing Regulatory Authority",
                ),
                "index": "mktauth_issuing_organization"}),
            ("Reg_number", {
                "title": _(
                    u"label_marketingauthorization_registration_number",
                    default=u"Marketing Authorization Number",
                ),
                "index": "mktauth_registration_number"}),
            ("Trade_name", {
                "title": _(
                    u"label_marketingauthorization_trade_name",
                    default=u"Trade Name (Brand)",
                ),
                "index": "mktauth_trade_name",
                "searchable":True,}),
            ("Generic_name", {
                "title": _(
                    "label_marketingauthorization_generic_name",
                    default=u"Generic Name",
                ),
                "index": "mktauth_generic_name",
                "searchable":True,}),
            ("Dosage_form", {
                "title": _(
                    u"label_marketingauthorization_dosage_form",
                    default=u"Dosage Form",
                ),
                "index": "mktauth_dosage_form"}),
            ("Product_line", {
                "title": _(
                    u"label_marketingauthorization_product_line",
                    default=u"Product Line",
                ),
                "index": "mktauth_product_line",
                "toggle": False}),
            ("Registered_presentations", {
                "title": _(
                    u"label_marketingauthorization_registered_presentations",
                    default=u"Registered Presentations"
                ),
                "index": "mktauth_registered_presentations",
                "toggle": False}),
            ("Therapeutic_actions", {
                "title": _(
                    u"label_marketingauthorization_therapeutic_actions",
                    default=u"Therapeutic Indications",
                ),
                "index": "mktauth_therapeutic_actions",
                "toggle": False}),
            ("Atq_code", {
                "title": _(
                    u"label_marketingauthorization_atq_code",
                    default=u"A.T.Q. Code",
                ),
                "index": "mktauth_atq_code",
                "toggle": False}),
            ("Medicine_code", {
                "title": _(
                    u"label_marketingauthorization_medicine_code",
                    default=u"Medicine Code",
                ),
                "index": "mktauth_medicine_code",
                "toggle": False}),
            ("Sale_condition", {
                "title": _(
                    u"label_marketingauthorization_sale_condition",
                    default=u"Sale Condition",
                ),
                "index": "mktauth_sale_condition",
                "toggle": False}),
            ("Storage_conditions", {
                "title": _(
                    u"label_marketingauthorization_storage_conditions",
                    default=u"Storage Conditions",
                ),
                "index": "mktauth_storage_conditions",
                "toggle": False}),
            ("Administration_route", {
                "title": _(
                    u"label_marketingauthorization_administration_route",
                    default=u"Route of Administration",
                ),
                "index": "mktauth_administration_route",
                "toggle": False}),
            ("Issue_date", {
                "title": _(
                    u"label_marketingauthorization_issue_date",
                    default=u"Issue Date",
                ),
                "index": "mktauth_issue_date",
                "toggle": False}),
            ("Expiration_date", {
                "title": _(
                    u"label_marketingauthorization_expiration_date",
                    default=u"Expiration Date",
                ),
                "index": "mktauth_expiration_date",
                "sortable": True}),
            ("Shelf_life", {
                "title": _(
                    u"label_marketingauthorization_shelf_life",
                    default=u"Shelf Life (months)",
                ),
                "index": "mktauth_shelf_life"}),
            ("Holder", {
                "title": _(
                    u"label_marketingauthorization_holder",
                    default=u"Marketing Authorization Holder",
                ),
                "index": "mktauth_holder",
                "toggle": False}),
            ("Manufacturer", {
                "title": _(
                    u"label_marketingauthorization_manufacturer",
                    default=u"Manufacturer",
                ),
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
        bid = api.get_id(obj)
        title = safe_unicode(obj.Title())
        item["Title"] = safe_unicode(obj.Title())
        #item["replace"]["Title"] = get_link(url, value = bid)
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
