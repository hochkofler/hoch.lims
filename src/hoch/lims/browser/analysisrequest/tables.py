# -*- coding: utf-8 -*-
from bika.lims.browser.analysisrequest.tables import FieldAnalysesTable as BaseFieldAnalysesTable
from bika.lims.browser.analysisrequest.tables import LabAnalysesTable as BaseLabAnalysesTable
from bika.lims.browser.analysisrequest.tables import QCAnalysesTable as BaseQCAnalysesTable
from hoch.lims.browser.analyses.mixin import SubInstrumentsConsumablesMixin


class LabAnalysesTable(SubInstrumentsConsumablesMixin, BaseLabAnalysesTable):
    """Lab Analyses table with Sub-Instruments and Consumables support."""


class FieldAnalysesTable(SubInstrumentsConsumablesMixin, BaseFieldAnalysesTable):
    """Field Analyses table with Sub-Instruments and Consumables support."""


class QCAnalysesTable(SubInstrumentsConsumablesMixin, BaseQCAnalysesTable):
    """QC Analyses table with Sub-Instruments and Consumables support."""
