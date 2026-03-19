# -*- coding: utf-8 -*-

"""Unit tests for dynamically generated vocabularies.

These exercises are intentionally lightweight and do not require a full
Plone site.  They exist primarily to guard against regressions such as the
one reported in issue #... where ``getProcessesVocabulary`` threw an
AttributeError during ``ar_add`` because the add form passes the *batch*
object as the context.
"""

from Products.Archetypes.public import DisplayList

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


# Tests

def test_processes_vocabulary_on_request():
    """Calling the vocabulary method on an AR instance should return the list."""

    batch = DummyBatch(["a", "b"])
    ar = DummyAnalysisRequest(batch)
    vocab = analysisrequest.getProcessesVocabulary(ar)
    assert isinstance(vocab, DisplayList)
    assert list(vocab) == [("a", "a"), ("b", "b")]


def test_processes_vocabulary_on_batch():
    """The same method should also handle being passed a Batch directly.

    This is what happens during ``ar_add`` where the form template invokes
    ``field.Vocabulary(context)`` and ``context`` is the batch container.
    """

    batch = DummyBatch(["x", "y"])
    vocab = analysisrequest.getProcessesVocabulary(batch)
    assert isinstance(vocab, DisplayList)
    assert list(vocab) == [("x", "x"), ("y", "y")]


def test_processes_vocabulary_on_container_without_product():
    """If context is the batch but it can't produce a product, we return an
    empty DisplayList instead of raising an AttributeError.  This reflects
    the situation seen on ``/ar_add`` where the container is an empty
    ``RequestContainer`` (Batch) that lacks our helper methods.
    """

    class MinimalBatch(object):
        pass

    batch = MinimalBatch()
    vocab = analysisrequest.getProcessesVocabulary(batch)
    assert isinstance(vocab, DisplayList)
    assert list(vocab) == []


def test_processes_vocabulary_with_wrapper():
    """When the vocabulary is invoked on a request container wrapper we
    should still retrieve data from the underlying batch via acquisition.
    """

    wrapped = type('W', (), {})()
    wrapped.aq_inner = DummyBatch(['p1', 'p2'])
    vocab = analysisrequest.getProcessesVocabulary(wrapped)
    assert isinstance(vocab, DisplayList)
    assert list(vocab) == [('p1', 'p1'), ('p2', 'p2')]


def test_processes_vocabulary_with_physical_path_resolution():
    """Simulate the situation where the context has no accessors at all but
    can be traversed from the portal.  ``REQUEST.PARENTS[0]`` should be the
    portal, which can look up the real Batch by path.
    """

    class FakePortal(object):
        def __init__(self, real_batch):
            self._batch = real_batch
        def restrictedTraverse(self, path, default=None):
            # ignore path parsing, just return the batch
            return self._batch

    batch = DummyBatch(["z"])
    wrapper = type('W', (), {})()
    # wrapper has no getProduct or acquisition helpers
    def getPhysicalPath():
        return (u'', u'clients', u'client-1', u'B-001')
    wrapper.getPhysicalPath = getPhysicalPath

    fake_portal = FakePortal(batch)
    wrapper.REQUEST = {'PARENTS': [fake_portal]}

    vocab = analysisrequest.getProcessesVocabulary(wrapper)
    assert isinstance(vocab, DisplayList)
    assert list(vocab) == [("z", "z")]
