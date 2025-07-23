from plone.indexer import indexer
from hoch.lims.interfaces import IMarketingAuthorization


@indexer(IMarketingAuthorization)
def patient_identifier_keys(instance):
    """Return patient identifier keys
    """
    identifiers = instance.getIdentifiers()
    return map(lambda i: i.get("key"), identifiers)


@indexer(IMarketingAuthorization)
def mktauth_reg_number(instance):
    """Index registration number
    """
    return instance.getRegNumber()

@indexer(IMarketingAuthorization)
def mktauth_expiration_date(instance):
    """Index expiration date
    """
    return instance.getExpirationDate()

@indexer(IMarketingAuthorization)
def mktauth_holder(instance):
    """Index holder
    """
    return instance.getHolder()