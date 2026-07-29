# -*- coding: utf-8 -*-

from hoch.lims import logger


PROFILE_ID = "profile-hoch.lims:default"
WORKFLOW_ID = "oos_investigation_workflow"
GUARDED_TRANSITIONS = (
    "escalate_phase2",
    "submit_for_review",
    "approve",
)


def upgrade(portal_setup):
    """Connect the OOS business guards to the installed workflow."""
    context = portal_setup._getImportContext(PROFILE_ID)
    portal = context.getSite()
    workflow = portal.portal_workflow.getWorkflowById(WORKFLOW_ID)
    if workflow is None:
        raise ValueError("Missing workflow: {}".format(WORKFLOW_ID))

    for transition_id in GUARDED_TRANSITIONS:
        transition = workflow.transitions.get(transition_id)
        if transition is None:
            raise ValueError(
                "Missing transition {} in {}".format(
                    transition_id, WORKFLOW_ID))
        expression = 'python:here.guard_handler("{}")'.format(
            transition_id)
        transition.guard.changeFromProperties({
            "guard_expr": expression,
        })

    logger.info("Installed OOS workflow guard expressions")
