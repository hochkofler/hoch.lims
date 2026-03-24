# -*- coding: utf-8 -*-
from bika.lims.browser.analyses.view import AnalysesView as BaseAnalysesView
from hoch.lims.browser.analyses.mixin import SubInstrumentsConsumablesMixin


class AnalysesView(SubInstrumentsConsumablesMixin, BaseAnalysesView):
    """AnalysesView extended with Sub-Instruments and Consumables columns."""
