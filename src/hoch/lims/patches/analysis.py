# -*- coding: utf-8 -*-
"""
Monkey patch for AbstractAnalysis.setCalculation to preserve service-level
interim field overrides (value, hidden, etc.) when merging with calculation
interims.

Background:
-----------
When an Analysis is created from an AnalysisService that has a linked
Calculation, `setCalculation` merges the Calculation's interim fields with the
service's own interim fields.  The upstream logic treats Calculation interims
as authoritative: if a keyword appears in both the Calculation and the
AnalysisService, only the Calculation's version is kept, discarding any
service-level customizations such as a custom `DefaultValue` (`value`) or a
different `hidden` flag.

This patch changes the merge so that service-level overrides for `value`,
`hidden`, `report`, `unit`, `title`, and `wide` are preserved for interims
that appear in both the Calculation and the AnalysisService.
"""

import copy
import json

from bika.lims import api
from bika.lims.content.abstractanalysis import _normalize_interim

# Fields on an interim dict that the AnalysisService is allowed to override
# relative to the Calculation's definition.
SERVICE_OVERRIDE_KEYS = ("value", "hidden", "report", "unit", "title", "wide")


def setCalculation(self, value):
    """Link a Calculation and snapshot its formula, imports and version.

    Same behaviour as the upstream method, except that service-level
    customisations of shared interims (same keyword in both the Calculation
    and the AnalysisService) are preserved for the keys listed in
    SERVICE_OVERRIDE_KEYS.
    """
    if value:
        calc = api.get_object(value)
        uid = api.get_uid(calc)
        formula = calc.getMinifiedFormula()
        imports = json.dumps(calc.getPythonImports() or [])
        version = api.get_version(calc) or 0
    else:
        uid = ""
        formula = ""
        imports = json.dumps([])
        version = 0

    self.getField("CalculationUID").set(self, uid)
    self.getField("CalculationFormula").set(self, formula)
    self.getField("CalculationImports").set(self, imports)
    self.getField("CalculationVersion").set(self, version)

    if not value:
        return

    # Build indexed lookup of service interims by keyword so we can apply
    # service-level overrides to shared interims.
    service_interims_by_kw = {
        i.get("keyword"): i
        for i in copy.deepcopy(self.getInterimFields())
    }

    calc_interims = [
        _normalize_interim(i)
        for i in copy.deepcopy(calc.getInterimFields())
    ]
    calc_keywords = {i.get("keyword") for i in calc_interims}

    # For interims shared between Calculation and AnalysisService, apply
    # the service overrides on top of the Calculation's definition.
    merged_interims = []
    for interim in calc_interims:
        kw = interim.get("keyword")
        svc_interim = service_interims_by_kw.get(kw)
        if svc_interim is not None:
            for key in SERVICE_OVERRIDE_KEYS:
                if key in svc_interim:
                    interim[key] = svc_interim[key]
        merged_interims.append(interim)

    # Append service-only interims (keywords not present in the Calculation).
    service_only = [
        i for kw, i in service_interims_by_kw.items()
        if kw not in calc_keywords
    ]

    self.setInterimFields(merged_interims + service_only)
