# -*- coding: utf-8 -*-
"""Re-sync interim flags between AnalysisServices and their Analyses.

`RecordsField` only stores the interim subfields present in the request, so
an unchecked checkbox on the AnalysisService edit form leaves `hidden`,
`report` and `wide` *absent* from the stored record.  When
`setCalculation` merged the service interims with the Calculation's, a
missing key was read as "the service has no opinion" and the Calculation's
own value won.  For interims such as `potencia_declarada_m` -- hidden on the
Calculation, visible and pre-filled on the service -- the analyst ended up
with an analysis where the declared potency was invisible.

This upgrade:

1. Normalises the stored interim records of every AnalysisService so the
   three checkbox subfields are always present as real booleans.
2. Re-applies the service overrides on the interims of every analysis that
   is still awaiting results, so already-created samples show the fields.

Analyses that are past result entry (to_be_verified, verified, published,
retracted, rejected, cancelled) are deliberately left untouched: their
records are part of the audit trail.
"""

from bika.lims import api
from hoch.lims import logger
from hoch.lims.patches.analysis import SERVICE_BOOLEAN_KEYS
from hoch.lims.patches.analysis import SERVICE_OVERRIDE_KEYS
from hoch.lims.patches.analysis import _normalize_service_interim

PROFILE_ID = "profile-hoch.lims:default"

# Analyses in these states are still awaiting result entry, so refreshing
# their interim display flags cannot alter any recorded outcome.
EDITABLE_STATES = ("registered", "unassigned", "assigned")


def normalize_service_interims(portal):
    """Make the checkbox subfields explicit on every AnalysisService."""
    total = 0
    services = portal.bika_setup.bika_analysisservices.objectValues()
    for service in services:
        interims = service.getInterimFields() or []
        if not any(k not in i for i in interims for k in SERVICE_BOOLEAN_KEYS):
            continue
        service.setInterimFields([_normalize_service_interim(i)
                                  for i in interims])
        total += 1
        logger.info("Normalized interims of %s", api.get_path(service))
    return total


def resync_analysis_interims(portal):
    """Re-apply service interim overrides on analyses awaiting results."""
    catalog = api.get_tool("senaite_catalog_analysis")
    brains = catalog.unrestrictedSearchResults(
        portal_type="Analysis", review_state=EDITABLE_STATES)
    total = 0
    for brain in brains:
        analysis = api.get_object(brain)
        service = api.get_object_by_uid(analysis.getRawAnalysisService(), None)
        if service is None:
            continue
        overrides = {i.get("keyword"): _normalize_service_interim(i)
                     for i in (service.getInterimFields() or [])}
        interims = analysis.getInterimFields() or []
        changed = False
        for interim in interims:
            override = overrides.get(interim.get("keyword"))
            if override is None:
                continue
            for key in SERVICE_OVERRIDE_KEYS:
                if key not in override or interim.get(key) == override[key]:
                    continue
                interim[key] = override[key]
                changed = True
        if not changed:
            continue
        analysis.setInterimFields(interims)
        total += 1
        logger.info("Re-synced interims of %s", api.get_path(analysis))
    return total


def upgrade(portal_setup):
    """Re-sync interim flags between AnalysisServices and their Analyses."""
    context = portal_setup._getImportContext(PROFILE_ID)
    portal = context.getSite()
    services = normalize_service_interims(portal)
    analyses = resync_analysis_interims(portal)
    logger.info(
        "Interim re-sync complete: %s services normalized, %s analyses fixed",
        services, analyses)
