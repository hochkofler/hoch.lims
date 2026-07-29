# -*- coding: utf-8 -*-

import unittest2 as unittest

from DateTime import DateTime
from hoch.lims.adapters.batch import BatchGuardAdapter
from hoch.lims.patches import batch as batch_patch
from hoch.lims.workflow.batch import events
from hoch.lims.workflow.batch import guards


class DummyField(object):

    def __init__(self, value=None):
        self.value = value

    def get(self, context):
        return self.value

    def set(self, context, value):
        self.value = value


class DummyAnalysis(object):

    def __init__(self, uid="analysis-1", status="verified",
                 out_of_range=False):
        self.uid = uid
        self.status = status
        self.out_of_range = out_of_range

    def getId(self):
        return self.uid

    def isOutOfRange(self):
        return self.out_of_range


class DummySample(object):

    def __init__(self, uid, destination="release", status="verified",
                 invalid=False, analyses=None):
        self.uid = uid
        self.status = status
        self.invalid = invalid
        self.analyses = analyses or [DummyAnalysis()]
        self.fields = {
            "Destination": DummyField(destination),
        }

    def getId(self):
        return self.uid

    def getField(self, name):
        return self.fields.get(name)

    def getDestination(self):
        return self.fields["Destination"].value

    def getAnalyses(self, full_objects=False):
        return self.analyses

    def isInvalid(self):
        return self.invalid


class DummyPublication(object):

    def __init__(self, samples=None, status="active"):
        self.uid = "publication-1"
        self.status = status
        self.samples = samples or []

    def getAnalysisRequests(self):
        return self.samples

    def getSample(self):
        return self.samples[0] if self.samples else None

    def getContainedSamples(self):
        return self.samples[1:]

    def getMetadata(self):
        return {}


class DummyBatch(object):
    portal_type = "Batch"

    def __init__(self, samples=None, publication=None, status="closed",
                 audit_fields=True):
        self.uid = "batch-1"
        self.status = status
        self.samples = samples or []
        self.reindex_calls = 0
        self.fields = {
            "ReleasePublication": DummyField(publication),
        }
        if audit_fields:
            self.fields["ReleaseDate"] = DummyField()
            self.fields["ReleasedBy"] = DummyField()

    def getId(self):
        return self.uid

    def getField(self, name):
        return self.fields.get(name)

    def getReleasePublication(self):
        return self.fields["ReleasePublication"].value

    def getAnalysisRequests(self):
        return self.samples

    def reindexObject(self):
        self.reindex_calls += 1


class DummyUser(object):

    def getId(self):
        return "release-manager"


class TestBatchWorkflow(unittest.TestCase):

    def setUp(self):
        self.open_oos = []
        self.original_get_review_status = guards.api.get_review_status
        self.original_get_uid = guards.api.get_uid
        self.original_get_tool = guards.api.get_tool
        guards.api.get_review_status = lambda obj: obj.status
        guards.api.get_uid = lambda obj: obj.uid
        guards.api.get_tool = lambda name: self.catalog

    def tearDown(self):
        guards.api.get_review_status = self.original_get_review_status
        guards.api.get_uid = self.original_get_uid
        guards.api.get_tool = self.original_get_tool

    def catalog(self, **query):
        return self.open_oos

    def valid_batch(self):
        sample = DummySample("sample-1")
        publication = DummyPublication([sample])
        return DummyBatch([sample], publication), sample, publication

    def test_release_is_allowed_when_all_invariants_hold(self):
        batch, sample, publication = self.valid_batch()
        self.assertTrue(guards.guard_release(batch))

    def test_release_rejects_batch_that_is_not_closed(self):
        batch, sample, publication = self.valid_batch()
        batch.status = "open"
        self.assertFalse(guards.guard_release(batch))

    def test_release_rejects_missing_publication(self):
        batch, sample, publication = self.valid_batch()
        batch.fields["ReleasePublication"].value = None
        self.assertFalse(guards.guard_release(batch))

    def test_release_rejects_batch_without_release_samples(self):
        batch, sample, publication = self.valid_batch()
        sample.fields["Destination"].value = "stability"
        self.assertFalse(guards.guard_release(batch))

    def test_release_rejects_unverified_release_sample(self):
        batch, sample, publication = self.valid_batch()
        sample.status = "received"
        self.assertFalse(guards.guard_release(batch))

    def test_release_accepts_published_release_sample(self):
        batch, sample, publication = self.valid_batch()
        sample.status = "published"
        self.assertTrue(guards.guard_release(batch))

    def test_release_rejects_publication_missing_release_sample(self):
        batch, sample, publication = self.valid_batch()
        publication.samples = []
        self.assertFalse(guards.guard_release(batch))

    def test_release_rejects_inactive_publication(self):
        batch, sample, publication = self.valid_batch()
        publication.status = "draft"
        self.assertFalse(guards.guard_release(batch))

    def test_release_rejects_out_of_specification_analysis(self):
        batch, sample, publication = self.valid_batch()
        sample.analyses[0].out_of_range = True
        self.assertFalse(guards.guard_release(batch))

    def test_release_rejects_open_oos_investigation(self):
        batch, sample, publication = self.valid_batch()
        self.open_oos = [object()]
        self.assertFalse(guards.guard_release(batch))

    def test_close_and_reopen_guards_follow_batch_state(self):
        batch, sample, publication = self.valid_batch()
        batch.status = "open"
        self.assertTrue(guards.guard_close(batch))
        self.assertFalse(guards.guard_reopen(batch))
        batch.status = "closed"
        self.assertFalse(guards.guard_close(batch))
        self.assertTrue(guards.guard_reopen(batch))

    def test_guard_adapter_delegates_release_and_allows_other_actions(self):
        batch, sample, publication = self.valid_batch()
        adapter = BatchGuardAdapter(batch)
        self.assertTrue(adapter.guard("release"))
        self.assertTrue(adapter.guard("close"))

    def test_legacy_batch_guard_applies_out_of_specification_rule(self):
        batch, sample, publication = self.valid_batch()
        sample.analyses[0].out_of_range = True
        self.assertFalse(batch_patch.guard_release_batch(batch))

    def test_after_release_records_audit_fields_and_reindexes(self):
        batch, sample, publication = self.valid_batch()
        original_get_current_user = events.api.get_current_user
        events.api.get_current_user = lambda: DummyUser()
        self.addCleanup(
            setattr, events.api, "get_current_user",
            original_get_current_user)

        events.after_release(batch)

        self.assertIsInstance(
            batch.fields["ReleaseDate"].value, DateTime)
        self.assertEqual(
            "release-manager", batch.fields["ReleasedBy"].value)
        self.assertEqual(1, batch.reindex_calls)

    def test_after_release_tolerates_missing_audit_fields(self):
        batch, sample, publication = self.valid_batch()
        batch.fields.pop("ReleaseDate")
        batch.fields.pop("ReleasedBy")
        original_get_current_user = events.api.get_current_user
        events.api.get_current_user = lambda: DummyUser()
        self.addCleanup(
            setattr, events.api, "get_current_user",
            original_get_current_user)

        events.after_release(batch)

        self.assertEqual(1, batch.reindex_calls)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestBatchWorkflow)
