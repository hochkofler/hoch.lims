# -*- coding: utf-8 -*-

import unittest2 as unittest

from bika.lims.content.abstractbaseanalysis import RESULT_TYPES
from hoch.lims.calc import BaseCalculator
from hoch.lims.utils import get_formatted_interim


class TestTimeSupport(unittest.TestCase):

    def test_time_result_type_is_registered(self):
        result_type_ids = [item[0] for item in RESULT_TYPES]
        self.assertIn("time", result_type_ids)

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
