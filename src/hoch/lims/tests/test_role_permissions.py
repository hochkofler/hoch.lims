# -*- coding: utf-8 -*-

from bika.lims import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

from hoch.lims.tests.base import SimpleTestCase
from hoch.lims.patches.worksheet_permissions import WORKSHEET_PERMISSIONS
from senaite.core.permissions.worksheet import can_add_worksheet


BATCH_ROLES = {
    "close": ("LabManager", "Manager"),
    "release": (
        "LabManager", "Manager", "RegulatoryPharmacist"),
    "reopen": ("LabManager", "Manager"),
}

OOS_ROLES = {
    "start_phase1": ("Analyst", "LabManager", "Manager"),
    "escalate_phase2": ("Analyst", "LabManager", "Manager"),
    "resolve_lab_error": ("Analyst", "LabManager", "Manager"),
    "cancel": ("LabManager", "Manager"),
    "submit_for_review": ("LabManager", "Manager"),
    "approve": (
        "LabManager", "Manager", "RegulatoryPharmacist"),
    "reject_review": (
        "LabManager", "Manager", "RegulatoryPharmacist"),
}

OOS_EDIT_ROLES = {
    "recorded": ("Analyst", "LabManager", "Manager"),
    "phase1": ("Analyst", "LabManager", "Manager"),
    "phase2": ("LabManager", "Manager"),
    "review": ("LabManager", "Manager"),
    "closed": ("LabManager", "Manager"),
    "cancelled": ("LabManager", "Manager"),
}

OOS_EDIT_PERMISSIONS = (
    "Modify portal content",
    "hoch.lims: Edit OOSInvestigation",
)


class TestInstalledRolePermissions(SimpleTestCase):

    def get_workflow(self, workflow_id):
        return self.portal.portal_workflow.getWorkflowById(workflow_id)

    def permission_roles(self, permission):
        return tuple(sorted(
            item["name"]
            for item in self.portal.rolesOfPermission(permission)
            if item["selected"]))

    def set_test_role(self, role):
        setRoles(self.portal, TEST_USER_ID, [role])

    def transition_ids(self, obj):
        return set(
            transition["id"]
            for transition in api.get_transitions_for(obj))

    def create_oos(self):
        return api.create(
            self.portal.OOSInvestigations, "OOSInvestigation")

    def create_review_oos(self, investigator="investigator-1"):
        self.set_test_role("LabManager")
        investigation = self.create_oos()
        api.do_transition_for(investigation, "start_phase1")
        investigation.phase1_summary = u"Laboratory checks complete"
        api.do_transition_for(investigation, "escalate_phase2")
        investigation.conclusion = u"Confirmed OOS"
        investigation.disposition = u"reject_batch"
        investigation.oos_category = u"confirmed"
        investigation.investigator = investigator
        api.do_transition_for(investigation, "submit_for_review")
        return investigation

    def test_batch_transitions_have_exact_role_guards(self):
        workflow = self.get_workflow("hoch_batch_workflow")

        for transition_id, expected in BATCH_ROLES.items():
            guard = workflow.transitions[transition_id].guard
            self.assertEqual(
                tuple(sorted(expected)),
                tuple(sorted(guard.roles)),
                transition_id)

    def test_batch_transitions_preserve_permissions_and_release_guard(self):
        workflow = self.get_workflow("hoch_batch_workflow")

        self.assertEqual(
            ("Modify portal content",),
            workflow.transitions["close"].guard.permissions)
        self.assertEqual(
            ("Modify portal content",),
            workflow.transitions["reopen"].guard.permissions)
        release_guard = workflow.transitions["release"].guard
        self.assertEqual(
            ("hoch.lims: Release Batch",),
            release_guard.permissions)
        self.assertEqual(
            "python:here.guard_release_batch()",
            release_guard.expr.text)

    def test_oos_transitions_have_exact_role_guards(self):
        workflow = self.get_workflow("oos_investigation_workflow")

        for transition_id, expected in OOS_ROLES.items():
            guard = workflow.transitions[transition_id].guard
            self.assertEqual(
                tuple(sorted(expected)),
                tuple(sorted(guard.roles)),
                transition_id)
            self.assertEqual(
                ("hoch.lims: Transition OOSInvestigation",),
                guard.permissions,
                transition_id)

    def test_oos_transitions_preserve_business_guard_expressions(self):
        workflow = self.get_workflow("oos_investigation_workflow")
        expected = {
            "escalate_phase2":
                'python:here.guard_handler("escalate_phase2")',
            "submit_for_review":
                'python:here.guard_handler("submit_for_review")',
            "approve": 'python:here.guard_handler("approve")',
        }

        for transition_id, expression in expected.items():
            self.assertEqual(
                expression,
                workflow.transitions[transition_id].guard.expr.text)

    def test_oos_states_have_exact_edit_roles(self):
        workflow = self.get_workflow("oos_investigation_workflow")

        for state_id, expected in OOS_EDIT_ROLES.items():
            state = workflow.states[state_id]
            for permission in OOS_EDIT_PERMISSIONS:
                info = state.getPermissionInfo(permission)
                self.assertEqual(0, info["acquired"])
                self.assertEqual(
                    tuple(sorted(expected)),
                    tuple(sorted(info["roles"])),
                    "{}:{}".format(state_id, permission))

    def test_root_permissions_support_approved_roles(self):
        self.assertEqual(
            (
                "LabManager",
                "Manager",
                "RegulatoryPharmacist",
            ),
            self.permission_roles("hoch.lims: Release Batch"))
        self.assertEqual(
            (
                "Analyst",
                "LabManager",
                "Manager",
                "RegulatoryPharmacist",
            ),
            self.permission_roles(
                "hoch.lims: Transition OOSInvestigation"))

    def test_labclerk_has_all_global_and_local_worksheet_permissions(self):
        for context in (self.portal, self.portal.worksheets):
            for permission in WORKSHEET_PERMISSIONS:
                roles = tuple(sorted(
                    item["name"]
                    for item in context.rolesOfPermission(permission)
                    if item["selected"]))
                self.assertIn("LabClerk", roles, permission)

    def test_labclerk_can_create_worksheet_from_samples_context(self):
        self.set_test_role("LabClerk")

        self.assertTrue(can_add_worksheet(self.portal))

    def test_initial_oos_transition_is_authorized_by_effective_role(self):
        investigation = self.create_oos()
        expected = {
            "Analyst": True,
            "LabManager": True,
            "Manager": True,
            "RegulatoryPharmacist": False,
        }

        for role, allowed in expected.items():
            self.set_test_role(role)
            self.assertEqual(
                allowed,
                "start_phase1" in self.transition_ids(investigation),
                role)

    def test_review_transitions_are_authorized_by_effective_role(self):
        investigation = self.create_review_oos()
        expected = {
            "Analyst": False,
            "LabManager": True,
            "Manager": True,
            "RegulatoryPharmacist": True,
        }

        for role, allowed in expected.items():
            self.set_test_role(role)
            transitions = self.transition_ids(investigation)
            self.assertEqual(
                allowed, "approve" in transitions, role)
            self.assertEqual(
                allowed, "reject_review" in transitions, role)

    def test_allowed_reviewer_cannot_approve_own_investigation(self):
        investigation = self.create_review_oos(
            investigator=TEST_USER_ID)

        for role in (
                "LabManager", "Manager", "RegulatoryPharmacist"):
            self.set_test_role(role)
            transitions = self.transition_ids(investigation)
            self.assertNotIn("approve", transitions, role)
            self.assertIn("reject_review", transitions, role)

        investigation.investigator = "investigator-2"
        for role in (
                "LabManager", "Manager", "RegulatoryPharmacist"):
            self.set_test_role(role)
            self.assertIn(
                "approve", self.transition_ids(investigation), role)


def test_suite():
    import unittest2 as unittest
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestInstalledRolePermissions)
