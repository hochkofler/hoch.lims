# -*- coding: utf-8 -*-

import unittest2 as unittest

from bika.lims.browser.fields.interimfieldsfield import InterimFieldsField
from bika.lims.content.abstractbaseanalysis import ResultType
from hoch.lims.calc import BaseCalculator
from hoch.lims.patches.time_support import TimeResultTypesVocabulary
from hoch.lims.utils import get_formatted_interim


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


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(TestTimeSupport)
