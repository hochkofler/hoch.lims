# -*- coding: utf-8 -*-
from bika.lims.interfaces import IInstrument
from plone.indexer import indexer


@indexer(IInstrument)
def instrument_certificate_expiry_date(instance):
    return instance.getCertificateExpireDate() or None
