# -*- coding: utf-8 -*-

from hoch.lims import logger
from hoch.lims.setuphandlers import setup_behaviors


PROFILE_ID = "profile-hoch.lims:default"


def upgrade(portal_setup):
    """Enable the Dynamic exclusion behavior on AnalysisCategory."""
    context = portal_setup._getImportContext(PROFILE_ID)
    setup_behaviors(context.getSite())
    logger.info("Enabled Dynamic exclusion on AnalysisCategory")
