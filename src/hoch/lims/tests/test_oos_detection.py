# -*- coding: utf-8 -*-

import unittest2 as unittest

from hoch.lims.adapters import oos_detection as detection


class DummyTransition(object):

    def __init__(self, transition_id):
        self.transition_id = transition_id

    def getId(self):
        return self.transition_id


class DummyEvent(object):

    def __init__(self, transition):
        self.transition = transition


class DummyAnalysis(object):

    def __init__(self):
        self.uid = "analysis-1"

    def getId(self):
        return self.uid

    def getResult(self):
        return "12.5"

    def getResultsRange(self):
        return {"min": "10", "max": "11"}

    def Title(self):
        return "Assay"


class DummyOOS(object):

    def __init__(self, uid):
        self.uid = uid
        self.reindex_calls = 0

    def reindexObject(self):
        self.reindex_calls += 1


class DummyUser(object):

    def getId(self):
        return "analyst-1"


class TestOOSDetection(unittest.TestCase):

    def setUp(self):
        self.created = []
        self.catalog_results = []
        self.analysis = DummyAnalysis()
        self.oos_folder = object()
        self.portal = {"OOSInvestigations": self.oos_folder}

        self.original_is_out_of_range = detection.is_out_of_range
        self.original_get_portal = detection.api.get_portal
        self.original_get_uid = detection.api.get_uid
        self.original_get_tool = detection.api.get_tool
        self.original_get_current_user = detection.api.get_current_user
        self.original_create = detection.api.create
        self.original_get_id = detection.api.get_id

        detection.is_out_of_range = lambda analysis: (True, False)
        detection.api.get_portal = lambda: self.portal
        detection.api.get_uid = lambda analysis: analysis.uid
        detection.api.get_tool = lambda name: self.catalog
        detection.api.get_current_user = lambda: DummyUser()
        detection.api.create = self.create
        detection.api.get_id = lambda obj: obj.uid

    def tearDown(self):
        detection.is_out_of_range = self.original_is_out_of_range
        detection.api.get_portal = self.original_get_portal
        detection.api.get_uid = self.original_get_uid
        detection.api.get_tool = self.original_get_tool
        detection.api.get_current_user = self.original_get_current_user
        detection.api.create = self.original_create
        detection.api.get_id = self.original_get_id

    def catalog(self, **query):
        return self.catalog_results

    def create(self, container, portal_type):
        self.assertIs(self.oos_folder, container)
        self.assertEqual("OOSInvestigation", portal_type)
        oos = DummyOOS("oos-{}".format(len(self.created) + 1))
        self.created.append(oos)
        return oos

    def test_ignores_event_without_transition(self):
        detection.on_analysis_transition(self.analysis, DummyEvent(None))
        self.assertEqual([], self.created)

    def test_ignores_unrelated_transition(self):
        detection.on_analysis_transition(
            self.analysis, DummyEvent(DummyTransition("retract")))
        self.assertEqual([], self.created)

    def test_does_not_create_oos_for_in_spec_result(self):
        detection.is_out_of_range = lambda analysis: (False, False)
        detection.on_analysis_transition(
            self.analysis, DummyEvent(DummyTransition("submit")))
        self.assertEqual([], self.created)

    def test_submit_dispatches_oos_detection(self):
        detection.on_analysis_transition(
            self.analysis, DummyEvent(DummyTransition("submit")))
        self.assertEqual(1, len(self.created))

    def test_verify_dispatches_oos_detection(self):
        detection.on_analysis_transition(
            self.analysis, DummyEvent(DummyTransition("verify")))
        self.assertEqual(1, len(self.created))

    def test_created_oos_contains_detection_snapshot(self):
        oos = detection._check_and_create_oos(self.analysis)

        self.assertEqual("analysis-1", oos.analysis_uid)
        self.assertEqual("12.5", oos.result_value)
        self.assertEqual(u"min=10, max=11", oos.specification_range)
        self.assertEqual("Assay", oos.analysis_service_title)
        self.assertEqual("analyst-1", oos.responsible_analyst)
        self.assertEqual(30, int(oos.due_date - oos.detection_date))
        self.assertEqual(1, oos.reindex_calls)

    def test_existing_oos_prevents_duplicate_creation(self):
        self.catalog_results = [object()]

        result = detection._check_and_create_oos(self.analysis)

        self.assertIsNone(result)
        self.assertEqual([], self.created)

    def test_missing_oos_folder_does_not_create_partial_record(self):
        self.portal.pop("OOSInvestigations")

        result = detection._check_and_create_oos(self.analysis)

        self.assertIsNone(result)
        self.assertEqual([], self.created)

    def test_creation_failure_is_propagated(self):
        def fail_create(container, portal_type):
            raise RuntimeError("cannot persist OOS")

        detection.api.create = fail_create

        with self.assertRaises(RuntimeError):
            detection._check_and_create_oos(self.analysis)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestOOSDetection)
