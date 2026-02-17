from Products.Archetypes.public import DisplayList
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

def getDestinationsVocabulary(self):
    factory = getUtility(
        IVocabularyFactory,
        name='hoch.lims.vocabularies.destinations'
    )
    vocab = factory(self)

    pairs = [(t.value, t.title) for t in vocab]
    return DisplayList(pairs)