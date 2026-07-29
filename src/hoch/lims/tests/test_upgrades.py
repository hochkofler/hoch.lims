# -*- coding: utf-8 -*-

import unittest2 as unittest

from Products.DCWorkflow.Guard import Guard
from hoch.lims.upgrades import v1001


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


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestOOSUpgrade)
