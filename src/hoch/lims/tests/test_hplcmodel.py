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

    def test_standard_preparations_use_their_own_weights(self):
        model, variables, rows = ex.flamadin("assay", "PARACETAMOL")
        values = ex.values_of(variables)
        values["W_st_2"] = 252.25
        output = hm.calculate(model, values, rows)
        preps = output["preparations"]
        self.assertEqual([p["W_st"] for p in preps], [250.25, 252.25])
        self.assertEqual([len(p["areas"]) for p in preps], [3, 3])
        self.assertAlmostEqual(output["C_st"],
                               (preps[0]["C_st"] + preps[1]["C_st"]) / 2, 9)
        self.assertNotIn("W_st", output["variables"])
        self.assertEqual(output["variables"]["W_st_2"], 252.25)

    def test_product_overrides_injections_and_Q(self):
        model, variables, rows = ex.flamadin("dissolution", "PARACETAMOL",
                                             aggregate="dissolution")
        values = ex.values_of(variables)
        output = hm.calculate(model, values, rows)
        self.assertEqual(output["Q"], 70.0)
        self.assertEqual(output["injections_per_unit"], 2)
        self.assertEqual(len(output["units"]), 6)
        values["n_iny_mue"] = 3
        values["Q"] = 99
        output = hm.calculate(model, values, rows)
        self.assertEqual(len(output["units"]), 4)
        self.assertFalse(output["S1"])

    def test_preparations_need_complete_groups(self):
        model, variables, rows = ex.flamadin("assay", "PARACETAMOL")
        values = ex.values_of(variables)
        values["n_iny_st"] = 4
        with self.assertRaises(hm.ModelError):
            hm.calculate(model, values, rows)

    def test_units_need_complete_groups(self):
        case = ex.get_cases()[0]
        rows = case["injections"][:-1]
        with self.assertRaises(hm.ModelError):
            hm.calculate(case["model"], ex.values_of(case["variables"]), rows)

    def instrument_case(self, ratio, **values):
        """Flamadin assay with the Std. Conc. of the file at a ratio of the
        expected one
        """
        model, variables, rows = ex.flamadin("assay", "PARACETAMOL")
        values = dict(ex.values_of(variables), **values)
        expected = hm.calculate(model, values, rows)
        for row in rows:
            if row["type"] == "ST":
                row["std_conc"] = expected["C_st"] / 1000. * ratio
        model["standard_from_instrument"] = True
        return model, values, rows, expected

    def test_standard_from_instrument_within_tolerance(self):
        model, values, rows, expected = self.instrument_case(1.0005)
        output = hm.calculate(model, values, rows)
        check = output["standard_check"]
        self.assertTrue(check["passed"])
        self.assertAlmostEqual(check["difference"], 0.05, 6)
        self.assertEqual(check["tolerance"], 0.1)
        self.assertAlmostEqual(check["expected"], expected["C_st"], 9)
        self.assertAlmostEqual(output["C_st"], expected["C_st"] * 1.0005, 9)
        # the result follows the concentration of the instrument
        self.assertAlmostEqual(output["result"], expected["result"] * 1.0005,
                               6)

    def test_standard_from_instrument_blocks_out_of_tolerance(self):
        # Rosuvastatina 52614L: LabSolutions rounded Std. Conc. to 0.016
        # for an expected 0.0159154 mg/mL (+0.53 %)
        model, values, rows, expected = self.instrument_case(0.016 / 0.0159154)
        with self.assertRaises(hm.StandardMismatch) as error:
            hm.calculate(model, values, rows)
        check = error.exception.check
        self.assertFalse(check["passed"])
        self.assertAlmostEqual(check["difference"], 0.5316, 3)

    def test_standard_tolerance_and_factor_are_configurable(self):
        ratio = 0.016 / 0.0159154
        model, values, rows, expected = self.instrument_case(ratio)
        model["standard_tolerance"] = 1
        self.assertTrue(hm.calculate(model, values, rows)
                        ["standard_check"]["passed"])
        # the product parameter wins over the calculation
        model, values, rows, expected = self.instrument_case(
            ratio, tol_std_equipo=0.5)
        with self.assertRaises(hm.StandardMismatch):
            hm.calculate(model, values, rows)
        model, values, rows, expected = self.instrument_case(1, usa_std_equipo=0)
        self.assertIsNone(hm.calculate(model, values, rows)["standard_check"])
        model, values, rows, expected = self.instrument_case(1000,
                                                             f_std_equipo=1)
        self.assertTrue(hm.calculate(model, values, rows)
                        ["standard_check"]["passed"])

    def test_standard_from_instrument_needs_the_std_conc(self):
        model, values, rows, expected = self.instrument_case(1)
        for row in rows:
            row.pop("std_conc", None)
        with self.assertRaises(hm.ModelError):
            hm.calculate(model, values, rows)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestExpressions))
    suite.addTest(unittest.makeSuite(TestExamples))
    return suite
