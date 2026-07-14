# -*- coding: utf-8 -*-
from bika.lims import api
from DateTime import DateTime
from hoch.lims import logger


def after_start_phase1(investigation):
    """Set investigation start date and phase after starting Phase I."""
    logger.info("after_start_phase1: %s", api.get_id(investigation))
    investigation.investigation_start_date = DateTime()
    investigation.investigation_phase = u"phase_1"
    investigation.reindexObject()


def after_escalate_phase2(investigation):
    """Set Phase II start date and update phase."""
    logger.info("after_escalate_phase2: %s", api.get_id(investigation))
    investigation.phase2_start_date = DateTime()
    investigation.investigation_phase = u"phase_2"
    investigation.reindexObject()


def after_approve(investigation):
    """Set completion date and reviewer on approval."""
    logger.info("after_approve: %s", api.get_id(investigation))
    investigation.completion_date = DateTime()
    investigation.reviewer = api.get_current_user().getId()
    investigation.reindexObject()
