from AccessControl import ClassSecurityInfo
from plone.autoform import directives
from Products.CMFCore import permissions
from plone.supermodel import model
from zope import schema
from hoch.lims import messageFactory as _
from senaite.core.content.base import Container
from hoch.lims.interfaces import IMarketingAuthorization
from zope.interface import implementer
from hoch.lims.catalog import HOCHLIMS_CATALOG

class IMarketingAuthorizationSchema(model.Schema):
    """Marketing Authorization Schema"""

    directives.omitted("title")

    title = schema.TextLine(
        title=_(
            u"title",
            default=u"title"
        ),
        required=True,
    )

    description = schema.TextLine(
        title=_(
            u"description",
            default=u"Description"
        ),
        required=False,
    )

    reg_number = schema.TextLine(
        title=_("Registration Number"),
        required=True,
    )

    expiration_date = schema.Date(
        title=_("Expiration Date"),
        required=True,
    )

    holder = schema.TextLine(
        title=_("Holder"),
        required=True,
    )

@implementer(IMarketingAuthorization, IMarketingAuthorizationSchema)
class MarketingAuthorization(Container):
    """Marketing Authorization content type"""
    _catalogs = [HOCHLIMS_CATALOG]
    security = ClassSecurityInfo()

    @security.protected(permissions.View)
    def getRegNumber(self):
        """Returns the registration number with the field accessor
        """
        accessor = self.accessor("reg_number")
        value = accessor(self) or ""
        return value.encode("utf-8")

    @security.protected(permissions.View)
    def getExpirationDate(self, as_date=True):
        """Returns the expiration date with the field accessor
        """
        accessor = self.accessor("expiration_date")
        value = accessor(self)
        # Return a plain date object to avoid timezone issues
        # TODO Convert to current timezone and keep it as datetime instead!
        if dtime.is_dt(value) and as_date:
            value = value.date()
        return value