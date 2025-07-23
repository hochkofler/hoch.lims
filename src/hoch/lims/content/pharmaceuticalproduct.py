from AccessControl import ClassSecurityInfo
from plone.autoform import directives
from plone.supermodel import model
from zope import schema
from hoch.lims import messageFactory as _
from senaite.core.content.base import Container
from hoch.lims.interfaces import IPharmaceuticalProduct
from zope.interface import implementer
from hoch.lims.catalog import HOCHLIMS_CATALOG

class IPharmaceuticalProductSchema(model.Schema):
    """Pharmaceutical Product Schema"""

    title = schema.TextLine(
        title=_(
            u"title_product_itemcode",
            default=u"Code"
        ),
        required=True,
    )

    description = schema.TextLine(
        title=_(
            u"title_product_itemname",
            default=u"Item Name"
        ),
        required=False,
    )

@implementer(IPharmaceuticalProduct, IPharmaceuticalProductSchema)
class PharmaceuticalProduct(Container):
    """Pharmaceutical Product content type"""
    _catalogs = [HOCHLIMS_CATALOG]
    security = ClassSecurityInfo()