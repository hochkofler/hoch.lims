from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from bika.lims import api

def registry_vocabulary_factory(registry_key):
    """Devuelve una IVocabularyFactory que lee de registry_key."""
    @implementer(IVocabularyFactory)
    class _RegistryVocabulary(object):
        def __call__(self, context):
            items = api.get_registry_record(registry_key) or []
            terms = []
            for item in items:
                keyword = item.get("key")
                title = item.get("value")
                term = SimpleTerm(keyword, keyword, title)
                terms.append(term)
            return SimpleVocabulary(terms)

    return _RegistryVocabulary()

RegulatoryAuthoritiesVocabularyFactory = registry_vocabulary_factory("hoch.lims.regulatory_authorities")
DosageFormsVocabularyFactory = registry_vocabulary_factory("hoch.lims.dosage_forms")
ProductLinesVocabularyFactory = registry_vocabulary_factory("hoch.lims.product_lines")
TherapeuticIndicationsVocabularyFactory = registry_vocabulary_factory("hoch.lims.therapeutic_indications")
SaleConditionsVocabularyFactory = registry_vocabulary_factory("hoch.lims.sale_conditions")
StorageConditionsVocabularyFactory = registry_vocabulary_factory("hoch.lims.storage_conditions")
AdministrationRoutesVocabularyFactory = registry_vocabulary_factory("hoch.lims.administration_routes")
PrimaryPresentationVocabularyFactory = registry_vocabulary_factory("hoch.lims.primary_presentations")
SecundaryPresentationVocabularyFactory = registry_vocabulary_factory("hoch.lims.secundary_presentations")
DosageUnitsVocabularyFactory = registry_vocabulary_factory("hoch.lims.dosage_units")