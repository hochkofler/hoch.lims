from App.class_init import InitializeClass
from senaite.core.catalog.base_catalog import COLUMNS as BASE_COLUMNS
from senaite.core.catalog.base_catalog import INDEXES as BASE_INDEXES
from senaite.core.catalog.base_catalog import BaseCatalog
from hoch.lims.interfaces import IHochLimsCatalog
from zope.interface import implementer

CATALOG_ID = "hochlims_catalog_marketingauthorization"
CATALOG_TITLE = "HochLims Marketing Authorization Catalog"

INDEXES = BASE_INDEXES + [
    # id, indexed attribute, type
    ("mktauth_registration_number", "", "FieldIndex"),
    ("mktauth_expiration_date", "", "DateIndex"),
    ("mktauth_holder", "", "FieldIndex"),
    ("mktauth_trade_name", "", "FieldIndex"),
    ("mktauth_issuing_organization", "", "FieldIndex"),
    ("mktauth_dosage_form", "", "FieldIndex"),
    ("mktauth_therapeutic_actions", "", "KeywordIndex"),
    ("mktauth_atq_code", "", "FieldIndex"),
    ("mktauth_sale_condition", "", "FieldIndex"),
    ("mktauth_administration_route", "", "FieldIndex"),
    ("mktauth_medicine_code", "", "FieldIndex"),
    ("mktauth_product_line", "", "FieldIndex"),
    ("mktauth_storage_conditions", "", "FieldIndex"),
    ("mktauth_issue_date", "", "DateIndex"),
    ("mktauth_manufacturer", "", "FieldIndex"),
    ("mktauth_shelf_life", "", "FieldIndex"),
    ("mktauth_abbreviated_registration", "", "FieldIndex"),
    ("mktauth_generic_name", "", "FieldIndex"),
    ("mktauth_registered_presentations", "", "FieldIndex"),
    ("mktauth_searchable_text", "", "ZCTextIndex"),
]

COLUMNS = BASE_COLUMNS + [
    # attribute name
]

TYPES = [
    # portal_type name
    "MarketingAuthorization",
    "PharmaceuticalProduct",
]


@implementer(IHochLimsCatalog)
class HochLimsCatalog(BaseCatalog):
    """Catalog for HochLims
    """
    def __init__(self):
        BaseCatalog.__init__(self, CATALOG_ID, title=CATALOG_TITLE)

    @property
    def mapped_catalog_types(self):
        return TYPES


InitializeClass(HochLimsCatalog)