from archetypes.schemaextender.interfaces import IBrowserLayerAwareExtender
from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from zope.component import adapts
from zope.interface import implements
from bika.lims.interfaces import IBatch
from hoch.lims.content.fields import UIDReferenceFieldAT, ExtDateTimeFieldAT, ExtIntegerFieldAT, ExtStringFieldAT
from hoch.lims.interfaces import IHochLims
from senaite.core.browser.widgets.referencewidget import ReferenceWidget
from bika.lims.browser.widgets import DateTimeWidget
from Products.Archetypes.Widget import IntegerWidget, StringWidget
from hoch.lims.catalog import HOCHLIMS_CATALOG
from hoch.lims import messageFactory as _
from DateTime.DateTime import DateTime

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
        read_permission=View,
        write_permission=ModifyPortalContent,
        widget=ReferenceWidget(
            label=_(
                u"label_batch_product",
                default=u"Product"),
            description=_(
                u"description_batch_product",
                default=u"Select the product for this batch."),
            visible=True,
            catalog=HOCHLIMS_CATALOG,
            search_index="pharmaceuticalproduct_searchable_text",
            search_wildcard=True,
            query={
                "is_active": True,
                "sort_on": "product_name",
                "sort_order": "ascending"
            },
        )),
        ExtDateTimeFieldAT(
            'ExpirationDate',
            mode="rw",
            min="current",
            default_method=DateTime,
            required=True,
            widget=DateTimeWidget(
                label=_(
                    u"label_batch_expirationdate",
                    default=u"Expire date"),
                datepicker_nopast=1,
            ),
        ),
        ExtIntegerFieldAT(
            'SubGroups',
            required=True,
            default=1,
            widget=IntegerWidget(
              label=_(
                u"label_batch_subgroups",
                default=u"Sub groups",),  
            ),
        ),
        ExtDateTimeFieldAT(
            'ManufactureDate',
            mode="rw",
            max="current",
            default_method=DateTime,
            required=False,
            widget=DateTimeWidget(
                label=_(
                    u"label_batch_manufacturedate",
                    default=u"Manufacture date"),
            ),
        ),
        ExtIntegerFieldAT(
            'BatchSize',
            required=True,
            widget=IntegerWidget(
              label=_(
                u"label_batch_batchsize",
                default=u"Batch size",),  
            ),
        ),
        ExtIntegerFieldAT(
            'ReleasedBatchSize',
            required=False,
            widget=IntegerWidget(
                label=_(
                    u"label_batch_releasedbatchsize",
                    default=u"Released batch size",
                ),)
        ),
        UIDReferenceFieldAT(
            'ReleasePublication',
            allowed_types=['ResultsReport'],
            mode="rw",
            required=False,
            multiValued=False,
            relationship='BatchReleasePublication',
            render_own_label=True,
            read_permission=View,
            write_permission=ModifyPortalContent,
            widget=ReferenceWidget(
                label=_(
                    u"label_batch_release_publication",
                    default=u"Batch Release COA"),
                description=_(
                    u"description_batch_release_publication",
                    default=u"Select the multi-sample publication for batch release"),
                visible=True,
                catalog='senaite_catalog_report',
                base_query={
                    'portal_type': 'ResultsReport',
                    'sort_on': 'created',
                    'sort_order': 'descending',
                },
                search_fields=('title', 'id'),
                showOn=True,
            )),
        ExtDateTimeFieldAT(
            'ReleaseDate',
            mode="rw",
            required=False,
            widget=DateTimeWidget(
                label=_(
                    u"label_batch_release_date",
                    default=u"Release Date"),
                description=_(
                    u"description_batch_release_date",
                    default=u"Date when the batch was released"),
                visible={'edit': 'hidden', 'view': 'visible'},
            ),
        ),
        ExtStringFieldAT(
            'ReleasedBy',
            mode="rw",
            required=False,
            widget=StringWidget(
                label=_(
                    u"label_batch_released_by",
                    default=u"Released By"),
                description=_(
                    u"description_batch_released_by",
                    default=u"User who released the batch"),
                visible={'edit': 'hidden', 'view': 'visible'},
            ),
        ),
        
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