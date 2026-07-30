# -*- coding: utf-8 -*-

"""Unit tests for dynamically generated vocabularies.

These exercises are intentionally lightweight and do not require a full
Plone site.  They exist primarily to guard against regressions such as the
one reported in issue #... where ``getProcessesVocabulary`` threw an
AttributeError during ``ar_add`` because the add form passes the *batch*
object as the context.
"""

from Products.Archetypes.public import DisplayList
import unittest2 as unittest

from hoch.lims.patches import analysisrequest


class DummyBatch(object):
    """Minimal batch-like object used by the vocabulary code."""

    def __init__(self, processes):
        self._processes = processes

    def getProduct(self):
        return self

    def getProcessGroup(self):
        return self

    def getProcesses(self):
        return self._processes


class DummyAnalysisRequest(object):
    """AnalysisRequest-like container that delegates to a batch."""

    def __init__(self, batch):
        self._batch = batch

    def getBatch(self):
        return self._batch


class TestProcessesVocabulary(unittest.TestCase):

    def test_processes_vocabulary_on_request(self):
        """An AR instance returns the processes from its batch."""
        batch = DummyBatch(["a", "b"])
        ar = DummyAnalysisRequest(batch)
        vocab = analysisrequest.getProcessesVocabulary(ar)
        assert isinstance(vocab, DisplayList)
        assert list(vocab.items()) == [("a", "a"), ("b", "b")]

    def test_processes_vocabulary_on_batch(self):
        """The vocabulary accepts a Batch directly, as used by ar_add."""
        batch = DummyBatch(["x", "y"])
        vocab = analysisrequest.getProcessesVocabulary(batch)
        assert isinstance(vocab, DisplayList)
        assert list(vocab.items()) == [("x", "x"), ("y", "y")]

    def test_processes_vocabulary_on_container_without_product(self):
        """A container without product accessors returns an empty list."""
        class MinimalBatch(object):
            pass

        batch = MinimalBatch()
        vocab = analysisrequest.getProcessesVocabulary(batch)
        assert isinstance(vocab, DisplayList)
        assert list(vocab.items()) == []

    def test_processes_vocabulary_with_wrapper(self):
        """An acquisition wrapper resolves the underlying batch."""
        wrapped = type("W", (), {})()
        wrapped.aq_inner = DummyBatch(["p1", "p2"])
        vocab = analysisrequest.getProcessesVocabulary(wrapped)
        assert isinstance(vocab, DisplayList)
        assert list(vocab.items()) == [("p1", "p1"), ("p2", "p2")]

    def test_processes_vocabulary_with_physical_path_resolution(self):
        """A request parent resolves the real Batch by physical path."""
        class FakePortal(object):

            def __init__(self, real_batch):
                self._batch = real_batch

            def restrictedTraverse(self, path, default=None):
                return self._batch

        batch = DummyBatch(["z"])
        wrapper = type("W", (), {})()

        def get_physical_path():
            return (u"", u"clients", u"client-1", u"B-001")

        wrapper.getPhysicalPath = get_physical_path
        fake_portal = FakePortal(batch)
        wrapper.REQUEST = {"PARENTS": [fake_portal]}

        vocab = analysisrequest.getProcessesVocabulary(wrapper)
        assert isinstance(vocab, DisplayList)
        assert list(vocab.items()) == [("z", "z")]


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestProcessesVocabulary)
