# -*- coding: utf-8 -*-

import unittest2 as unittest

from Products.DCWorkflow.Guard import Guard
from hoch.lims.upgrades import v1001
from hoch.lims.upgrades import v1002
from hoch.lims.upgrades import v1003
from hoch.lims.upgrades import v1004


PERMISSION = "hoch.lims: Transition OOSInvestigation"


class DummyTransition(object):

    def __init__(self):
        self.guard = Guard()
        self.guard.changeFromProperties({
            "guard_permissions": PERMISSION,
        })


class DummyTransitions(dict):

    def get(self, transition_id):
        return dict.get(self, transition_id)


class DummyWorkflow(object):

    def __init__(self):
        self.transitions = DummyTransitions(
            (transition_id, DummyTransition())
            for transition_id in v1001.GUARDED_TRANSITIONS)


class DummyWorkflowTool(object):

    def __init__(self, workflow):
        self.workflow = workflow

    def getWorkflowById(self, workflow_id):
        if workflow_id == v1001.WORKFLOW_ID:
            return self.workflow
        return None


class DummyPortal(object):

    def __init__(self, workflow):
        self.portal_workflow = DummyWorkflowTool(workflow)


class DummyContext(object):

    def __init__(self, portal):
        self.portal = portal

    def getSite(self):
        return self.portal


class DummyPortalSetup(object):

    def __init__(self, portal):
        self.portal = portal
        self.profile_ids = []

    def _getImportContext(self, profile_id):
        self.profile_ids.append(profile_id)
        return DummyContext(self.portal)


class RoleDummyTransition(object):

    def __init__(self):
        self.guard = Guard()
        self.guard.changeFromProperties({
            "guard_permissions": "Keep permission",
            "guard_expr": "python:True",
            "guard_groups": "KeepGroup",
            "guard_roles": "LegacyRole",
        })


class RoleDummyState(object):

    def __init__(self):
        self.permissions = {}

    def setPermission(self, permission, acquire, roles):
        self.permissions[permission] = (acquire, tuple(roles))


class RoleDummyWorkflow(object):

    def __init__(self, transition_roles):
        self.transitions = DummyTransitions(
            (transition_id, RoleDummyTransition())
            for transition_id in transition_roles)
        self.states = dict(
            (state_id, RoleDummyState())
            for state_id in v1002.OOS_EDIT_STATES)
        self.permissions = tuple(v1002.OOS_EDIT_PERMISSIONS)


class RoleDummyWorkflowTool(object):

    def __init__(self, workflows):
        self.workflows = workflows

    def getWorkflowById(self, workflow_id):
        return self.workflows.get(workflow_id)


class RoleDummyPortal(object):

    def __init__(self):
        self.batch_workflow = RoleDummyWorkflow(
            v1002.BATCH_TRANSITION_ROLES)
        self.oos_workflow = RoleDummyWorkflow(
            v1002.OOS_TRANSITION_ROLES)
        self.portal_workflow = RoleDummyWorkflowTool({
            v1002.BATCH_WORKFLOW_ID: self.batch_workflow,
            v1002.OOS_WORKFLOW_ID: self.oos_workflow,
        })
        self.managed_permissions = {}

    def manage_permission(self, permission, roles, acquire):
        self.managed_permissions[permission] = (
            tuple(roles), acquire)


class WorksheetDummyFolder(object):

    def __init__(self):
        self.selected_roles = {}
        self.managed_permissions = {}
        for permission in v1003.WORKSHEET_PERMISSIONS:
            self.selected_roles[permission] = ("LabManager", "Manager")

    def rolesOfPermission(self, permission):
        return [
            {"name": role, "selected": role in self.selected_roles[permission]}
            for role in ("LabClerk", "LabManager", "Manager")
        ]

    def manage_permission(self, permission, roles, acquire):
        roles = tuple(roles)
        self.selected_roles[permission] = roles
        self.managed_permissions[permission] = (roles, acquire)

    def reindexObject(self):
        pass

    def snapshot(self):
        return (
            dict(self.selected_roles),
            dict(self.managed_permissions),
        )


class WorksheetDummyPortal(object):

    def __init__(self):
        self.selected_roles = {}
        self.managed_permissions = {}
        for permission in v1003.WORKSHEET_PERMISSIONS:
            self.selected_roles[permission] = ("LabManager", "Manager")
        self.worksheets = WorksheetDummyFolder()

    def rolesOfPermission(self, permission):
        return [
            {"name": role, "selected": role in self.selected_roles[permission]}
            for role in ("LabClerk", "LabManager", "Manager")
        ]

    def manage_permission(self, permission, roles, acquire):
        roles = tuple(roles)
        self.selected_roles[permission] = roles
        self.managed_permissions[permission] = (roles, acquire)

    def snapshot(self):
        return (
            dict(self.selected_roles),
            dict(self.managed_permissions),
            self.worksheets.snapshot(),
        )


class TestOOSUpgrade(unittest.TestCase):

    def setUp(self):
        self.workflow = DummyWorkflow()
        self.portal = DummyPortal(self.workflow)
        self.portal_setup = DummyPortalSetup(self.portal)

    def snapshot(self):
        return tuple(
            (
                transition_id,
                self.workflow.transitions[transition_id].guard.expr.text,
                self.workflow.transitions[transition_id].guard.permissions,
                self.workflow.transitions[transition_id].guard.roles,
                self.workflow.transitions[transition_id].guard.groups,
            )
            for transition_id in v1001.GUARDED_TRANSITIONS)

    def test_upgrade_adds_guard_expressions_and_preserves_permissions(self):
        v1001.upgrade(self.portal_setup)

        self.assertEqual([v1001.PROFILE_ID], self.portal_setup.profile_ids)
        for transition_id in v1001.GUARDED_TRANSITIONS:
            guard = self.workflow.transitions[transition_id].guard
            self.assertEqual(
                'python:here.guard_handler("{}")'.format(
                    transition_id),
                guard.expr.text)
            self.assertEqual((PERMISSION,), guard.permissions)

    def test_upgrade_is_idempotent(self):
        v1001.upgrade(self.portal_setup)
        first = self.snapshot()

        v1001.upgrade(self.portal_setup)

        self.assertEqual(first, self.snapshot())

    def test_upgrade_rejects_missing_workflow(self):
        self.portal.portal_workflow.workflow = None

        with self.assertRaisesRegexp(
                ValueError, v1001.WORKFLOW_ID):
            v1001.upgrade(self.portal_setup)

    def test_upgrade_rejects_missing_transition(self):
        missing = v1001.GUARDED_TRANSITIONS[0]
        self.workflow.transitions.pop(missing)

        with self.assertRaisesRegexp(ValueError, missing):
            v1001.upgrade(self.portal_setup)


class TestRolePermissionsUpgrade(unittest.TestCase):

    def setUp(self):
        self.portal = RoleDummyPortal()
        self.portal_setup = DummyPortalSetup(self.portal)

    def snapshot(self):
        workflows = (
            (self.portal.batch_workflow,
             v1002.BATCH_TRANSITION_ROLES),
            (self.portal.oos_workflow,
             v1002.OOS_TRANSITION_ROLES),
        )
        transitions = tuple(
            (
                transition_id,
                workflow.transitions[transition_id].guard.permissions,
                workflow.transitions[transition_id].guard.expr.text,
                workflow.transitions[transition_id].guard.groups,
                workflow.transitions[transition_id].guard.roles,
            )
            for workflow, role_map in workflows
            for transition_id in role_map)
        states = tuple(
            (
                state_id,
                tuple(sorted(
                    self.portal.oos_workflow.states[
                        state_id].permissions.items())),
            )
            for state_id in v1002.OOS_EDIT_STATES)
        return transitions, states, self.portal.managed_permissions.copy()

    def test_upgrade_installs_exact_transition_roles(self):
        v1002.upgrade(self.portal_setup)

        self.assertEqual([v1002.PROFILE_ID], self.portal_setup.profile_ids)
        workflows = (
            (self.portal.batch_workflow,
             v1002.BATCH_TRANSITION_ROLES),
            (self.portal.oos_workflow,
             v1002.OOS_TRANSITION_ROLES),
        )
        for workflow, role_map in workflows:
            for transition_id, expected_roles in role_map.items():
                guard = workflow.transitions[transition_id].guard
                self.assertEqual(tuple(expected_roles), guard.roles)
                self.assertEqual(("Keep permission",), guard.permissions)
                self.assertEqual("python:True", guard.expr.text)
                self.assertEqual(("KeepGroup",), guard.groups)

    def test_upgrade_installs_edit_and_global_permissions(self):
        v1002.upgrade(self.portal_setup)

        expected = (0, ("LabManager", "Manager"))
        for state_id in v1002.OOS_EDIT_STATES:
            state = self.portal.oos_workflow.states[state_id]
            for permission in v1002.OOS_EDIT_PERMISSIONS:
                self.assertEqual(expected, state.permissions[permission])
        self.assertEqual(
            (
                v1002.OOS_TRANSITION_PERMISSION_ROLES,
                0,
            ),
            self.portal.managed_permissions[
                v1002.OOS_TRANSITION_PERMISSION])

    def test_upgrade_is_idempotent(self):
        v1002.upgrade(self.portal_setup)
        first = self.snapshot()

        v1002.upgrade(self.portal_setup)

        self.assertEqual(first, self.snapshot())

    def test_upgrade_rejects_missing_workflow(self):
        self.portal.portal_workflow.workflows.pop(
            v1002.BATCH_WORKFLOW_ID)

        with self.assertRaisesRegexp(
                ValueError, v1002.BATCH_WORKFLOW_ID):
            v1002.upgrade(self.portal_setup)

    def test_upgrade_rejects_missing_transition(self):
        missing = sorted(v1002.OOS_TRANSITION_ROLES)[0]
        self.portal.oos_workflow.transitions.pop(missing)

        with self.assertRaisesRegexp(ValueError, missing):
            v1002.upgrade(self.portal_setup)

    def test_upgrade_rejects_missing_state(self):
        missing = v1002.OOS_EDIT_STATES[0]
        self.portal.oos_workflow.states.pop(missing)

        with self.assertRaisesRegexp(ValueError, missing):
            v1002.upgrade(self.portal_setup)

    def test_upgrade_rejects_unmanaged_edit_permission(self):
        missing = v1002.OOS_EDIT_PERMISSIONS[0]
        self.portal.oos_workflow.permissions = (
            v1002.OOS_EDIT_PERMISSIONS[1],)

        with self.assertRaisesRegexp(ValueError, missing):
            v1002.upgrade(self.portal_setup)


class TestWorksheetPermissionsUpgrade(unittest.TestCase):

    def setUp(self):
        self.portal = WorksheetDummyPortal()
        self.portal_setup = DummyPortalSetup(self.portal)

    def test_restores_all_labclerk_worksheet_permissions(self):
        v1003.upgrade(self.portal_setup)

        self.assertEqual([v1003.PROFILE_ID], self.portal_setup.profile_ids)
        for permission in v1003.WORKSHEET_PERMISSIONS:
            self.assertEqual(
                (("LabClerk", "LabManager", "Manager"), 1),
                self.portal.worksheets.managed_permissions[permission])

    def test_is_idempotent(self):
        v1003.upgrade(self.portal_setup)
        first = self.portal.worksheets.snapshot()

        v1003.upgrade(self.portal_setup)

        self.assertEqual(first, self.portal.worksheets.snapshot())


class TestGlobalWorksheetPermissionsUpgrade(unittest.TestCase):

    def setUp(self):
        self.portal = WorksheetDummyPortal()
        self.portal_setup = DummyPortalSetup(self.portal)

    def test_restores_global_and_local_labclerk_permissions(self):
        v1004.upgrade(self.portal_setup)

        self.assertEqual([v1004.PROFILE_ID], self.portal_setup.profile_ids)
        for context in (self.portal, self.portal.worksheets):
            for permission in v1004.WORKSHEET_PERMISSIONS:
                self.assertIn(permission, context.managed_permissions)
                self.assertIn(
                    "LabClerk",
                    context.managed_permissions[permission][0])

    def test_is_idempotent(self):
        v1004.upgrade(self.portal_setup)
        first = self.portal.snapshot()

        v1004.upgrade(self.portal_setup)

        self.assertEqual(first, self.portal.snapshot())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(
        TestOOSUpgrade))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(
        TestRolePermissionsUpgrade))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(
        TestWorksheetPermissionsUpgrade))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(
        TestGlobalWorksheetPermissionsUpgrade))
    return suite
