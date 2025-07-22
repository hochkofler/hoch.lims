from plone.autoform import directives as form
from plone.supermodel import model
from zope import schema
from hoch.lims import messageFactory as _
from senaite.core.content.base import Container
from hoch.lims.interfaces import IPharmaceuticalProduct
from zope.interface import implementer

class IPharmaceuticalProductSchema(model.Schema):
    """Pharmaceutical Product Schema"""

    form.write_permission(marketing_authorization="hoch.lims: Field: Edit Regulatory Field")
    form.read_permission(marketing_authorization="hoch.lims: Field: View Regulatory Field")
    marketing_authorization = schema.Choice(
        title=_("Marketing Authorization"),
        vocabulary="hoch.lims.MarketingAuthorizationVocabulary",
        required=True,
    )

@implementer(IPharmaceuticalProduct)
class PharmaceuticalProduct(Container):
    """Pharmaceutical Product content type"""
    pass