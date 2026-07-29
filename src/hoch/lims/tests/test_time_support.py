# -*- coding: utf-8 -*-

import unittest2 as unittest

from bika.lims.browser.fields.interimfieldsfield import InterimFieldsField
from bika.lims.content.abstractbaseanalysis import ResultType
from hoch.lims.calc import BaseCalculator
from hoch.lims.patches.time_support import format_analysis_result
from hoch.lims.patches.time_support import format_listing_interim
from hoch.lims.patches.time_support import TimeResultTypesVocabulary
from hoch.lims.utils import get_formatted_interim


class DummyAnalysis(object):

    def __init__(self, result_type, result):
        self.result_type = result_type
        self.result = result
        self.original_calls = 0

    def getResultType(self):
        return self.result_type

    def getResult(self):
        return self.result

    def _old_getFormattedResult(self, *args, **kwargs):
        self.original_calls += 1
        return "original-analysis"


class DummyAnalysesView(object):

    def __init__(self):
        self.original_calls = 0

    def _old_get_formatted_interim(self, interim):
        self.original_calls += 1
        return "original-interim"


class TestTimeSupport(unittest.TestCase):

    def test_time_is_available_for_analysis_results(self):
        self.assertIn("time", list(ResultType.vocabulary))

    def test_time_is_available_for_legacy_interims(self):
        field = InterimFieldsField("Interims")
        vocabulary = field.subfield_vocabularies["result_type"]
        self.assertIn("time", list(vocabulary))

    def test_time_is_available_for_modern_interims(self):
        vocabulary = TimeResultTypesVocabulary()(None)
        self.assertIn("time", [term.value for term in vocabulary])

    def test_minutes_and_seconds_are_converted_to_seconds(self):
        self.assertEqual(
            62.0, BaseCalculator.parse_time_to_seconds("01:02"))

    def test_hours_minutes_and_seconds_are_converted_to_seconds(self):
        self.assertEqual(
            3723.0, BaseCalculator.parse_time_to_seconds("01:02:03"))

    def test_numeric_seconds_are_normalized_to_float(self):
        self.assertEqual(
            15.0, BaseCalculator.parse_time_to_seconds(15))

    def test_empty_time_has_no_value(self):
        self.assertIsNone(BaseCalculator.parse_time_to_seconds(""))
        self.assertIsNone(BaseCalculator.parse_time_to_seconds(None))

    def test_invalid_time_is_rejected(self):
        with self.assertRaises(ValueError):
            BaseCalculator.parse_time_to_seconds("invalid")

    def test_time_interim_is_formatted_for_display(self):
        interim = {
            "result_type": "time",
            "value": "01:02:03",
        }
        self.assertEqual("01:02", get_formatted_interim(interim))

    def test_time_analysis_result_uses_hoch_formatter(self):
        analysis = DummyAnalysis("time", "01:02:03")
        self.assertEqual("01:02", format_analysis_result(analysis))
        self.assertEqual(0, analysis.original_calls)

    def test_non_time_analysis_result_delegates_to_core(self):
        analysis = DummyAnalysis("numeric", "12.3")
        self.assertEqual(
            "original-analysis", format_analysis_result(analysis))
        self.assertEqual(1, analysis.original_calls)

    def test_time_listing_interim_uses_hoch_formatter(self):
        view = DummyAnalysesView()
        interim = {"result_type": "time", "value": "01:02:03"}
        self.assertEqual("01:02", format_listing_interim(view, interim))
        self.assertEqual(0, view.original_calls)

    def test_non_time_listing_interim_delegates_to_core(self):
        view = DummyAnalysesView()
        interim = {"result_type": "numeric", "value": "12.3"}
        self.assertEqual(
            "original-interim", format_listing_interim(view, interim))
        self.assertEqual(1, view.original_calls)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(TestTimeSupport)
