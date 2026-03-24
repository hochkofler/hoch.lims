# -*- coding: utf-8 -*-

from archetypes.schemaextender.interfaces import IBrowserLayerAwareExtender
from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaExtender
from bika.lims import api
from bika.lims.content.abstractbaseanalysis import AbstractBaseAnalysis
from bika.lims.interfaces import IAnalysis
from bika.lims.interfaces import IAnalysisService
from bika.lims.interfaces import IBaseAnalysis
from bika.lims.browser.widgets import RecordsWidget
from hoch.lims import messageFactory as _
from hoch.lims.content.fields import ExtConsumableFieldsFieldAT
from hoch.lims.content.fields import UIDReferenceFieldAT
from hoch.lims.interfaces import IHaveSubInstruments
from hoch.lims.interfaces import IHochLims
from Products.Archetypes.public import DisplayList
from Products.Archetypes.atapi import PicklistWidget
from Products.CMFCore.permissions import View
from senaite.core.permissions import FieldEditAnalysisResult
from zope.component import adapts
from zope.interface import classImplements
from zope.interface import implements


# ---------------------------------------------------------------------------
# Vocabulary classes implementing AT IVocabulary
# AT calls value.getDisplayList(instance) for IVocabulary-providing objects.
# This avoids adding methods to content classes (no monkey patching).
# ---------------------------------------------------------------------------

from Products.Archetypes.interfaces import IVocabulary as IATVocabulary


class SubInstrumentsAllowedVocabulary(object):
    """Vocabulary for SubInstrumentsAllowed on AnalysisService.

    Returns instruments reachable through the service's methods, or all
    available instruments when no methods are selected.
    """
    implements(IATVocabulary)

    def getDisplayList(self, instance):
        sub_instruments = []
        instruments_assigned = instance.getInstruments()
        methods = instance.getMethods()
        for method in methods:
            for instrument in method.getInstruments():
                if instrument in sub_instruments or instrument in instruments_assigned:
                    continue
                sub_instruments.append(instrument)
        if not methods:
            sub_instruments = instance.query_available_instruments()
        items = [(api.get_uid(i), api.get_title(i)) for i in sub_instruments]
        return DisplayList(items)

    def getVocabularyDict(self, instance):
        return dict(self.getDisplayList(instance).items())

    def isFlat(self):
        return True

    def showLeafsOnly(self):
        return True


class SubInstrumentsVocabulary(object):
    """Vocabulary for SubInstruments (default sub-instrument per analysis).

    For AnalysisService: shows the SubInstrumentsAllowed of that service.
    For Analysis instances: shows the SubInstrumentsAllowed of the linked service.
    """
    implements(IATVocabulary)

    def getDisplayList(self, instance):
        if IAnalysisService.providedBy(instance):
            allowed_field = instance.getField("SubInstrumentsAllowed")
            instruments = allowed_field.get(instance) if allowed_field else []
        else:
            service = instance.getAnalysisService() if IAnalysis.providedBy(instance) else None
            if service:
                allowed_field = service.getField("SubInstrumentsAllowed")
                instruments = allowed_field.get(service) if allowed_field else []
            else:
                instruments = []
        items = [(api.get_uid(i), api.get_title(i)) for i in instruments]
        return DisplayList(items).sortedByValue()

    def getVocabularyDict(self, instance):
        return dict(self.getDisplayList(instance).items())

    def isFlat(self):
        return True

    def showLeafsOnly(self):
        return True


# ---------------------------------------------------------------------------
# Schema extenders
# ---------------------------------------------------------------------------

class AbstractBaseAnalysisSchemaExtender(object):
    """Adds SubInstruments field to AbstractBaseAnalysis (IBaseAnalysis).

    This covers AnalysisService, RoutineAnalysis, ReferenceAnalysis, etc.
    """
    layer = IHochLims
    implements(ISchemaExtender, IBrowserLayerAwareExtender, IOrderableSchemaExtender)
    adapts(IBaseAnalysis)

    fields = [
        UIDReferenceFieldAT(
            "SubInstruments",
            read_permission=View,
            write_permission=FieldEditAnalysisResult,
            schemata="Method",
            multiValued=1,
            searchable=True,
            required=0,
            vocabulary=SubInstrumentsVocabulary(),
            allowed_types=("Instrument",),
            widget=PicklistWidget(
                format="select",
                label=_("Default Sub Instruments"),
                description=_("Default sub-instruments used for analyses of this type"),
            ),
        ),
    ]

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields

    def getOrder(self, original):
        method = original.get("Method", [])
        # Only reorder SubInstruments here when SubInstrumentsAllowed is absent
        # (i.e. non-AnalysisService types). For AnalysisService, the
        # AnalysisServiceSchemaExtender.getOrder() handles both fields.
        if ("SubInstruments" in method
                and "Instrument" in method
                and "SubInstrumentsAllowed" not in method):
            method.remove("SubInstruments")
            idx = method.index("Instrument")
            method.insert(idx + 1, "SubInstruments")
        return original


class AbstractAnalysisSchemaExtender(object):
    """Adds ConsumablesFields to AbstractAnalysis (IAnalysis).

    Covers RoutineAnalysis and ReferenceAnalysis.
    """
    layer = IHochLims
    implements(ISchemaExtender, IBrowserLayerAwareExtender)
    adapts(IAnalysis)

    fields = [
        ExtConsumableFieldsFieldAT(
            "ConsumablesFields",
            read_permission=View,
            write_permission=FieldEditAnalysisResult,
            schemata="Method",
            widget=RecordsWidget(
                label=_("Consumable Fields"),
            ),
        ),
    ]

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields


class AnalysisServiceSchemaExtender(object):
    """Adds SubInstrumentsAllowed and ConsumablesFields to AnalysisService."""

    layer = IHochLims
    implements(ISchemaExtender, IBrowserLayerAwareExtender, IOrderableSchemaExtender)
    adapts(IAnalysisService)

    fields = [
        UIDReferenceFieldAT(
            "SubInstrumentsAllowed",
            schemata="Method",
            required=0,
            multiValued=1,
            vocabulary=SubInstrumentsAllowedVocabulary(),
            allowed_types=("Instrument",),
            widget=PicklistWidget(
                label=_("SubInstruments Allowed"),
                description=_("Sub-instruments allowed based on the selected methods"),
            ),
        ),
        ExtConsumableFieldsFieldAT(
            "ConsumablesFields",
            schemata="Advanced",
            widget=RecordsWidget(
                label=_("Consumables setup"),
                description=_("Consumables required to perform this analysis service"),
            ),
        ),
    ]

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields

    def getOrder(self, original):
        method = original.get("Method", [])
        # 1) Place SubInstrumentsAllowed immediately after Instrument
        if "SubInstrumentsAllowed" in method and "Instrument" in method:
            method.remove("SubInstrumentsAllowed")
            idx = method.index("Instrument")
            method.insert(idx + 1, "SubInstrumentsAllowed")
        # 2) Place SubInstruments immediately after SubInstrumentsAllowed
        if "SubInstruments" in method and "SubInstrumentsAllowed" in method:
            method.remove("SubInstruments")
            idx = method.index("SubInstrumentsAllowed")
            method.insert(idx + 1, "SubInstruments")
        return original


# Apply IHaveSubInstruments to AbstractBaseAnalysis — standard zope.interface API
classImplements(AbstractBaseAnalysis, IHaveSubInstruments)
