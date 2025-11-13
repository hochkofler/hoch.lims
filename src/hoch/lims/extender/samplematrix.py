from AccessControl import ClassSecurityInfo
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from Products.CMFCore import permissions
from senaite.core.interfaces import ISampleMatrix
from zope.component import adapter
from zope.interface import implementer
from zope.interface import provider
from hoch.lims.content.fields import UIDReferenceFieldDx
from senaite.core.z3cform.widgets.uidreference import UIDReferenceWidgetFactory
from hoch.lims.catalog import HOCHLIMS_CATALOG
from hoch.lims import messageFactory as _

@provider(IFormFieldProvider)
class ISampleMatrixSchemaExtender(model.Schema):
    """Extended schema fields
    """
    directives.widget(
        "marketingauthorization",
        UIDReferenceWidgetFactory,
        catalog=HOCHLIMS_CATALOG,
        query={
            "is_active": True,
            "sort_on": "mktauth_trade_name",
            "sort_order": "ascending",
        },
    )
    marketingauthorization = UIDReferenceFieldDx(
        title=_(
            u"title_samplematrix_marketingauthorization",
            default=u"Marketing Authorization"
        ),
        description=_(
            u"description_samplematrix_marketingauthorization",
            default=u"Select a marketing authorization to be used for this product. "
        ),
        relationship="SampleMatrixMarketingAuthorization",
        allowed_types=("MarketingAuthorization", ),
        multi_valued=False,
        required=False,
    )
    
@implementer(ISampleMatrixSchemaExtender)
@adapter(ISampleMatrix)
class SampleMatrixSchemaExtender(object):
    """Extends sample types with additional fields
    """
    security = ClassSecurityInfo()
    def __init__(self, context):
        self.context = context
    @security.protected(permissions.View)
    def get_marketingauthorization(self):
        accessor = self.context.accessor("marketingauthorization")
        return accessor(self.context)
    
    @security.protected(permissions.ModifyPortalContent)
    def set_marketingauthorization(self, value):
        mutator = self.context.mutator("marketingauthorization")
        mutator(self.context, value)
    
    marketingauthorization = property(get_marketingauthorization, set_marketingauthorization)
    
