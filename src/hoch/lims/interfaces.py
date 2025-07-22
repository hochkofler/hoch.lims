# -*- coding: utf-8 -*-

from bika.lims.interfaces import IBikaLIMS
from senaite.core.interfaces import ISenaiteCore
from zope.interface import Interface


class IHochLims(IBikaLIMS, ISenaiteCore):
    """Marker interface that defines a Zope 3 browser layer.
    """

class IProduct(Interface):
    """Marker interface for product item
    """

class IProducts(Interface):
    """Marker interface for products main folder
    """
class IMarketingAuthorization(Interface):
    """Marker interface for Marketing Authorization content type
    """

class IPharmaceuticalProduct(Interface):
    """Marker interface for Pharmaceutical Product content type
    """
