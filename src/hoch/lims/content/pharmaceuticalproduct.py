from AccessControl import ClassSecurityInfo
from plone.autoform import directives
from plone.supermodel import model
from zope import schema
from hoch.lims import messageFactory as _
from senaite.core.content.base import Container
from hoch.lims.interfaces import IPharmaceuticalProduct
from zope.interface import implementer
from hoch.lims.catalog import HOCHLIMS_CATALOG
from hoch.lims.content.fields import UIDReferenceFieldDx
from senaite.core.z3cform.widgets.uidreference import UIDReferenceWidgetFactory
from Products.CMFCore import permissions
from bika.lims import api

class IPharmaceuticalProductSchema(model.Schema):
    """Pharmaceutical Product Schema"""

    directives.omitted("title", "description")
    title = schema.TextLine(
        title=_(
            u"title_product_itemcode",
            default=u"Code"
        ),
        required=True,
        readonly=True,
    )

    code = schema.TextLine(
        title=_(
            u"label_product_code",
            default=u"Code",
        ),
        description=_(
            u"description_product_code",
            default=u"Unique product code",
        ),
        required=False,
    )

    description = schema.TextLine(
        title=_(
            u"title_product_itemname",
            default=u"Item Name"
        ),
        required=True,
        readonly=True,
    )

    directives.widget(
        "marketingauthorization",
        UIDReferenceWidgetFactory,
        catalog=HOCHLIMS_CATALOG,
        query={
            "is_active": True,
            "sort_on": "title",
            "sort_order": "ascending",
        },
    )
    marketingauthorization = UIDReferenceFieldDx(
        title=_(
            u"title_pharmaceuticalproduct_marketingauthorization",
            default=u"Marketing Authorization"
        ),
        description=_(
            u"description_pharmaceuticalproduct_marketingauthorization",
            default=u"Select a marketing authorization to be used for this product. "
        ),
        relationship="PharmaceuticalProductMarketingAuthorization",
        allowed_types=("MarketingAuthorization", ),
        multi_valued=False,
        required=True,
    )

    name = schema.TextLine(
        title=_(
            u"label_product_name",
            default=u"Name",
        ),
        description=_(
            u"description_product_name",
            default=u"Description of the product",
        ),
        required=True,
    )

    presentation = schema.TextLine(
        title=_(
            u"label_product_presentation",
            default=u"Presentation",
        ),
        description=_(
            u"description_product_presentation",
            default=u"Description of the product presentation",
        ),
        required=True,
    ),

    primary_presentation = schema.Choice(
        title=_(
            u"label_product_primary_presentation",
            default=u"Primary Presentation",
        ),
        description=_(
            u"description_product_primary_presentation",
            default=u"Select the primary presentation for this product.",
        ),
        required=True,
        vocabulary="hoch.lims.PrimaryPresentationVocabulary",
    )

    dosage_unit_per_primary_presentation = schema.Int(
        title=_(
            u"label_product_dosage_unit_per_primary_presentation",
            default=u"Dosage Unit per Primary Presentation",
        ),
        description=_(
            u"description_product_dosage_unit_per_primary_presentation",
            default=u"Number of dosage units contained in the primary presentation.",
        ),
        required=True,
    )

    secundary_presentation = schema.Choice(
        title=_(
            u"label_product_secundary_presentation",
            default=u"Secondary Presentation",
        ),
        description=_(
            u"description_product_secundary_presentation",
            default=u"Select the secondary presentation for this product.",
        ),
        required=False,
        vocabulary="hoch.lims.SecundaryPresentationVocabulary",
    )

    dosage_unit_per_secundary_presentation = schema.Int(
        title=_(
            u"label_product_dosage_unit_per_secondary_presentation",
            default=u"Dosage Unit per Secondary Presentation",
        ),
        description=_(
            u"description_product_dosage_unit_per_secondary_presentation",
            default=u"Number of dosage units contained in the secondary presentation.",
        ),
        required=True,
    )
    

@implementer(IPharmaceuticalProduct, IPharmaceuticalProductSchema)
class PharmaceuticalProduct(Container):
    """Pharmaceutical Product content type"""
    _catalogs = [HOCHLIMS_CATALOG]
    security = ClassSecurityInfo()

    @security.protected(permissions.View)
    def Title(self):
        regObj = api.get_object(self.getMarketingAuthorization())
        reg = regObj.getRegistrationNumber()
        code = self.getCode()
        name = self.getName()
        return u" ".join(filter(None, (reg, code)))

    @security.protected(permissions.View)
    def Description(self):
        regObj = api.get_object(self.getMarketingAuthorization())
        reg = regObj.getRegistrationNumber()
        code = self.getCode()
        name = self.getName()
        return u" ".join(filter(None, (reg, code, name)))

    @security.protected(permissions.View)
    def getMarketingAuthorization(self):
        accessor = self.accessor("marketingauthorization")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getCode(self):
        accessor = self.accessor("code")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getName(self):
        accessor = self.accessor("name")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getPresentation(self):
        accessor = self.accessor("presentation")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getPrimaryPresentation(self):
        accessor = self.accessor("primary_presentation")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getDosageUnitPerPrimaryPresentation(self):
        accessor = self.accessor("dosage_unit_per_primary_presentation")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getDosageUnitPerSecundaryPresentation(self):
        accessor = self.accessor("dosage_unit_per_secundary_presentation")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getSecundaryPresentation(self):
        accessor = self.accessor("secundary_presentation")
        return accessor(self)