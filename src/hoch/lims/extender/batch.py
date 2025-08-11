from archetypes.schemaextender.interfaces import IBrowserLayerAwareExtender
from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from zope.component import adapts
from zope.interface import implements
from bika.lims.interfaces import IBatch
from hoch.lims.content.fields import UIDReferenceFieldAT
from hoch.lims.interfaces import IHochLims
from senaite.core.browser.widgets.referencewidget import ReferenceWidget
from hoch.lims.catalog import HOCHLIMS_CATALOG
from hoch.lims import messageFactory as _

class BatchSchemaExtender(object):
    """Extend Schema Fields for Batch content type."""
    layer = IHochLims
    implements(
        ISchemaExtender,
        IBrowserLayerAwareExtender,
        IOrderableSchemaExtender)
    adapts(IBatch)
    
    fields = [
        UIDReferenceFieldAT(
        "Product",
        required=1,
        allowed_types=("PharmaceuticalProduct",),
        mode="rw",
        render_own_label=True,
        #read_permission=View,
        #write_permission=ModifyPortalContent,
        widget=ReferenceWidget(
            label=_(
                u"label_batch_product",
                default=u"Product"),
            description=_(
                u"description_batch_product",
                default=u"Select the product for this batch."),
            visible=True,
            catalog=HOCHLIMS_CATALOG,
            search_index="product_searchable_text",
            value_key="description",
            search_wildcard=True,
            query={
                "is_active": True,
                "sort_on": "product_name",
                "sort_order": "ascending"
            },
        )),
    ]
    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields
    
    def getOrder(self, original):
        """Change the order of the extended fields
        """
        # get the fields of the default schemata
        default = original["default"]

        # move  Order Number 
        index = default.index("title")
        # remove any existing field
        default.remove("Product")
        # add the field below the reference index
        default.insert(index - 1, "Product")

        return original

class BatchSchemaModifier(object):
    """Modify Batch Schema Fields
    """
    layer = IHochLims
    implements(
        ISchemaModifier,
        IBrowserLayerAwareExtender)
    adapts(IBatch)

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        # Make the profiles field required
        # profiles = schema.get("Profiles")
        # profiles.required = True

        return schema