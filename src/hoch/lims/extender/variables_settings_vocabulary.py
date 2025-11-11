from zope.interface import implementer
from zope.component import adapter
from Products.Archetypes import DisplayList
from hoch.lims.interfaces import IVariablesSettingsVocabularyProvider
from zope.interface import Interface
from bika.lims.interfaces import IReferenceSample, IReferenceSamplesFolder, IInstruments, IInstrument
from senaite.core.interfaces import ISupplier

@adapter(Interface)
@implementer(IVariablesSettingsVocabularyProvider)
class DefaultVariablesSettingsVocabularyProvider:
    """Fallback vocabulary provider"""

    def __init__(self, context):
        self.context = context

    def getVocabulary(self):
        return DisplayList((
            ('', ''),
            ('generic', 'Generic variable'),
        ))
        
@adapter(IReferenceSample)
@implementer(IVariablesSettingsVocabularyProvider)
class ReferenceSampleVariablesVocabulary:
    def __init__(self, context):
        self.context = context

    def getVocabulary(self):
        return DisplayList((
            ('', ''),
            ('concentration', 'Concentration'),
            ('sensitivity', 'Sensitivity'),
            ('other', 'Other'),
        ))


@adapter(IInstrument, IInstruments)
@implementer(IVariablesSettingsVocabularyProvider)
class InstrumentVariablesVocabulary:
    def __init__(self, context):
        self.context = context

    def getVocabulary(self):
        return DisplayList((
            ('', ''),
            ('weight', 'Weight'),
            ('water_filled_weight', 'Water Filled Weight'),
        ))
