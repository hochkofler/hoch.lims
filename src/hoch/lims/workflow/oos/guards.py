# -*- coding: utf-8 -*-
from bika.lims import api
from hoch.lims import logger


def guard_escalate_phase2(investigation):
    """Phase I must be documented before escalating to Phase II.
    Requires phase1_summary to be filled.
    """
    if not investigation.getPhase1Summary():
        logger.info(
            "guard_escalate_phase2 [REJECT] %s: Phase I summary is required",
            api.get_id(investigation))
        return False
    return True


def guard_submit_for_review(investigation):
    """Requires conclusion, disposition, and OOS category before submitting
    for QA review.
    """
    if not investigation.getConclusion():
        logger.info(
            "guard_submit_for_review [REJECT] %s: Conclusion is required",
            api.get_id(investigation))
        return False
    if not investigation.getDisposition():
        logger.info(
            "guard_submit_for_review [REJECT] %s: Disposition is required",
            api.get_id(investigation))
        return False
    if not investigation.getOosCategory():
        logger.info(
            "guard_submit_for_review [REJECT] %s: OOS Category is required",
            api.get_id(investigation))
        return False
    return True


def guard_approve(investigation):
    """Separation of duties: the reviewer/approver must be a different user
    than the investigator (FDA 21 CFR Part 211.192).
    """
    current_user = api.get_current_user().getId()
    investigator = investigation.getInvestigator()
    if investigator and current_user == investigator:
        logger.info(
            "guard_approve [REJECT] %s: Reviewer (%s) cannot be the same as "
            "investigator (%s)",
            api.get_id(investigation), current_user, investigator)
        return False
    return True
