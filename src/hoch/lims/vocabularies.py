from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from bika.lims import api

@implementer(IVocabularyFactory)
class BaseRegistryVocabulary(object):
    """Base class for registry-based vocabularies"""
    registry_key = None
    
    def __call__(self, context):
        items = api.get_registry_record(self.registry_key)
        terms = []
        for item in items:
            keyword = item.get("key")
            title = item.get("value")
            term = SimpleTerm(keyword, keyword, title)
            terms.append(term)
        return SimpleVocabulary(terms)

class RegulatoryAuthoritiesVocabularyFactory(BaseRegistryVocabulary):
    registry_key = "hoch.lims.regulatory_authorities"

class DosageFormsVocabularyFactory(BaseRegistryVocabulary):
    registry_key = "hoch.lims.dosage_forms"

class ProductLinesVocabularyFactory(BaseRegistryVocabulary):
    registry_key = "hoch.lims.product_lines"

class TherapeuticIndicationsVocabularyFactory(BaseRegistryVocabulary):
    registry_key = "hoch.lims.therapeutic_indications"

class SaleConditionsVocabularyFactory(BaseRegistryVocabulary):
    registry_key = "hoch.lims.sale_conditions"

class StorageConditionsVocabularyFactory(BaseRegistryVocabulary):
    registry_key = "hoch.lims.storage_conditions"

class AdministrationRoutesVocabularyFactory(BaseRegistryVocabulary):
    registry_key = "hoch.lims.administration_routes"