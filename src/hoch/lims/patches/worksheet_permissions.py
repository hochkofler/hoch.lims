# -*- coding: utf-8 -*-
"""Preserve HOCH worksheet permissions after SENAITE recalculations."""

from bika.lims import api
from senaite.core.permissions import AddWorksheet
from senaite.core.permissions import EditWorksheet
from senaite.core.permissions import ManageWorksheets
from senaite.core.subscribers import senaite_setup as core_setup


WORKSHEET_PERMISSIONS = (
    AddWorksheet,
    EditWorksheet,
    ManageWorksheets,
)


def synchronize_worksheet_permissions(portal=None):
    """Add LabClerk without discarding roles selected by SENAITE Core."""
    portal = portal or api.get_portal()
    folder = portal.worksheets

    for permission in WORKSHEET_PERMISSIONS:
        roles = set(
            info["name"]
            for info in folder.rolesOfPermission(permission)
            if info["selected"])
        roles.add("LabClerk")
        folder.manage_permission(
            permission,
            roles=tuple(sorted(roles)),
            acquire=1)

    folder.reindexObject()


def apply_worksheet_permissions_patch():
    """Run the Core recalculation before restoring HOCH permissions."""
    original = core_setup.update_worksheets_permissions
    if getattr(
            original, "_hoch_lims_worksheet_permissions_patch", False):
        return

    def update_worksheets_permissions(senaite_setup):
        original(senaite_setup)
        synchronize_worksheet_permissions()

    update_worksheets_permissions._hoch_lims_original = original
    update_worksheets_permissions._hoch_lims_worksheet_permissions_patch = True
    core_setup.update_worksheets_permissions = update_worksheets_permissions


apply_worksheet_permissions_patch()
