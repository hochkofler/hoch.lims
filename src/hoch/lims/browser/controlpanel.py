import re

from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.autoform import directives
from plone.protect.interfaces import IDisableCSRFProtection
from plone.supermodel import model
from plone.z3cform import layout
from senaite.core.schema.registry import DataGridRow
from senaite.core.z3cform.widgets.datagrid import DataGridWidgetFactory
from hoch.lims import messageFactory as _
from zope import schema
from zope.interface import Interface
from zope.interface import Invalid
from zope.interface import alsoProvides
from zope.interface import invariant
from zope.interface import provider
from zope.schema.interfaces import IContextAwareDefaultFactory
from hoch.lims.api import hochlims_search
from hoch.lims.config import REGULATORY_AUTHORITIES


@provider(IContextAwareDefaultFactory)
def default_regulatory_authorities(context):
    return [{u"key": i[0], u"value": i[1]} for i in REGULATORY_AUTHORITIES]

class IRegulatoryAuthorities(Interface):
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
            u"The value will be displayed in the identifers selection"
        ),
        required=True,
    )


class IHochControlPanel(Interface):
    """Controlpanel Settings
    """

    ###
    # Fieldsets
    ###
    model.fieldset(
        "regulatory_authorities",
        label=_(u"Regulatory Authorities"),
        description=_(""),
        fields=[
            "regulatory_authorities",
        ],
    )

    ###
    # Fields
    ###
    directives.widget(
        "regulatory_authorities",
        DataGridWidgetFactory,
        allow_reorder=True,
        auto_append=True)
    regulatory_authorities = schema.List(
        title=_(
            u"label_controlpanel_marketingauthorizations_regulatory_authorities",
            default=u"Marital Statuses"),
        description=_(
            u"description_controlpanel_marketingauthorizations_regulatory_authorities",
            default=u"regulatory companies that grant marketing authorizations"
        ),
        value_type=DataGridRow(schema=IRegulatoryAuthorities),
        required=True,
        defaultFactory=default_regulatory_authorities,
    )

    @invariant
    def validate_regulatory_authorities(data):
        """Checks if the keyword is unique and valid
        """
        keys = []
        for status in data.regulatory_authorities:
            key = status.get("key")
            # check if the key contains invalid characters
            if re.findall(r"[^A-Za-z\w\d\-\_]", key):
                raise Invalid(_("Key contains invalid characters"))
            # check if the key is unique
            if key in keys:
                raise Invalid(_("Key '%s' is not unique" % key))

            keys.append(key)

        # check if a used key is removed
        old_statuses = data.__context__.regulatory_authorities
        old_keys = map(lambda i: i.get("key"), old_statuses)
        removed = list(set(old_keys).difference(keys))

        for key in removed:
            # check if there are patients that use one of the removed key
            brains = hochlims_search({"mktauth_issuing_organization": key})
            if brains:
                raise Invalid(
                    _("Can not delete marital status that is in use"))


class HochControlPanelForm(RegistryEditForm):
    schema = IHochControlPanel
    schema_prefix = "hoch.lims"
    label = _("HochLims Settings")
    description = _("Global settings for Marketing Authorizatins")

    def __init__(self, context, request):
        super(HochControlPanelForm, self).__init__(context, request)
        alsoProvides(request, IDisableCSRFProtection)


HochControlPanelView = layout.wrap_form(
    HochControlPanelForm, ControlPanelFormWrapper)
