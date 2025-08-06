from AccessControl import ClassSecurityInfo
from plone.autoform import directives
from Products.CMFCore import permissions
from plone.supermodel import model
import zope.schema as schema
from hoch.lims import messageFactory as _
from senaite.core.api import dtime
from senaite.core.content.base import Container
from hoch.lims.interfaces import IMarketingAuthorization
from hoch.lims.content.fields import DatetimeField, DatetimeWidget
from zope.interface import implementer
from hoch.lims.catalog import HOCHLIMS_CATALOG
from hoch.lims.api import hochlims_search
from datetime import date
from zope.interface import invariant
from zope.interface import Invalid


class IMarketingAuthorizationSchema(model.Schema):
    """Marketing Authorization Schema"""

    directives.omitted("title")
    title = schema.TextLine(title="Title", required=False)

    directives.omitted("description")
    description = schema.Text(title="Description", required=False)

    issuing_organization = schema.Choice(
        title=_(
            "label_marketingauthorization_issuing_organization",
            default="Issuing Regulatory Authority",
        ),
        description=_(
            "description_marketingauthorization_issuing_organization",
            default="Authority that issued the certification",
        ),
        source="hoch.lims.vocabularies.regulatory_authorities",
        required=True,
    )

    registration_number = schema.TextLine(
        title=_(
            "label_marketingauthorization_registration_number",
            default="Marketing Authorization Number",
        ),
        description=_(
            "description_marketingauthorization_registration_number",
            default="Unique identifier assigned by the authority",
        ),
        required=True,
        max_length=50,
    )

    trade_name = schema.TextLine(
        title=_(
            "label_marketingauthorization_trade_name",
            default="Trade Name (Brand)",
        ),
        description=_(
            "description_marketingauthorization_trade_name",
            default="Commercial name under which the product is sold",
        ),
        required=True,
        max_length=255,
    )

    generic_name = schema.TextLine(
        title=_(
            "label_marketingauthorization_generic_name",
            default="Generic Name",
        ),
        description=_(
            "description_marketingauthorization_generic_name",
            default="Non-proprietary name or chemical name given to a drug",
        ),
        required=True,
        max_length=255,
    )

    dosage_form = schema.Choice(
        title=_(
            "label_marketingauthorization_dosage_form",
            default="Dosage Form",
        ),
        description=_(
            "description_marketingauthorization_dosage_form",
            default="Form in which the product is administered",
        ),
        source="hoch.lims.vocabularies.dosage_forms",
        required=True,
    )

    product_line = schema.Choice(
        title=_(
            "label_marketingauthorization_product_line",
            default="Product Line",
        ),
        description=_(
            "description_marketingauthorization_product_line",
            default="Product line or category",
        ),
        source="hoch.lims.vocabularies.product_lines",
        required=False,
    )

    registered_presentations = schema.List(
        title=_(
            "label_marketingauthorization_registered_presentations",
            "Registered Presentations",
        ),
        value_type=schema.TextLine(),
        required=True,
    )

    therapeutic_actions = schema.List(
        title=_(
            "label_marketingauthorization_therapeutic_actions",
            default="Therapeutic Indications",
        ),
        description=_(
            "description_marketingauthorization_therapeutic_actions",
            default="List of approved therapeutic uses",
        ),
        value_type=schema.Choice(
            source="hoch.lims.vocabularies.therapeutic_indications"
        ),
        required=True,
    )

    atq_code = schema.TextLine(
        title=_(
            "label_marketingauthorization_atq_code",
            default="A.T.Q. Code",
        ),
        description=_(
            "description_marketingauthorization_atq_code",
            default="Anatomical Therapeutic Chemical classification code",
        ),
        required=False,
    )

    medicine_code = schema.TextLine(
        title=_(
            "label_marketingauthorization_medicine_code",
            default="Medicine Code",
        ),
        required=False,
    )

    sale_condition = schema.Choice(
        title=_(
            "label_marketingauthorization_sale_condition",
            default="Sale Condition",
        ),
        description=_(
            "description_marketingauthorization_sale_condition",
            default="Conditions under which the product may be sold",
        ),
        source="hoch.lims.vocabularies.sale_conditions",
        required=True,
    )

    storage_conditions = schema.Choice(
        title=_(
            "label_marketingauthorization_storage_conditions",
            default="Storage Conditions",
        ),
        description=_(
            "description_marketingauthorization_storage_conditions",
            default="Conditions under which the product may be stored",
        ),
        source="hoch.lims.vocabularies.storage_conditions",
        required=True,
    )

    administration_route = schema.Choice(
        title=_(
            "label_marketingauthorization_administration_route",
            default="Route of Administration",
        ),
        description=_(
            "description_marketingauthorization_administration_route",
            default="How the product is administered",
        ),
        source="hoch.lims.vocabularies.administration_routes",
        required=True,
    )

    directives.widget("issue_date", DatetimeWidget, show_time=False)

    issue_date = DatetimeField(
        title=_(
            "label_marketingauthorization_issue_date",
            default="Issue Date",
        ),
        description=_(
            "description_marketingauthorization_issue_date",
            default="Date when the authorization was issued",
        ),
        required=True,
    )

    directives.widget("expiration_date", DatetimeWidget, show_time=False)

    expiration_date = DatetimeField(
        title=_(
            "label_marketingauthorization_expiration_date",
            default="Expiration Date",
        ),
        description=_(
            "description_marketingauthorization_expiration_date",
            default="Date when the authorization expires",
        ),
        required=True,
    )

    shelf_life = schema.Int(
        title=_(
            "label_marketingauthorization_shelf_life",
            default="Shelf Life (months)",
        ),
        description=_(
            "description_marketingauthorization_shelf_life",
            default="Product stability period",
        ),
        required=True,
        min=1,
        max=120,  # 10 years
    )

    holder = schema.TextLine(
        title=_(
            "label_marketingauthorization_holder",
            default="Marketing Authorization Holder",
        ),
        description=_(
            "description_marketingauthorization_holder",
            default="Entity holding the authorization",
        ),
        required=False,
        max_length=255,
    )

    manufacturer = schema.TextLine(
        title=_(
            "label_marketingauthorization_manufacturer",
            default="Manufacturer",
        ),
        description=_(
            "description_marketingauthorization_manufacturer",
            default="Entity that manufactured the product",
        ),
        required=False,
        max_length=255,
    )

    @invariant
    def validate_registration_number(data):
        """Checks if the registration_number is unique"""
        # https://community.plone.org/t/dexterity-unique-field-validation
        context = getattr(data, "__context__", None)
        if context is not None:
            if context.registration_number == data.registration_number:
                # nothing changed
                return
        index_name = "mktauth_registration_number"
        brains = hochlims_search({index_name: data.registration_number})
        if brains:
            raise Invalid(
                _(
                    "error_marketingauthorization_registration_number_unique",
                    default="Registration number must be unique.",
                )
            )


@implementer(IMarketingAuthorization, IMarketingAuthorizationSchema)
class MarketingAuthorization(Container):
    """Marketing Authorization content type"""

    _catalogs = [HOCHLIMS_CATALOG]
    security = ClassSecurityInfo()

    @security.protected(permissions.View)
    def Title(self):
        # get parts as unicode
        reg = self.getRegistrationNumber()
        name = self.getTradeName()
        return " ".join(filter(None, (reg, name)))

    @security.protected(permissions.View)
    def Description(self):
        reg = self.getRegistrationNumber()
        name = self.getTradeName()
        form = self.getDosageForm()
        generic = self.getGenericName()
        return " ".join(filter(None, (reg, name, form, generic)))

    @security.protected(permissions.View)
    def getRegistrationNumber(self):
        """Returns the registration number with the field accessor"""
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
        """Returns the expiration date with the field accessor"""
        accessor = self.accessor("expiration_date")
        value = accessor(self)
        # Return a plain date object to avoid timezone issues
        # TODO Convert to current timezone and keep it as datetime instead!
        if dtime.is_dt(value) and as_date:
            value = value.date()
        return value

    @security.protected(permissions.View)
    def getLocalizedExpirationDate(self):
        """Returns the Expiration Date with the field accessor"""
        date = dtime.to_DT(self.getExpirationDate())
        return dtime.to_localized_time(date)

    @security.protected(permissions.View)
    def getHolder(self):
        """Returns the holder with the field accessor"""
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

    @security.protected(permissions.View)
    def getIsExpired(self):
        today = date.today()
        validfrom = getIssueDate()
        validto = getExpirationDate()
        if not validfrom or not validto:
            return True
        validfrom = validfrom.asdatetime().date()
        validto = validto.asdatetime().date()
        return not (today >= validfrom and today <= validto)
