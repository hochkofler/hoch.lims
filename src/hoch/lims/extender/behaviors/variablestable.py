from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.dexterity.interfaces import IDexterityContent
from plone.supermodel import model
from hoch.lims import messageFactory as _
from senaite.core.schema.fields import DataGridField
from senaite.core.schema.fields import DataGridRow
from senaite.core.z3cform.widgets.datagrid import DataGridWidgetFactory
from zope import schema
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface
from zope.interface import provider
from senaite.core.z3cform.widgets.uidreference import UIDReferenceWidgetFactory
from hoch.lims.config import VARIABLES
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.config.widgets import get_default_columns
from senaite.core.schema import UIDReferenceField
from bika.lims.api import get_object_by_uid
from senaite.core.interfaces import ISampleMatrix
from zope.lifecycleevent.interfaces import IObjectModifiedEvent, IObjectAddedEvent
from hoch.lims import check_installed
from hoch.lims.utils import compute_variables_dict

class IVariablesTableSchema(Interface):
    directives.widget(
        "service",
        UIDReferenceWidgetFactory,
        catalog=SETUP_CATALOG,
        query={
            "portal_type": "AnalysisService",
            "is_active": True,
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        },
        display_template="<a href='${url}'>${Title}</a>",
        columns=get_default_columns)
    service = UIDReferenceField(
        title=_(
            u"label_variable_service",
            default=u"service"
        ),
        allowed_types=("AnalysisService", ),
        multi_valued=False,
        required=True)
    
    parameter = schema.Choice(
        title=_(
            u"label_variable_parameter",
            default=u"Parameter"
        ),
        source=VARIABLES,
        required=True,
    )
    value = schema.Float(
        title=_(
            u"label_variable_value",
            default=u"Value"
        ),
        min=0.0,
        default=1.0,
        required=True,
    )
    unit = schema.TextLine(
        title=_(
            u"label_variable_unit",
            default=u"Unit"
        ),
        required=False,
    )
    
@provider(IFormFieldProvider)
class IVariablesTableBehavior(model.Schema):

    variables_table = DataGridField(
        title=_(
            u"label_variables_table",
            default=u"Variables Table"
        ),
        value_type=DataGridRow(
            title=u"Variables",
            schema=IVariablesTableSchema),
        required=False,
        missing_value=[],
        default=[],
    )
    directives.widget(
        "variables_table",
        DataGridWidgetFactory,
        auto_append=True)
    
@implementer(IVariablesTableBehavior)
@adapter(IDexterityContent)
class VariablesTable(object):

    def __init__(self, context):
        self.context = context

    def _get_variables_table(self):
        return self.context.variables_table

    def _set_variables_table(self, value):
        self.context.variables_table = value

    variables_table = property(_get_variables_table, _set_variables_table)

@check_installed(None)
@adapter(ISampleMatrix, IObjectAddedEvent)
def on_samplematrix_added(obj, event):
    obj.variables_dict = compute_variables_dict(obj)

@check_installed(None)
@adapter(ISampleMatrix, IObjectModifiedEvent)
def on_samplematrix_modified(obj, event):
    obj.variables_dict = compute_variables_dict(obj)