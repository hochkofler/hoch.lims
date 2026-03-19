# -*- coding: utf-8 -*-

from bika.lims.browser.worksheet.views.printview import PrintView as BasePrintView
from hoch.lims.utils import get_formatted_specs, get_formatted_interim
from hoch.lims import logger
from bika.lims import api
class PrintView(BasePrintView):
    """Extends Senaite PrintView without rewriting everything."""

    def get_ws_status(self):
        ws = None
        if self._current_ws_index < len(self._worksheets):
            ws = self._worksheets[self._current_ws_index]
        
        return api.get_workflow_status_of(ws) if ws else "unknown"
    
    def get_formatted_specs(self, analysis, with_shoulder_range=False,
                            lt_operator=None, leq_operator=None, 
                            gt_operator=None, geq_operator=None):
        """Get formatted specifications for an analysis using custom function."""
        return get_formatted_specs(analysis, with_shoulder_range=False,
                            lt_operator=None, leq_operator=None, 
                            gt_operator=None, geq_operator=None)
        
    def get_consumables(self, analysis):
        if not analysis:
            return []
        consumables_dict = []
        consumables_raw = analysis.getConsumablesFields()
        if not consumables_raw:
            return consumables_dict
        for consumable in consumables_raw:
            logger.info("consumable: '%s'", consumable)
            ref_definition_uid = consumable.get("keyword", '')
            consumable_uid = consumable.get("value", '')
            if not ref_definition_uid:
                continue
            ref_definition_obj = api.get_object_by_uid(ref_definition_uid)
            if not ref_definition_obj:
                continue
            if not consumable_uid:
                continue
            consumable_obj = api.get_object_by_uid(consumable_uid) or ''
            consumables_dict.append(
                {
                    "ref_definition_obj": ref_definition_obj,
                    "consumable_obj": consumable_obj,
                }
            )
        return consumables_dict
    
    def get_formatted_interim(self, interim):
        return get_formatted_interim(interim)