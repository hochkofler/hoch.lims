from plone.autoform import directives as form
from plone.supermodel import model
from zope import schema
from hoch.lims import messageFactory as _
from senaite.core.content.base import Container
from hoch.lims.interfaces import IMarketingAuthorization
from zope.interface import implementer

class IMarketingAuthorizationSchema(model.Schema):
    """Marketing Authorization Schema"""

    form.write_permission(reg_number="hoch.lims: Field: Edit Regulatory Field")
    form.read_permission(reg_number="hoch.lims: Field: View Regulatory Field")
    reg_number = schema.TextLine(
        title=_("Registration Number"),
        required=True,
    )

    form.write_permission(expiration_date="hoch.lims: Field: Edit Regulatory Field")
    form.read_permission(expiration_date="hoch.lims: Field: View Regulatory Field")
    expiration_date = schema.Date(
        title=_("Expiration Date"),
        required=True,
    )

    form.write_permission(holder="hoch.lims: Field: Edit Regulatory Field")
    form.read_permission(holder="hoch.lims: Field: View Regulatory Field")
    holder = schema.TextLine(
        title=_("Holder"),
        required=True,
    )

@implementer(IMarketingAuthorization)
class MarketingAuthorization(Container):
    """Marketing Authorization content type"""
    pass