from bika.lims.interfaces import IDoNotSupportSnapshots
from plone.supermodel import model
from senaite.core.content.base import Container
from senaite.core.interfaces import IHideActionsMenu
from zope.interface import implementer
from hoch.lims.interfaces import IMarketingAuthorizations


class IMarketingAuthorizationsSchema(model.Schema):
    """Folder Interface
    """
    pass


@implementer(IMarketingAuthorizations, IDoNotSupportSnapshots, IHideActionsMenu)
class MarketingAuthorizations(Container):
    """Folder
    """
    pass