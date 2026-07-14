# -*- coding: utf-8 -*-

from bika.lims.interfaces import IBikaLIMS
from senaite.core.interfaces import ISenaiteCore
from zope.interface import Interface
from senaite.core.interfaces import ISenaiteCatalogObject


class IHochLims(IBikaLIMS, ISenaiteCore):
    """Marker interface that defines a Zope 3 browser layer.
    """

class IMarketingAuthorization(Interface):
    """Marker interface for Marketing Authorization content type
    """
class IMarketingAuthorizations(Interface):
    """Marker interface for Marketing Authorization folder
    """

class IPharmaceuticalProduct(Interface):
    """Marker interface for Pharmaceutical Product content type
    """

class IPharmaceuticalProducts(Interface):
    """Marker interface for Pharmaceutical Product folder
    """

class IProcessGroup(Interface):
    """Marker interface for Process Group
    """

class IProcess(Interface):
    """Marker interface for Process
    """

class IProcesses(Interface):
    """Marker interface for Processes folder
    """

class IProcessGroups(Interface):
    """Marker interface for Process Groups folder
    """

class IHochLimsCatalog(ISenaiteCatalogObject):
    """Marker interface for HochLims Catalog
    """
    
class IHaveSubInstruments(Interface):
    """Marker interface for objects that have sub Instrument(s) assigned"""

    def getSubInstruments():
        """Returns the sub instrument(s) the instance is assigned to"""


class IVariablesSettingsVocabularyProvider(Interface):
    """Provide the vocabulary for VariablesSettingsField keyword subfield"""

    def getVocabulary():
        """Return a DisplayList"""


class IOOSInvestigation(Interface):
    """Marker interface for OOS Investigation"""


class IOOSFolder(Interface):
    """Marker interface for OOS Investigations folder"""