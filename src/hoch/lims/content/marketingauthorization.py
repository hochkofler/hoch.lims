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

    directives.omitted("title")
    title = schema.TextLine(
        title=u"Title",
        required=False
    )

    directives.omitted("description")
    description = schema.Text(
        title=u"Description",
        required=False
    )

    issuing_organization = schema.Choice(
        title=_(
            u"label_marketingauthorization_issuing_organization",
            default=u"Issuing Regulatory Authority",
        ),
        description=_(
            u"description_marketingauthorization_issuing_organization",
            default=u"Authority that issued the certification",
        ),
        source="hoch.lims.vocabularies.regulatory_authorities",
        required=True,
    )
    
    registration_number = schema.TextLine(
        title=_(
            u"label_marketingauthorization_registration_number",
            default=u"Marketing Authorization Number",
        ),
        description=_(
            u"description_marketingauthorization_registration_number",
            default=u"Unique identifier assigned by the authority",
        ),
        required=True,
        max_length=50,
    )
    
    trade_name = schema.TextLine(
        title=_(
            u"label_marketingauthorization_trade_name",
            default=u"Trade Name (Brand)",
        ),
        description=_(
            u"description_marketingauthorization_trade_name",
            default=u"Commercial name under which the product is sold",
        ),
        required=True,
        max_length=255,
    )

    generic_name = schema.TextLine(
        title=_(
            u"label_marketingauthorization_generic_name",
            default=u"Generic Name",
        ),
        description=_(
            u"description_marketingauthorization_generic_name",
            default=u"Non-proprietary name or chemical name given to a drug",
        ),
        required=True,
        max_length=255,
    )
    
    dosage_form = schema.Choice(
        title=_(
            u"label_marketingauthorization_dosage_form",
            default=u"Dosage Form",
        ),
        description=_(
            u"description_marketingauthorization_dosage_form",
            default=u"Form in which the product is administered",
        ),
        source="hoch.lims.vocabularies.dosage_forms",
        required=True,
    )
    
    product_line = schema.Choice(
        title=_(
            u"label_marketingauthorization_product_line",
            default=u"Product Line",
        ),
        description=_(
            u"description_marketingauthorization_product_line",
            default=u"Product line or category",
        ),
        source="hoch.lims.vocabularies.product_lines",

        required=False,
    )

    registered_presentations = schema.List(
        title=_(u"label_marketingauthorization_registered_presentations",
            u"Registered Presentations"),
        value_type=schema.TextLine(),
        required=True,
    )

    therapeutic_actions = schema.List(
        title=_(
            u"label_marketingauthorization_therapeutic_actions",
            default=u"Therapeutic Indications",
        ),
        description=_(
            u"description_marketingauthorization_therapeutic_actions",
            default=u"List of approved therapeutic uses",
        ),
        value_type=schema.Choice(
            source="hoch.lims.vocabularies.therapeutic_indications"
        ),
        required=True,
    )

    atq_code = schema.TextLine(
        title=_(
            u"label_marketingauthorization_atq_code",
            default=u"A.T.Q. Code",
        ),
        description=_(
            u"description_marketingauthorization_atq_code",
            default=u"Anatomical Therapeutic Chemical classification code",
        ),
        required=False,
    )

    medicine_code = schema.TextLine(
        title=_(
            u"label_marketingauthorization_medicine_code",
            default=u"Medicine Code",
        ),
        required=False,
    )
    
    sale_condition = schema.Choice(
        title=_(
            u"label_marketingauthorization_sale_condition",
            default=u"Sale Condition",
        ),
        description=_(
            u"description_marketingauthorization_sale_condition",
            default=u"Conditions under which the product may be sold",
        ),
        source="hoch.lims.vocabularies.sale_conditions",
        required=True,
    )

    storage_conditions = schema.Choice(
        title=_(
            u"label_marketingauthorization_storage_conditions",
            default=u"Storage Conditions",
        ),
        description=_(
            u"description_marketingauthorization_storage_conditions",
            default=u"Conditions under which the product may be stored",
        ),
        source="hoch.lims.vocabularies.storage_conditions",
        required=True,
    )

    administration_route = schema.Choice(
        title=_(
            u"label_marketingauthorization_administration_route",
            default=u"Route of Administration",
        ),
        description=_(
            u"description_marketingauthorization_administration_route",
            default=u"How the product is administered",
        ),
        source="hoch.lims.vocabularies.administration_routes",
        required=True,
    )

    directives.widget("issue_date",
                      DatetimeWidget,
                      show_time=False)
    
    issue_date = DatetimeField(
        title=_(
            u"label_marketingauthorization_issue_date",
            default=u"Issue Date",
        ),
        description=_(
            u"description_marketingauthorization_issue_date",
            default=u"Date when the authorization was issued",
        ),
        required=True,
    )

    directives.widget("expiration_date",
                      DatetimeWidget,
                      show_time=False)
    
    expiration_date = DatetimeField(
        title=_(
            u"label_marketingauthorization_expiration_date",
            default=u"Expiration Date",
        ),
        description=_(
            u"description_marketingauthorization_expiration_date",
            default=u"Date when the authorization expires",
        ),
        required=True,
    )

    shelf_life = schema.Int(
        title=_(
            u"label_marketingauthorization_shelf_life",
            default=u"Shelf Life (months)",
        ),
        description=_(
            u"description_marketingauthorization_shelf_life",
            default=u"Product stability period",
        ),
        required=True,
        min=1,
        max=120,  # 10 years
    )
    
    holder = schema.TextLine(
        title=_(
            u"label_marketingauthorization_holder",
            default=u"Marketing Authorization Holder",
        ),
        description=_(
            u"description_marketingauthorization_holder",
            default=u"Entity holding the authorization",
        ),
        required=False,
        max_length=255,
    )
    
    manufacturer = schema.TextLine(
        title=_(
            u"label_marketingauthorization_manufacturer",
            default=u"Manufacturer",
        ),
        description=_(
            u"description_marketingauthorization_manufacturer",
            default=u"Entity that manufactured the product",
        ),
        required=False,
        max_length=255,
    )


@implementer(IMarketingAuthorization, IMarketingAuthorizationSchema)
class MarketingAuthorization(Container):
    """Marketing Authorization content type"""
    _catalogs = [HOCHLIMS_CATALOG]
    security = ClassSecurityInfo()

    @security.protected(permissions.View)
    def Title(self):
        """Dynamic title for display"""
        parts = [self.getRegistrationNumber(), self.getTradeName()]
        return " ".join(filter(None, parts))
    
    @security.protected(permissions.View)
    def Description(self):
        """Dynamic description for display"""
        parts = [self.getRegistrationNumber(), self.getTradeName(), self.getDosageForm()]
        return " ".join(filter(None, parts))

    @security.protected(permissions.View)
    def getRegistrationNumber(self):
        """Returns the registration number with the field accessor
        """
        accessor = self.accessor("registration_number")
        return accessor(self)

    @security.protected(permissions.View)
    def getAbbreviatedRegistration(self):

        accessor = self.accessor("abbreviated_registration")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getTradeName(self):

        accessor = self.accessor("trade_name")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getDosageForm(self):

        accessor = self.accessor("dosage_form")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getGenericName(self):

        accessor = self.accessor("generic_name")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getTherapeuticActions(self):

        accessor = self.accessor("therapeutic_actions")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getAtqCode(self):

        accessor = self.accessor("atq_code")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getSaleCondition(self):

        accessor = self.accessor("sale_condition")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getAdministrationRoute(self):

        accessor = self.accessor("administration_route")
        return accessor(self)

    @security.protected(permissions.View)
    def getMedicineCode(self):

        accessor = self.accessor("medicine_code")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getProductLine(self):

        accessor = self.accessor("product_line")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getRegisteredPresentations(self):

        accessor = self.accessor("registered_presentations")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getStorageConditions(self):

        accessor = self.accessor("storage_conditions")
        return accessor(self)

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
        return accessor(self)
    
    @security.protected(permissions.View)
    def getIssueDate(self):
        accessor = self.accessor("issue_date")
        value = accessor(self)
        if dtime.is_dt(value):
            return value.date()
        return value

    @security.protected(permissions.View)
    def getLocalizedIssueDate(self):
        date = dtime.to_DT(self.getIssueDate())
        return dtime.to_localized_time(date)
    
    @security.protected(permissions.View)
    def getIssuingOrganization(self):
        accessor = self.accessor("issuing_organization")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getManufacturer(self):
        accessor = self.accessor("manufacturer")
        return accessor(self)
    
    @security.protected(permissions.View)
    def getShelfLife(self):
        accessor = self.accessor("shelf_life")
        return accessor(self)