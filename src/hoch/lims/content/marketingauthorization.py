from AccessControl import ClassSecurityInfo
from plone.autoform import directives
from Products.CMFCore import permissions
from plone.supermodel import model
from zope import schema
from hoch.lims import messageFactory as _
from senaite.core.api import dtime
from senaite.core.content.base import Container
from hoch.lims.interfaces import IMarketingAuthorization
from hoch.lims.content.fields import DatetimeField, DatetimeWidget
from zope.interface import implementer
from hoch.lims.catalog import HOCHLIMS_CATALOG

class IMarketingAuthorizationSchema(model.Schema):
    """Marketing Authorization Schema"""

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

    directives.widget("expiration_date",
                      DatetimeWidget,
                      show_time=False)
    
    expiration_date = DatetimeField(
        title=_(u"label_marketingauthorization_expiration_date", default=u"Expiration Date"),
        description=_(u"Expiration date of the marketing authorization"),
        required=True,
    )

    holder = schema.Choice(
        title=_(u"label_marketingauthorization_holder", default=u"Holder"),
        description=_(u"Organization that holds the certification"),
        source="hoch.lims.vocabularies.regulators",
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
    
    @security.protected(permissions.View)
    def getLocalizedExpirationDate(self):
        """Returns the Expiration Date with the field accessor
        """
        date = dtime.to_DT(self.getExpirationDate())
        return dtime.to_localized_time(date)

    @security.protected(permissions.View)
    def getHolder(self):
        """Returns the holder with the field accessor
        """
        accessor = self.accessor("holder")
        value = accessor(self) or ""
        return value.encode("utf-8")