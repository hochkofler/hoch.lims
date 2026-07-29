# -*- coding: utf-8 -*-

import unittest2 as unittest

from DateTime import DateTime
from hoch.lims.adapters import oos_detection as detection
from hoch.lims.adapters.oos import OOSInvestigationGuardAdapter
from hoch.lims.tests.base import SimpleTestCase
from hoch.lims.workflow.oos import events
from hoch.lims.workflow.oos import guards


class DummyUser(object):

    def __init__(self, user_id):
        self.user_id = user_id

    def getId(self):
        return self.user_id


class DummyTransition(object):

    def __init__(self, transition_id):
        self.transition_id = transition_id

    def getId(self):
        return self.transition_id


class DummyEvent(object):

    def __init__(self, transition):
        self.transition = transition


class DummyInvestigation(object):

    def __init__(self, phase1_summary="", conclusion="",
                 disposition="", oos_category="", investigator=""):
        self.uid = "oos-1"
        self.phase1_summary = phase1_summary
        self.conclusion = conclusion
        self.disposition = disposition
        self.oos_category = oos_category
        self.investigator = investigator
        self.reindex_calls = 0

    def getPhase1Summary(self):
        return self.phase1_summary

    def getConclusion(self):
        return self.conclusion

    def getDisposition(self):
        return self.disposition

    def getOosCategory(self):
        return self.oos_category

    def getInvestigator(self):
        return self.investigator

    def reindexObject(self):
        self.reindex_calls += 1


class TestOOSWorkflow(unittest.TestCase):

    def setUp(self):
        self.investigation = DummyInvestigation()
        self.original_guard_get_current_user = guards.api.get_current_user
        self.original_guard_get_id = guards.api.get_id
        self.original_event_get_current_user = events.api.get_current_user
        self.original_event_get_id = events.api.get_id
        guards.api.get_current_user = lambda: DummyUser("reviewer-1")
        guards.api.get_id = lambda obj: obj.uid
        events.api.get_current_user = lambda: DummyUser("reviewer-1")
        events.api.get_id = lambda obj: obj.uid

    def tearDown(self):
        guards.api.get_current_user = self.original_guard_get_current_user
        guards.api.get_id = self.original_guard_get_id
        events.api.get_current_user = self.original_event_get_current_user
        events.api.get_id = self.original_event_get_id

    def test_escalation_requires_phase1_summary(self):
        self.assertFalse(
            guards.guard_escalate_phase2(self.investigation))
        self.investigation.phase1_summary = "Laboratory checks complete"
        self.assertTrue(
            guards.guard_escalate_phase2(self.investigation))

    def test_review_requires_conclusion(self):
        self.investigation.disposition = "reject_batch"
        self.investigation.oos_category = "confirmed"
        self.assertFalse(
            guards.guard_submit_for_review(self.investigation))

    def test_review_requires_disposition(self):
        self.investigation.conclusion = "Confirmed OOS"
        self.investigation.oos_category = "confirmed"
        self.assertFalse(
            guards.guard_submit_for_review(self.investigation))

    def test_review_requires_oos_category(self):
        self.investigation.conclusion = "Confirmed OOS"
        self.investigation.disposition = "reject_batch"
        self.assertFalse(
            guards.guard_submit_for_review(self.investigation))

    def test_review_accepts_complete_investigation(self):
        self.investigation.conclusion = "Confirmed OOS"
        self.investigation.disposition = "reject_batch"
        self.investigation.oos_category = "confirmed"
        self.assertTrue(
            guards.guard_submit_for_review(self.investigation))

    def test_approval_rejects_investigator_as_reviewer(self):
        self.investigation.investigator = "reviewer-1"
        self.assertFalse(guards.guard_approve(self.investigation))

    def test_approval_accepts_different_reviewer(self):
        self.investigation.investigator = "investigator-1"
        self.assertTrue(guards.guard_approve(self.investigation))

    def test_approval_accepts_unassigned_investigator(self):
        self.assertTrue(guards.guard_approve(self.investigation))

    def test_adapter_delegates_known_guard_and_permits_unknown_transition(self):
        adapter = OOSInvestigationGuardAdapter(self.investigation)
        self.assertFalse(adapter.guard("escalate_phase2"))
        self.assertTrue(adapter.guard("cancel"))

    def test_start_phase1_records_date_phase_and_reindexes(self):
        events.after_start_phase1(self.investigation)
        self.assertIsInstance(
            self.investigation.investigation_start_date, DateTime)
        self.assertEqual(
            u"phase_1", self.investigation.investigation_phase)
        self.assertEqual(1, self.investigation.reindex_calls)

    def test_escalate_phase2_records_date_phase_and_reindexes(self):
        events.after_escalate_phase2(self.investigation)
        self.assertIsInstance(
            self.investigation.phase2_start_date, DateTime)
        self.assertEqual(
            u"phase_2", self.investigation.investigation_phase)
        self.assertEqual(1, self.investigation.reindex_calls)

    def test_approve_records_date_reviewer_and_reindexes(self):
        events.after_approve(self.investigation)
        self.assertIsInstance(
            self.investigation.completion_date, DateTime)
        self.assertEqual("reviewer-1", self.investigation.reviewer)
        self.assertEqual(1, self.investigation.reindex_calls)

    def test_oos_dispatcher_ignores_missing_and_unrelated_transitions(self):
        detection.on_oos_transition(
            self.investigation, DummyEvent(None))
        detection.on_oos_transition(
            self.investigation, DummyEvent(DummyTransition("cancel")))
        self.assertEqual(0, self.investigation.reindex_calls)

    def test_oos_dispatcher_routes_supported_transitions(self):
        for transition_id in (
                "start_phase1", "escalate_phase2", "approve"):
            investigation = DummyInvestigation()
            detection.on_oos_transition(
                investigation,
                DummyEvent(DummyTransition(transition_id)))
            self.assertEqual(1, investigation.reindex_calls)


class TestInstalledOOSWorkflow(SimpleTestCase):

    def test_business_transitions_use_guard_handler(self):
        workflow = self.portal.portal_workflow.getWorkflowById(
            "oos_investigation_workflow")

        for transition_id in (
                "escalate_phase2", "submit_for_review", "approve"):
            guard = workflow.transitions[transition_id].guard
            self.assertEqual(
                'python:here.guard_handler("{}")'.format(
                    transition_id),
                guard.expr.text if guard.expr else None)
            self.assertIn(
                "hoch.lims: Transition OOSInvestigation",
                guard.permissions)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(
        TestOOSWorkflow))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(
        TestInstalledOOSWorkflow))
    return suite
