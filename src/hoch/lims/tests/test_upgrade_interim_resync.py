# -*- coding: utf-8 -*-

import unittest2 as unittest

from hoch.lims.upgrades import v1005


class DummyService(object):

    def __init__(self, interims):
        self.interims = interims

    def getInterimFields(self):
        return self.interims


class DummyAnalysis(object):

    def __init__(self, interims, state="assigned", service=None):
        self.interims = interims
        self.state = state
        self.service = service
        self.saved = None

    def getRawAnalysisService(self):
        return "service-uid"

    def getInterimFields(self):
        return self.interims

    def setInterimFields(self, interims):
        self.interims = interims
        self.saved = interims


class DummyCatalog(object):

    def __init__(self, brains):
        self.brains = brains

    def unrestrictedSearchResults(self, **kwargs):
        self.query = kwargs
        return self.brains


class FakeApi(object):
    """Minimal stand-in for bika.lims.api used by the upgrade module."""

    def __init__(self, catalog, analyses, service):
        self.catalog = catalog
        self.analyses = analyses
        self.service = service

    def get_tool(self, name):
        return self.catalog

    def get_object(self, brain):
        return brain

    def get_object_by_uid(self, uid, default=None):
        return self.service

    def get_review_status(self, obj):
        return obj.state

    def get_path(self, obj):
        return "/dummy"


class TestInterimResync(unittest.TestCase):

    def setUp(self):
        self.original_api = v1005.api

    def tearDown(self):
        v1005.api = self.original_api

    def resync(self, analyses, service_interims):
        service = DummyService(service_interims)
        catalog = DummyCatalog(analyses)
        v1005.api = FakeApi(catalog, analyses, service)
        return v1005.resync_analysis_interims(object())

    def test_captured_interim_value_is_never_overwritten(self):
        """The service default must not clobber data an analyst captured.

        Chromatography interims carry an empty default on the service; the
        analysis holds the measured value.  Copying the default down would
        destroy laboratory data.
        """
        analysis = DummyAnalysis([{
            "keyword": "area",
            "value": "1053816",
            "hidden": True,
        }])

        total = self.resync([analysis], [{
            "keyword": "area",
            "value": "",
            "hidden": False,
            "report": False,
            "wide": False,
        }])

        self.assertEqual(1, total)
        self.assertEqual("1053816", analysis.interims[0]["value"])
        self.assertFalse(analysis.interims[0]["hidden"])

    def test_value_is_not_in_the_resynced_keys(self):
        self.assertNotIn("value", v1005.RESYNC_KEYS)

    def test_analysis_past_result_entry_is_skipped(self):
        """A stale review_state index must not let a submitted analysis
        through: the state is re-checked on the object itself.
        """
        analysis = DummyAnalysis(
            [{"keyword": "area", "value": "123", "hidden": True}],
            state="to_be_verified")

        total = self.resync([analysis], [{
            "keyword": "area", "value": "", "hidden": False,
            "report": False, "wide": False,
        }])

        self.assertEqual(0, total)
        self.assertIsNone(analysis.saved)
        self.assertTrue(analysis.interims[0]["hidden"])

    def test_display_flags_are_applied(self):
        analysis = DummyAnalysis([{
            "keyword": "potencia_declarada_m",
            "value": "500",
            "hidden": True,
            "report": False,
            "wide": False,
        }])

        total = self.resync([analysis], [{
            "keyword": "potencia_declarada_m",
            "value": "500",
            "report": "on",
        }])

        self.assertEqual(1, total)
        interim = analysis.interims[0]
        self.assertEqual("500", interim["value"])
        self.assertFalse(interim["hidden"])
        self.assertTrue(interim["report"])


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestInterimResync)
