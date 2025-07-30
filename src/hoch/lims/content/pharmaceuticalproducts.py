from bika.lims.interfaces import IDoNotSupportSnapshots
from plone.dexterity.content import Container
from plone.supermodel import model
from senaite.core.interfaces import IHideActionsMenu
from hoch.lims.interfaces import IPharmaceuticalProducts
from zope.interface import implementer


class IPharmaceuticalProductsSchema(model.Schema):
    """Schema and marker interface
    """


@implementer(IPharmaceuticalProducts, IPharmaceuticalProductsSchema, IDoNotSupportSnapshots,
             IHideActionsMenu)
class PharmaceuticalProducts(Container):
    """A fake container for pharmaceutical products displayed in the navigation bar.
    Has the view browser/PharmaceuticalProducts/view.py wired
    """