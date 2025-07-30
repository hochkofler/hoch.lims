from plone.indexer import indexer
from hoch.lims.interfaces import IPharmaceuticalProduct

@indexer(IPharmaceuticalProduct)
def product_name(instance):
    return instance.getName()

@indexer(IPharmaceuticalProduct)
def product_code(instance):
    return instance.getCode()

@indexer(IPharmaceuticalProduct)
def product_description(instance):
    return instance.Description()

@indexer(IPharmaceuticalProduct)
def product_marketing_authorization(instance):
    """Return the marketing authorization of the pharmaceutical product."""
    ma = instance.getMarketingAuthorization()
    if ma:
        return ma.getRegistrationNumber()
    return None

@indexer(IPharmaceuticalProduct)
def product_presetnation(instance):
    """Return the primary presentation of the pharmaceutical product."""
    return instance.getPresentation()

@indexer(IPharmaceuticalProduct)
def product_primary_presentation(instance):
    """Return the primary presentation of the pharmaceutical product."""
    return instance.getPrimaryPresentation()

@indexer(IPharmaceuticalProduct)
def product_secundary_presentation(instance):
    """Return the secondary presentation of the pharmaceutical product."""
    return instance.getSecundaryPresentation()

@indexer(IPharmaceuticalProduct)
def product_dosage_unit_per_primary_presentation(instance):
    """Return the dosage unit per primary presentation."""
    return instance.getDosageUnitPerPrimaryPresentation()

@indexer(IPharmaceuticalProduct)
def product_dosage_unit_per_secundary_presentation(instance):
    """Return the dosage unit per secondary presentation."""
    return instance.getDosageUnitPerSecundaryPresentation()

