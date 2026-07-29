# -*- coding: utf-8 -*-

from hoch.lims import logger


PROFILE_ID = "profile-hoch.lims:default"
BATCH_WORKFLOW_ID = "hoch_batch_workflow"
OOS_WORKFLOW_ID = "oos_investigation_workflow"

BATCH_TRANSITION_ROLES = {
    "close": ("LabManager", "Manager"),
    "release": (
        "LabManager",
        "Manager",
        "RegulatoryPharmacist",
    ),
    "reopen": ("LabManager", "Manager"),
}

OOS_TRANSITION_ROLES = {
    "start_phase1": ("Analyst", "LabManager", "Manager"),
    "escalate_phase2": ("Analyst", "LabManager", "Manager"),
    "resolve_lab_error": ("Analyst", "LabManager", "Manager"),
    "cancel": ("LabManager", "Manager"),
    "submit_for_review": ("LabManager", "Manager"),
    "approve": (
        "LabManager",
        "Manager",
        "RegulatoryPharmacist",
    ),
    "reject_review": (
        "LabManager",
        "Manager",
        "RegulatoryPharmacist",
    ),
}

OOS_EDIT_STATES = ("review", "closed", "cancelled")
OOS_EDIT_PERMISSIONS = (
    "Modify portal content",
    "hoch.lims: Edit OOSInvestigation",
)
OOS_TRANSITION_PERMISSION = \
    "hoch.lims: Transition OOSInvestigation"
OOS_TRANSITION_PERMISSION_ROLES = (
    "Analyst",
    "LabManager",
    "Manager",
    "RegulatoryPharmacist",
)


def _get_workflow(portal, workflow_id):
    workflow = portal.portal_workflow.getWorkflowById(workflow_id)
    if workflow is None:
        raise ValueError("Missing workflow: {}".format(workflow_id))
    return workflow


def _set_transition_roles(workflow, workflow_id, role_map):
    for transition_id, roles in role_map.items():
        transition = workflow.transitions.get(transition_id)
        if transition is None:
            raise ValueError(
                "Missing transition {} in {}".format(
                    transition_id, workflow_id))
        transition.guard.changeFromProperties({
            "guard_roles": ";".join(roles),
        })


def _set_oos_edit_permissions(workflow):
    for permission in OOS_EDIT_PERMISSIONS:
        if permission not in workflow.permissions:
            raise ValueError(
                "Missing managed permission {} in {}".format(
                    permission, OOS_WORKFLOW_ID))
    for state_id in OOS_EDIT_STATES:
        state = workflow.states.get(state_id)
        if state is None:
            raise ValueError(
                "Missing state {} in {}".format(
                    state_id, OOS_WORKFLOW_ID))
        for permission in OOS_EDIT_PERMISSIONS:
            state.setPermission(
                permission, 0, ("LabManager", "Manager"))


def upgrade(portal_setup):
    """Install the approved Batch and OOS role matrix."""
    context = portal_setup._getImportContext(PROFILE_ID)
    portal = context.getSite()
    batch_workflow = _get_workflow(portal, BATCH_WORKFLOW_ID)
    oos_workflow = _get_workflow(portal, OOS_WORKFLOW_ID)

    _set_transition_roles(
        batch_workflow,
        BATCH_WORKFLOW_ID,
        BATCH_TRANSITION_ROLES)
    _set_transition_roles(
        oos_workflow,
        OOS_WORKFLOW_ID,
        OOS_TRANSITION_ROLES)
    _set_oos_edit_permissions(oos_workflow)
    portal.manage_permission(
        OOS_TRANSITION_PERMISSION,
        roles=OOS_TRANSITION_PERMISSION_ROLES,
        acquire=0)

    logger.info("Installed Batch and OOS workflow role permissions")
