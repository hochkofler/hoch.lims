from plone.dexterity.content import Container
from plone.supermodel import model
from hoch.lims.interfaces import IProducts
from zope.interface import implementer


class IProductsSchema(model.Schema):
    """Schema interface
    """


@implementer(IProducts, IProductsSchema)
class Products(Container):
    """Folder for Products contents
    """