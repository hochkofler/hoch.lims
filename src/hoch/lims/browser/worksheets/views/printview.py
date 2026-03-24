# -*- coding: utf-8 -*-
from bika.lims import api
from bika.lims.utils import formatDecimalMark
from bika.lims.utils import get_client
from senaite.core.browser.worksheets.worksheet.printview import PrintView as BasePrintView


class PrintView(BasePrintView):
    """Custom PrintView that adds helper methods used by ws_template.pt."""

    def get_ws_status(self):
        """Returns the review state of the worksheet being rendered."""
        if self._current_ws_index < len(self._worksheets):
            ws = self._worksheets[self._current_ws_index]
            return api.get_workflow_status_of(ws)
        return ""

    def get_formatted_specs(self, analysis):
        """Returns formatted specifications string for the given analysis."""
        specs = analysis.getResultsRange()
        client = get_client(analysis)
        if client:
            decimalmark = client.getDecimalMark()
        else:
            decimalmark = self.get_default_decimal_mark()
        fs = ""
        if specs.get("min", None) and specs.get("max", None):
            fs = "%s - %s" % (specs["min"], specs["max"])
        elif specs.get("min", None):
            fs = "> %s" % specs["min"]
        elif specs.get("max", None):
            fs = "< %s" % specs["max"]
        return formatDecimalMark(fs, decimalmark)

    def get_consumables(self, an_obj):
        """Returns a list of dicts with consumable_obj and ref_definition_obj
        for each consumable assigned to the given analysis."""
        if an_obj is None:
            return []
        field = an_obj.getField("ConsumablesFields")
        if not field:
            return []
        consumables_fields = field.get(an_obj) or []
        result = []
        for cf in consumables_fields:
            keyword = cf.get("keyword", "")
            value = cf.get("value", "")
            if not keyword or not value:
                continue
            ref_def = api.get_object_by_uid(keyword, None)
            consumable = api.get_object_by_uid(value, None)
            if consumable and ref_def:
                result.append({
                    "consumable_obj": consumable,
                    "ref_definition_obj": ref_def,
                })
        return result

    def get_sub_instruments(self, an_obj):
        """Returns the sub-instruments assigned to the given analysis.
        Handles both AT (getSubInstruments) and DX (field accessor) objects.
        """
        if an_obj is None:
            return []
        # DX field access
        field = an_obj.getField("SubInstruments")
        if field is not None:
            return field.get(an_obj) or []
        # AT fallback
        getter = getattr(an_obj, "getSubInstruments", None)
        if callable(getter):
            return getter() or []
        return []

    def get_formatted_interim(self, interim):
        """Returns the formatted value of an interim field."""
        value = interim.get("value", "")
        if value is None:
            return ""
        return str(value)
