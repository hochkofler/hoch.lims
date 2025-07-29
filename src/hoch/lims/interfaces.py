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

class IHochLimsCatalog(ISenaiteCatalogObject):
    """Marker interface for HochLims Catalog
    """
