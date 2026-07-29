# -*- coding: utf-8 -*-

import json
import unittest2 as unittest

from hoch.lims.patches import analysis as analysis_patch


class DummyField(object):

    def __init__(self):
        self.value = None

    def set(self, context, value):
        self.value = value


class DummyCalculation(object):

    def __init__(self, interims=None):
        self.interims = interims or []

    def UID(self):
        return "calculation-uid"

    def getMinifiedFormula(self):
        return "[Temperature] * 2"

    def getPythonImports(self):
        return [{"module": "math", "function": "sqrt"}]

    def getInterimFields(self):
        return self.interims


class DummyAnalysis(object):

    def __init__(self, interims=None):
        self.interims = interims or []
        self.fields = {
            name: DummyField()
            for name in (
                "CalculationUID", "CalculationFormula",
                "CalculationImports", "CalculationVersion")
        }

    def getField(self, name):
        return self.fields[name]

    def getInterimFields(self):
        return self.interims

    def setInterimFields(self, interims):
        self.interims = interims


class TestCalculationInterims(unittest.TestCase):

    def setUp(self):
        self.original_get_object = analysis_patch.api.get_object
        self.original_get_version = analysis_patch.api.get_version
        analysis_patch.api.get_object = lambda calculation: calculation
        analysis_patch.api.get_version = lambda calculation: 7

    def tearDown(self):
        analysis_patch.api.get_object = self.original_get_object
        analysis_patch.api.get_version = self.original_get_version

    def test_calculation_metadata_is_snapshotted(self):
        analysis = DummyAnalysis()
        calculation = DummyCalculation()

        analysis_patch.setCalculation(analysis, calculation)

        self.assertEqual(
            "calculation-uid",
            analysis.fields["CalculationUID"].value)
        self.assertEqual(
            "[Temperature] * 2",
            analysis.fields["CalculationFormula"].value)
        self.assertEqual(
            [{"function": "sqrt", "module": "math"}],
            json.loads(analysis.fields["CalculationImports"].value))
        self.assertEqual(
            7, analysis.fields["CalculationVersion"].value)

    def test_service_overrides_display_and_default_properties(self):
        calculation = DummyCalculation([{
            "keyword": "Temperature",
            "title": "Calculation temperature",
            "value": "10",
            "hidden": False,
            "report": False,
            "unit": "C",
            "wide": False,
            "choices": "10:Ten|20:Twenty",
            "result_type": "select",
            "allow_empty": False,
        }])
        analysis = DummyAnalysis([{
            "keyword": "Temperature",
            "title": "Service temperature",
            "value": "25",
            "hidden": True,
            "report": True,
            "unit": "degC",
            "wide": True,
            "choices": "service-choice",
            "result_type": "string",
            "allow_empty": True,
        }])

        analysis_patch.setCalculation(analysis, calculation)

        interim = analysis.interims[0]
        self.assertEqual("Service temperature", interim["title"])
        self.assertEqual("25", interim["value"])
        self.assertTrue(interim["hidden"])
        self.assertTrue(interim["report"])
        self.assertEqual("degC", interim["unit"])
        self.assertTrue(interim["wide"])

    def test_calculation_owns_control_properties(self):
        calculation = DummyCalculation([{
            "keyword": "Temperature",
            "choices": "10:Ten|20:Twenty",
            "result_type": "select",
            "allow_empty": False,
        }])
        analysis = DummyAnalysis([{
            "keyword": "Temperature",
            "choices": "service-choice",
            "result_type": "string",
            "allow_empty": True,
        }])

        analysis_patch.setCalculation(analysis, calculation)

        interim = analysis.interims[0]
        self.assertEqual("10:Ten|20:Twenty", interim["choices"])
        self.assertEqual("select", interim["result_type"])
        self.assertFalse(interim["allow_empty"])

    def test_calculation_interims_precede_service_only_interims(self):
        calculation = DummyCalculation([
            {"keyword": "Shared"},
            {"keyword": "CalculationOnly"},
        ])
        analysis = DummyAnalysis([
            {"keyword": "ServiceOnly"},
            {"keyword": "Shared", "value": "service-value"},
        ])

        analysis_patch.setCalculation(analysis, calculation)

        self.assertEqual(
            ["Shared", "CalculationOnly", "ServiceOnly"],
            [interim["keyword"] for interim in analysis.interims])
        self.assertEqual(
            1,
            len([item for item in analysis.interims
                 if item["keyword"] == "Shared"]))

    def test_linking_copies_calculation_and_service_interims(self):
        calculation_interim = {
            "keyword": "Shared",
            "choices": "1:One",
        }
        service_interim = {
            "keyword": "Shared",
            "value": "service-value",
        }
        calculation = DummyCalculation([calculation_interim])
        analysis = DummyAnalysis([service_interim])

        analysis_patch.setCalculation(analysis, calculation)
        calculation_interim["choices"] = "changed"
        service_interim["value"] = "changed"

        self.assertEqual("1:One", analysis.interims[0]["choices"])
        self.assertEqual("service-value", analysis.interims[0]["value"])

    def test_unlink_clears_snapshot_and_preserves_interims(self):
        original_interims = [{"keyword": "ServiceOnly", "value": "12"}]
        analysis = DummyAnalysis(original_interims)

        analysis_patch.setCalculation(analysis, None)

        self.assertEqual("", analysis.fields["CalculationUID"].value)
        self.assertEqual("", analysis.fields["CalculationFormula"].value)
        self.assertEqual("[]", analysis.fields["CalculationImports"].value)
        self.assertEqual(0, analysis.fields["CalculationVersion"].value)
        self.assertIs(original_interims, analysis.interims)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestCalculationInterims)
