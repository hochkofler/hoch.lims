from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from bika.lims import api

@implementer(IVocabularyFactory)
class RegulatorsVocabulary(object):

    def __call__(self, context):

        regulators = api.get_registry_record(
            "hoch.lims.regulators")

        items = []
        for regulator in regulators:
            # note: the key will get the submitted value
            keyword = regulator.get("key")
            title = regulator.get("value")
            # value, token, title
            term = SimpleTerm(keyword, keyword, title)
            items.append(term)
        return SimpleVocabulary(items)


RegulatorsVocabularyFactory = RegulatorsVocabulary()