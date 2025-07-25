from plone.indexer import indexer
from hoch.lims.interfaces import IMarketingAuthorization


@indexer(IMarketingAuthorization)
def patient_identifier_keys(instance):
    """Return patient identifier keys
    """
    identifiers = instance.getIdentifiers()
    return map(lambda i: i.get("key"), identifiers)

@indexer(IMarketingAuthorization)
def mktauth_registration_number(instance):
    return instance.getRegistrationNumber()

@indexer(IMarketingAuthorization)
def mktauth_expiration_date(instance):
    return instance.getExpirationDate()

@indexer(IMarketingAuthorization)
def mktauth_holder(instance):
    return instance.getHolder()

@indexer(IMarketingAuthorization)
def mktauth_trade_name(instance):
    value = instance.getTradeName()
    return value

@indexer(IMarketingAuthorization)
def mktauth_issuing_organization(instance):
    return instance.getIssuingOrganization()

@indexer(IMarketingAuthorization)
def mktauth_dosage_form(instance):
    return instance.getDosageForm()

@indexer(IMarketingAuthorization)
def mktauth_therapeutic_actions(instance):
    return instance.getTherapeuticActions()

@indexer(IMarketingAuthorization)
def mktauth_atq_code(instance):
    return instance.getAtqCode()

@indexer(IMarketingAuthorization)
def mktauth_sale_condition(instance):
    return instance.getSaleCondition()

@indexer(IMarketingAuthorization)
def mktauth_administration_route(instance):
    return instance.getAdministrationRoute()

@indexer(IMarketingAuthorization)
def mktauth_medicine_code(instance):
    return instance.getMedicineCode()

@indexer(IMarketingAuthorization)
def mktauth_product_line(instance):
    return instance.getProductLine()

@indexer(IMarketingAuthorization)
def mktauth_storage_conditions(instance):
    return instance.getStorageConditions()

@indexer(IMarketingAuthorization)
def mktauth_issue_date(instance):
    return instance.getIssueDate()

@indexer(IMarketingAuthorization)
def mktauth_manufacturer(instance):
    return instance.getManufacturer()

@indexer(IMarketingAuthorization)
def mktauth_shelf_life(instance):
    return instance.getShelfLife()

@indexer(IMarketingAuthorization)
def mktauth_abbreviated_registration(instance):
    return instance.getAbbreviatedRegistration()

@indexer(IMarketingAuthorization)
def mktauth_generic_name(instance):
    return instance.getGenericName()

@indexer(IMarketingAuthorization)
def mktauth_registered_presentations(instance):
    return instance.getRegisteredPresentations()