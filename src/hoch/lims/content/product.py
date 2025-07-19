# -*- coding: utf-8 -*-

from AccessControl import ClassSecurityInfo
from hoch.lims import messageFactory as _
from bika.lims.interfaces import IDeactivable
from plone.autoform import directives
from plone.namedfile.field import NamedBlobFile
from plone.supermodel import model
from Products.CMFCore import permissions
from senaite.core.catalog import SETUP_CATALOG
from plone.dexterity.content import Container
from senaite.core.z3cform.widgets.uidreference import UIDReferenceWidgetFactory
from zope import schema
from zope.interface import implementer
from hoch.lims.content.fields import UIDReferenceFieldDx
from hoch.lims.interfaces import IProduct


class IProductSchema(model.Schema):
    """Schema interface
    """

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

    directives.widget(
        "samplematrix",
        UIDReferenceWidgetFactory,
        catalog=SETUP_CATALOG,
        query={
            "is_active": True,
            "sort_on": "title",
            "sort_order": "ascending",
        },
    )
    samplematrix = UIDReferenceFieldDx(
        title=_(
            u"title_product_samplematrix",
            default=u"Sample Matrix"
        ),
        description=_(
            u"description_product_product_samplematrix",
            default=u"Select a sample matrix to be used for this product. "
        ),
        relationship="ProductSampleMatrix",
        allowed_types=("SampleMatrix", ),
        multi_valued=False,
        required=True,
    )

    is_medical_sample = schema.Bool(
        title=_(
            u"title_product_is_medical_sample",
            default=u"Is medical sample?"
        ),
        description=_(
            u"description_product_is_medical_sample",
            default=u"Is this product a medical sample?"
        ),
        required=False,
    )

    attachment_file = NamedBlobFile(
        title=_(
            u"title_product_attachment_file",
            default=u"Attachment"
        ),
        required=False,
    )


@implementer(IProduct, IProductSchema, IDeactivable)
class Product(Container):
    """Product content type
    """
    # Catalogs where this type will be catalogued
    _catalogs = [SETUP_CATALOG]
    security = ClassSecurityInfo()

    @security.protected(permissions.View)
    def getTitle(self):
        accessor = self.accessor("title")
        return accessor(self)

    @security.protected(permissions.ModifyPortalContent)
    def setTitle(self, value):
        current = self.title
        value = value.strip()
        
        if current and value != current:
            raise ValueError(_("The product code cannot be changed"))

        check_title(value, self)
        self.mutator("title")(self, value)