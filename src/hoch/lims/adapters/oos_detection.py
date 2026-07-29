# -*- coding: utf-8 -*-
"""OOS auto-detection subscriber.

Listens for analysis workflow transitions (submit/verify) and automatically
creates an OOS Investigation when a result is out of specification.
"""
from bika.lims import api
from bika.lims.api.analysis import is_out_of_range
from DateTime import DateTime
from hoch.lims import logger
from hoch.lims.catalog import HOCHLIMS_CATALOG


def on_analysis_transition(analysis, event):
    """Subscriber for IAfterTransitionEvent on IRoutineAnalysis.

    Dispatches on submit/verify transitions to check for OOS results.
    """
    transition_id = event.transition.getId() if event.transition else None
    if transition_id not in ("submit", "verify"):
        return
    _check_and_create_oos(analysis)


def _check_and_create_oos(analysis):
    """Check if analysis result is out of range and create OOS investigation."""
    out_of_range, out_of_shoulders = is_out_of_range(analysis)
    if not out_of_range:
        return

    # Get the OOS folder
    portal = api.get_portal()
    oos_folder = portal.get("OOSInvestigations")
    if not oos_folder:
        logger.warn(
            "OOSInvestigations folder not found; cannot create OOS record.")
        return

    # Avoid duplicates: check if OOS already exists for this analysis UID
    analysis_uid = api.get_uid(analysis)
    catalog = api.get_tool(HOCHLIMS_CATALOG)
    existing = catalog(
        portal_type="OOSInvestigation",
        oos_analysis_uid=analysis_uid,
    )
    if existing:
        logger.info(
            "OOS investigation already exists for analysis %s",
            analysis_uid)
        return

    # Gather snapshot data
    result_value = str(analysis.getResult() or "")
    results_range = analysis.getResultsRange() or {}
    spec_str = u"min={}, max={}".format(
        results_range.get("min", ""),
        results_range.get("max", ""),
    )
    service_title = analysis.Title() or ""
    current_user = api.get_current_user().getId()

    # Calculate due date (30 calendar days per FDA guidance)
    detection = DateTime()
    due = detection + 30

    # Create the OOS Investigation
    try:
        oos = api.create(oos_folder, "OOSInvestigation")
        oos.analysis_uid = analysis_uid
        oos.detection_date = detection
        oos.due_date = due
        oos.result_value = result_value
        oos.specification_range = spec_str
        oos.analysis_service_title = service_title
        oos.responsible_analyst = current_user
        oos.reindexObject()
        logger.info(
            "Created OOS Investigation %s for analysis %s (result=%s)",
            api.get_id(oos), analysis.getId(), result_value)
        return oos
    except Exception as e:
        logger.error(
            "Failed to create OOS Investigation for analysis %s: %s",
            analysis_uid, str(e))
        raise
