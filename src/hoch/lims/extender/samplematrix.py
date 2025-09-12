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
from bika.lims.browser.widgets.recordswidget import RecordsWidget
from senaite.core.z3cform.widgets.uidreference import UIDReferenceWidgetFactory
from hoch.lims.catalog import HOCHLIMS_CATALOG
from hoch.lims import messageFactory as _
from hoch.lims.content.AnalysisSettingsField import AnalysisSettingsField
from hoch.lims.content.AnalysisSettingsField import IVariableRow
from zope import schema
from senaite.core.browser.fields.records import RecordField
from senaite.core.z3cform.widgets.datagrid import DataGridWidgetFactory
from senaite.core.schema.registry import DataGridRow
from zope.interface import Interface

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
            "sort_on": "title",
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
    
