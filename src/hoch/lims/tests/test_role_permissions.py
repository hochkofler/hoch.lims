# -*- coding: utf-8 -*-

from hoch.lims.tests.base import SimpleTestCase


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


def test_suite():
    import unittest2 as unittest
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestInstalledRolePermissions)
