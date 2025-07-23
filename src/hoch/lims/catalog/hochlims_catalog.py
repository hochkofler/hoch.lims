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
    ("mktauth_reg_number", "", "FieldIndex"),
    ("mktauth_expiration_date", "", "DateIndex"),
    ("mktauth_holder", "", "FieldIndex")
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
    """Catalog for Patients
    """
    def __init__(self):
        BaseCatalog.__init__(self, CATALOG_ID, title=CATALOG_TITLE)

    @property
    def mapped_catalog_types(self):
        return TYPES


InitializeClass(HochLimsCatalog)