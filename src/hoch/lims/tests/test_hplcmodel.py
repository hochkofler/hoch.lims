# -*- coding: utf-8 -*-

import unittest2 as unittest

from hoch.lims import hplcmodel as hm
from hoch.lims.tests import hplc_examples as ex


class TestExpressions(unittest.TestCase):

    def test_arithmetic_and_functions(self):
        self.assertEqual(hm.evaluate("2 * (a + 1) ** 2", {"a": 2}), 18.0)
        self.assertEqual(hm.evaluate("mean(a, b)", {"a": 1, "b": 3}), 2.0)
        self.assertEqual(hm.evaluate("-a / 4", {"a": 2}), -0.5)

    def test_dotted_names_are_variables(self):
        self.assertEqual(
            hm.evaluate("1 - valoracion.agua_st/100",
                        {"valoracion.agua_st": 4.0}), 0.96)

    def test_code_is_not_allowed(self):
        for expression in ("__import__('os')", "a.__class__()", "a if b else c",
                           "[a]", "lambda: 1", "open('x')", "a < b"):
            with self.assertRaises(hm.ModelError):
                hm.parse(expression)

    def test_optional_uses_default_only_when_missing(self):
        self.assertEqual(hm.evaluate("a * opcional(b, 1)", {"a": 2}), 2.0)
        self.assertEqual(hm.evaluate("a * opcional(b, 1)",
                                     {"a": 2, "b": 3}), 6.0)

    def test_condition_only_needs_the_chosen_branch(self):
        self.assertEqual(hm.evaluate("si(f, x, 0)", {"f": 0}), 0.0)
        self.assertEqual(hm.evaluate("si(f, x, 0)", {"f": 1, "x": 5}), 5.0)
        with self.assertRaises(hm.MissingVariables) as error:
            hm.evaluate("si(f, x, 0)", {"f": 1})
        self.assertEqual(error.exception.names, ["x"])
        with self.assertRaises(hm.MissingVariables) as error:
            hm.evaluate("si(f, x, 0)", {})
        self.assertEqual(error.exception.names, ["f"])

    def test_lazy_functions_are_validated(self):
        for expression in ("opcional(1, 2)", "opcional(a)", "si(a, b)"):
            with self.assertRaises(hm.ModelError):
                hm.parse(expression)

    def test_missing_variables_are_reported(self):
        with self.assertRaises(hm.MissingVariables) as error:
            hm.evaluate("a * b + c", {"a": 1}, stage="standard")
        self.assertEqual(error.exception.names, ["b", "c"])
        self.assertEqual(error.exception.stage, "standard")

    def test_derived_variables_in_any_order(self):
        values, trace = hm.resolve_derived(
            {"c": "b * 2", "b": "a + 1"}, {"a": 1})
        self.assertEqual(trace, {"b": 2.0, "c": 4.0})

    def test_circular_derived_variables(self):
        with self.assertRaises(hm.ModelError):
            hm.resolve_derived({"a": "b", "b": "a"}, {})


class TestExamples(unittest.TestCase):

    def run_case(self, case):
        return hm.calculate(case["model"], ex.values_of(case["variables"]),
                            case["injections"])

    def test_all_cases(self):
        for case in ex.get_cases():
            if case["error"]:
                with self.assertRaises(hm.MissingVariables) as error:
                    self.run_case(case)
                self.assertIn(case["error"], error.exception.names,
                              case["key"])
                continue
            output = self.run_case(case)
            self.assertAlmostEqual(output["result"], case["expected"], 3,
                                   "{}: {} != {}".format(
                                       case["key"], output["result"],
                                       case["expected"]))

    def test_assay_matches_the_spreadsheet_cell_by_cell(self):
        case = ex.get_cases()[0]
        output = self.run_case(case)
        self.assertAlmostEqual(output["C_st"], 15.91538346016, 9)   # I48
        self.assertAlmostEqual(output["A_st"], 793927.5, 6)         # J48
        first = output["units"][0]
        self.assertAlmostEqual(first["C_i"][0], 16.54537146071511, 9)  # M42
        self.assertAlmostEqual(first["resultado"], 99.54204593854386, 9)
        self.assertAlmostEqual(output["result"], 98.42716649073077, 9)  # L64
        self.assertAlmostEqual(output["s"], 0.9255376850733474, 9)      # L65
        self.assertAlmostEqual(output["cv"], 0.9403274706282524, 9)     # L66

    def test_dissolution_vessels_and_stage(self):
        case = [c for c in ex.get_cases() if c["key"] == "disolucion"][0]
        output = self.run_case(case)
        vessels = [u["resultado"] for u in output["units"]]
        expected = [101.98301842769288, 96.50907277853726, 102.73221969604928,
                    105.36885457198149, 101.63415629169546, 101.43415550255325]
        for value, cell in zip(vessels, expected):                   # O135...
            self.assertAlmostEqual(value, cell, 9)
        self.assertTrue(output["S1"])

    def test_units_need_complete_groups(self):
        case = ex.get_cases()[0]
        rows = case["injections"][:-1]
        with self.assertRaises(hm.ModelError):
            hm.calculate(case["model"], ex.values_of(case["variables"]), rows)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestExpressions))
    suite.addTest(unittest.makeSuite(TestExamples))
    return suite
