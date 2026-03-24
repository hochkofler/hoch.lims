# -*- coding: utf-8 -*-
"""Mixin for Sub-Instruments and Consumables support in analyses listing views.

Place this mixin FIRST in the MRO (before the base view class) so that:
  - __init__ initialises the extra columns AFTER the base __init__ runs
  - folderitem, folderitems and _on_method_change chain through super()

Usage::

    class MyView(SubInstrumentsConsumablesMixin, BaseAnalysesView):
        pass
"""

from collections import OrderedDict
from copy import deepcopy
from operator import itemgetter

from bika.lims import api
from bika.lims import logger
from bika.lims.interfaces import IAnalysis
from bika.lims.interfaces import IAnalysisService
from bika.lims.utils import get_link_for
from hoch.lims import messageFactory as _
from senaite.core.catalog import SENAITE_CATALOG
from senaite.core.permissions import FieldEditAnalysisResult


class SubInstrumentsConsumablesMixin(object):
    """Mixin that adds Sub-Instruments and Consumables columns to any
    analyses listing view that subclasses AnalysesView.
    """

    def __init__(self, context, request):
        super(SubInstrumentsConsumablesMixin, self).__init__(context, request)
        # Initialise after base __init__ has set up self.columns
        if not hasattr(self, "consumable_columns"):
            self.consumable_columns = OrderedDict()
        if "SubInstruments" not in self.columns:
            self.columns["SubInstruments"] = {
                "title": _("SubInstruments"),
                "ajax": True,
                "sortable": False,
                "toggle": True,
                "type": "multiselect",
            }

    # ------------------------------------------------------------------
    # Field access helpers (no method calls on AT content objects)
    # ------------------------------------------------------------------

    def _get_sub_instruments(self, obj):
        field = obj.getField("SubInstruments")
        return field.get(obj) if field else []

    def _get_raw_sub_instruments(self, obj):
        return [i.UID() for i in self._get_sub_instruments(obj)]

    def _get_allowed_sub_instruments(self, obj):
        if IAnalysisService.providedBy(obj):
            service = obj
        elif IAnalysis.providedBy(obj):
            service = obj.getAnalysisService()
        else:
            service = None
        if not service:
            return []
        field = service.getField("SubInstrumentsAllowed")
        return field.get(service) if field else []

    def _get_raw_allowed_sub_instruments(self, obj):
        return [api.get_uid(i) for i in self._get_allowed_sub_instruments(obj)]

    def _get_consumables(self, obj):
        field = obj.getField("ConsumablesFields")
        return field.get(obj) if field else []

    # ------------------------------------------------------------------
    # Vocabulary helpers
    # ------------------------------------------------------------------

    def get_sub_instruments_vocabulary(self, analysis, method=None):
        obj = self.get_object(analysis)
        subinstruments = self._get_allowed_sub_instruments(obj)

        if method is None:
            method = obj.getMethod()
        if method:
            method_instruments = method.getInstruments()
            subinstruments = list(set(subinstruments).intersection(method_instruments))

        is_qc = api.get_portal_type(obj) == "ReferenceAnalysis"
        vocab = []
        for si in subinstruments:
            uid = api.get_uid(si)
            title = api.safe_unicode(api.get_title(si))
            if si.isValid():
                vocab.append({"ResultValue": uid, "ResultText": title})
            elif is_qc:
                if si.isOutOfDate():
                    title = _(u"{} (Out of date)".format(title))
                vocab.append({"ResultValue": uid, "ResultText": title})
            elif si.isOutOfDate():
                title = _(u"{} (Out of date)".format(title))
                vocab.append({"disabled": True, "ResultValue": None, "ResultText": title})

        vocab = sorted(vocab, key=itemgetter("ResultText"))
        return [{"ResultValue": "", "ResultText": _("None")}] + vocab

    def get_consumables_vocabulary(self, analysis, keyword):
        if not keyword:
            return []
        catalog = api.get_tool(SENAITE_CATALOG)
        results = catalog({
            "portal_type": "ReferenceSample",
            "getReferenceDefinitionUID": keyword,
            "isValid": True,
            "review_state": "current",
            "is_active": True,
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        })
        return [{"ResultValue": api.get_uid(i), "ResultText": api.get_title(i)} for i in results]

    def get_formatted_consumable(self, consumable):
        raw_value = consumable.get("value")
        if not api.is_uid(raw_value):
            return raw_value
        obj = api.get_object_by_uid(raw_value, None)
        return (api.get_title(obj) or raw_value) if obj else raw_value

    # ------------------------------------------------------------------
    # Column requirement checks
    # ------------------------------------------------------------------

    def is_sub_instruments_required(self, analysis):
        obj = self.get_object(analysis)
        if self._get_raw_sub_instruments(obj):
            return True
        return len(self._get_raw_allowed_sub_instruments(obj)) > 0

    def is_sub_instruments_column_required(self, items):
        for item in items:
            obj = item.get("obj")
            if obj and self.is_sub_instruments_required(obj):
                return True
        return False

    def calculate_consumable_columns_position(self, review_state):
        columns = review_state.get("columns", [])
        if "Method" in columns:
            return columns.index("Method")
        if "Result" in columns:
            return columns.index("Result")
        return len(columns)

    # ------------------------------------------------------------------
    # Per-item rendering
    # ------------------------------------------------------------------

    def _folder_item_sub_instruments(self, analysis_brain, item):
        item["SubInstruments"] = ""
        is_editable = self.is_analysis_edition_allowed(analysis_brain)
        obj = self.get_object(analysis_brain)
        subinstruments = self._get_sub_instruments(obj)

        if is_editable:
            voc = self.get_sub_instruments_vocabulary(analysis_brain)
            item["SubInstruments"] = [i.UID() for i in subinstruments]
            item["choices"]["SubInstruments"] = voc
            item["allow_edit"].append("SubInstruments")
        elif subinstruments:
            links = [get_link_for(si, tabindex="-1") for si in subinstruments]
            names = [api.get_title(si) for si in subinstruments]
            item["replace"]["SubInstruments"] = "<br/>".join(links)
            item["SubInstruments"] = ", ".join(names)
        else:
            item["SubInstruments"] = _("Manual")

    def _folder_item_consumables(self, analysis_brain, item):
        obj = self.get_object(analysis_brain)
        consumables_fields = deepcopy(self._get_consumables(obj))
        is_editable = self.is_analysis_edition_allowed(analysis_brain)

        for consumable_field in consumables_fields:
            keyword = consumable_field.get("keyword", "")
            if not keyword:
                logger.error("Not valid consumable keyword: '%s'", consumable_field)
                continue
            consumable_brain = api.get_brain_by_uid(keyword)
            if not consumable_brain:
                logger.error("Not valid consumable brain for keyword: '%s'", keyword)
                continue
            consumable_title = api.get_title(consumable_brain)
            if not consumable_title:
                logger.error("Not valid consumable title for: '%s'", consumable_field)
                continue

            self.consumable_columns[keyword] = consumable_title
            consumable_value = consumable_field.get("value", "")
            item[keyword] = consumable_value

            if is_editable:
                if self.has_permission(FieldEditAnalysisResult, analysis_brain):
                    item["allow_edit"].append(keyword)
                voc = [{"ResultValue": "", "ResultText": ""}] + (
                    self.get_consumables_vocabulary(analysis_brain, keyword) or []
                )
                item.setdefault("choices", {})[keyword] = voc
                item[keyword] = consumable_value
            elif consumable_value:
                item[keyword] = self.get_formatted_consumable(consumable_field)
            else:
                item[keyword] = "-"

    # ------------------------------------------------------------------
    # Override lifecycle methods — chain through super()
    # ------------------------------------------------------------------

    def folderitem(self, obj, item, index):
        item = super(SubInstrumentsConsumablesMixin, self).folderitem(obj, item, index)
        self._folder_item_sub_instruments(obj, item)
        self._folder_item_consumables(obj, item)
        return item

    def _on_method_change(self, uid=None, value=None, item=None, **kw):
        item = super(SubInstrumentsConsumablesMixin, self)._on_method_change(
            uid=uid, value=value, item=item, **kw)
        if item is not None:
            obj = api.get_object_by_uid(uid, None)
            method = api.get_object_by_uid(value, None)
            if obj:
                sub_inst_vocab = self.get_sub_instruments_vocabulary(obj, method=method)
                item["choices"]["SubInstruments"] = sub_inst_vocab
        return item

    def folderitems(self):
        items = super(SubInstrumentsConsumablesMixin, self).folderitems()

        show_sub = self.is_sub_instruments_column_required(items)
        if "SubInstruments" in self.columns:
            self.columns["SubInstruments"]["toggle"] = show_sub

        for item in items:
            for field in self.consumable_columns:
                if field not in item:
                    item[field] = ""

        consumable_keys = list(self.consumable_columns.keys())
        for col_id in consumable_keys:
            if col_id not in self.columns:
                self.columns[col_id] = {
                    "title": self.consumable_columns[col_id],
                    "input_width": "6",
                    "sortable": False,
                    "toggle": True,
                    "ajax": True,
                }

        new_states = []
        for state in self.review_states:
            cols = state.get("columns", [])
            pos = self.calculate_consumable_columns_position(state)
            # Add consumable columns for all users (visibility is independent
            # of editability — non-admin users can still read the values)
            for col_id in consumable_keys:
                if col_id not in cols:
                    cols.insert(pos, col_id)
            # Add SubInstruments column after Instrument when required
            if show_sub and "SubInstruments" not in cols:
                if "Instrument" in cols:
                    cols.insert(cols.index("Instrument") + 1, "SubInstruments")
                else:
                    cols.insert(pos, "SubInstruments")
            state["columns"] = cols
            new_states.append(state)
        self.review_states = new_states

        if self.allow_edit:
            self.show_select_column = True

        return items
