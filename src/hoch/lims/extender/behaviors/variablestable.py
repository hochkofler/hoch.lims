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
        required=False)
    
    parameter = schema.Choice(
        title=_(
            u"label_variable_parameter",
            default=u"Parameter"
        ),
        source=VARIABLES,
        required=False,
    )
    value = schema.Float(
        title=_(
            u"label_variable_vakye",
            default=u"Value"
        ),
        min=0.0,
        default=1.0,
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
    
def compute_variables_dict(obj):
    """Build variables_dict from variables_table"""
    data = {}
    cache = {}
    for row in (obj.variables_table or []):
        param = row.get("parameter")
        value = row.get("value")
        uids = row.get("service")
        if not uids:
            continue
        for uid in (uids if isinstance(uids, (list, tuple)) else [uids]):
            if uid not in cache:
                service = get_object_by_uid(uid)
                cache[uid] = service.getKeyword() if service else uid
            code = cache[uid]
            
            if param and value is not None:
                data.setdefault(code, {})[param] = value
    return data
@check_installed(None)
@adapter(ISampleMatrix, IObjectAddedEvent)
def on_samplematrix_added(obj, event):
    obj.variables_dict = compute_variables_dict(obj)

@check_installed(None)
@adapter(ISampleMatrix, IObjectModifiedEvent)
def on_samplematrix_modified(obj, event):
    obj.variables_dict = compute_variables_dict(obj)