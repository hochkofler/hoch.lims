from plone.autoform import directives
from plone.supermodel import model
from zope import schema
from zope.interface import Interface
from zope.interface import Invalid
from zope.interface import invariant
from zope.interface import provider
from zope.schema.interfaces import IContextAwareDefaultFactory

from plone.z3cform.layout import wrap_form
from z3c.form import form
from plone.app.registry.browser import controlpanel
from senaite.core.z3cform.widgets.datagrid import DataGridWidgetFactory
from senaite.core.schema.registry import DataGridRow
from plone import api

import re

from hoch.lims import messageFactory as _
from hoch.lims.config import (
    REGULATORY_AUTHORITIES,
    DOSAGE_FORMS,
    PRODUCT_LINES,
    THERAPEUTIC_INDICATIONS,
    SALE_CONDITIONS,
    STORAGE_CONDITIONS,
    ADMINISTRATION_ROUTES,
)

# Common interface for all vocabulary rows
class IVocabularyRow(Interface):
    key = schema.TextLine(
        title=_(u"Key"),
        description=_(
            u"The key will be stored in the database and must be unique"
        ),
        required=True,
    )

    value = schema.TextLine(
        title=_(u"Value"),
        description=_(
            u"The value will be displayed in selection fields"
        ),
        required=True,
    )

# Default factories
@provider(IContextAwareDefaultFactory)
def default_regulatory_authorities(context):
    return [{u"key": i[0], u"value": i[1]} for i in REGULATORY_AUTHORITIES]

@provider(IContextAwareDefaultFactory)
def default_dosage_forms(context):
    return [{u"key": i[0], u"value": i[1]} for i in DOSAGE_FORMS]

@provider(IContextAwareDefaultFactory)
def default_product_lines(context):
    return [{u"key": i[0], u"value": i[1]} for i in PRODUCT_LINES]

@provider(IContextAwareDefaultFactory)
def default_therapeutic_indications(context):
    return [{u"key": i[0], u"value": i[1]} for i in THERAPEUTIC_INDICATIONS]

@provider(IContextAwareDefaultFactory)
def default_sale_conditions(context):
    return [{u"key": i[0], u"value": i[1]} for i in SALE_CONDITIONS]

@provider(IContextAwareDefaultFactory)
def default_storage_conditions(context):
    return [{u"key": i[0], u"value": i[1]} for i in STORAGE_CONDITIONS]

@provider(IContextAwareDefaultFactory)
def default_administration_routes(context):
    return [{u"key": i[0], u"value": i[1]} for i in ADMINISTRATION_ROUTES]

class IHochControlPanel(Interface):
    """Controlpanel Settings for HochLIMS"""
    
    model.fieldset(
        "regulatory_settings",
        label=_(u"Regulatory Settings"),
        fields=[
            "regulatory_authorities",
            "dosage_forms",
            "product_lines",
            "therapeutic_indications",
            "sale_conditions",
            "storage_conditions",
            "administration_routes",
        ],
    )
    
    # Regulatory Authorities
    directives.widget(
        "regulatory_authorities",
        DataGridWidgetFactory,
        allow_reorder=True,
        auto_append=True)
    regulatory_authorities = schema.List(
        title=_(u"Regulatory Authorities"),
        description=_(u"Regulatory bodies that grant marketing authorizations"),
        value_type=DataGridRow(schema=IVocabularyRow),
        required=True,
        defaultFactory=default_regulatory_authorities,
    )
    
    # Dosage Forms
    directives.widget(
        "dosage_forms",
        DataGridWidgetFactory,
        allow_reorder=True,
        auto_append=True)
    dosage_forms = schema.List(
        title=_(u"Dosage Forms"),
        description=_(u"Pharmaceutical dosage forms"),
        value_type=DataGridRow(schema=IVocabularyRow),
        required=True,
        defaultFactory=default_dosage_forms,
    )
    
    # Product Lines
    directives.widget(
        "product_lines",
        DataGridWidgetFactory,
        allow_reorder=True,
        auto_append=True)
    product_lines = schema.List(
        title=_(u"Product Lines"),
        description=_(u"Types of pharmaceutical products"),
        value_type=DataGridRow(schema=IVocabularyRow),
        required=True,
        defaultFactory=default_product_lines,
    )
    
    # Therapeutic Indications
    directives.widget(
        "therapeutic_indications",
        DataGridWidgetFactory,
        allow_reorder=True,
        auto_append=True)
    therapeutic_indications = schema.List(
        title=_(u"Therapeutic Indications"),
        description=_(u"Approved therapeutic uses"),
        value_type=DataGridRow(schema=IVocabularyRow),
        required=True,
        defaultFactory=default_therapeutic_indications,
    )
    
    # Sale Conditions
    directives.widget(
        "sale_conditions",
        DataGridWidgetFactory,
        allow_reorder=True,
        auto_append=True)
    sale_conditions = schema.List(
        title=_(u"Sale Conditions"),
        description=_(u"Conditions under which products may be sold"),
        value_type=DataGridRow(schema=IVocabularyRow),
        required=True,
        defaultFactory=default_sale_conditions,
    )
    
    # Storage Conditions
    directives.widget(
        "storage_conditions",
        DataGridWidgetFactory,
        allow_reorder=True,
        auto_append=True)
    storage_conditions = schema.List(
        title=_(u"Storage Conditions"),
        description=_(u"Required storage conditions"),
        value_type=DataGridRow(schema=IVocabularyRow),
        required=True,
        defaultFactory=default_storage_conditions,
    )
    
    # Administration Routes
    directives.widget(
        "administration_routes",
        DataGridWidgetFactory,
        allow_reorder=True,
        auto_append=True)
    administration_routes = schema.List(
        title=_(u"Administration Routes"),
        description=_(u"Methods of drug administration"),
        value_type=DataGridRow(schema=IVocabularyRow),
        required=True,
        defaultFactory=default_administration_routes,
    )
    
    @invariant
    def validate_keys(data):
        """Validate all vocabulary keys"""
        fields = [
            "regulatory_authorities",
            "dosage_forms",
            "product_lines",
            "therapeutic_indications",
            "sale_conditions",
            "storage_conditions",
            "administration_routes",
        ]
        
        for field_name in fields:
            items = getattr(data, field_name, [])
            keys = []
            
            for item in items:
                key = item.get("key")
                # Check for invalid characters
                if re.findall(r"[^A-Za-z0-9_-]", key):
                    raise Invalid(_(
                        "Key contains invalid characters"
                        "Only letters, numbers, underscores and hyphens are allowed."
                    ))
                
                # Check for uniqueness
                if key in keys:
                    raise Invalid(_("Key '%s' is not unique" % key))
                keys.append(key)
                
                # Check if key is being removed and in use
                # (Implementation would require checking existing content)
                # This is a placeholder for actual in-use validation
                pass

class HochControlPanelForm(controlpanel.RegistryEditForm):
    schema = IHochControlPanel
    schema_prefix = "hoch.lims"
    label = _("HochLIMS Settings")
    description = _("Configuration for pharmaceutical regulatory settings")

    def updateFields(self):
        super(HochControlPanelForm, self).updateFields()

    def updateWidgets(self):
        super(HochControlPanelForm, self).updateWidgets()

HochControlPanelView = wrap_form(
    HochControlPanelForm, controlpanel.ControlPanelFormWrapper)