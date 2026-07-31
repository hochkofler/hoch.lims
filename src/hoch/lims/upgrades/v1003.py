# -*- coding: utf-8 -*-

from hoch.lims import logger
from hoch.lims.patches.worksheet_permissions import WORKSHEET_PERMISSIONS
from hoch.lims.patches.worksheet_permissions import (
    synchronize_worksheet_permissions)


PROFILE_ID = "profile-hoch.lims:default"


def upgrade(portal_setup):
    """Restore LabClerk worksheet permissions on an existing site."""
    context = portal_setup._getImportContext(PROFILE_ID)
    synchronize_worksheet_permissions(context.getSite())
    logger.info("Restored LabClerk worksheet permissions")
