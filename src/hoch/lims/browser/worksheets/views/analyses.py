# -*- coding: utf-8 -*-
from senaite.core.browser.worksheets.worksheet.analyses_listing import AnalysesView as BaseWorksheetView
from hoch.lims.browser.analyses.mixin import SubInstrumentsConsumablesMixin


class AnalysesView(SubInstrumentsConsumablesMixin, BaseWorksheetView):
    """Worksheet AnalysesView extended with Sub-Instruments and Consumables."""
