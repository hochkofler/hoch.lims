# -*- coding: utf-8 -*-

import transaction
import unittest2 as unittest
from bika.lims import api
from bika.lims.utils.analysisrequest import create_analysisrequest
from bika.lims.workflow import doActionFor
from DateTime import DateTime
from hoch.lims import hplcanalysis as ha
from hoch.lims import injections as inj
from hoch.lims.tests import hplc_examples as ex
from hoch.lims.tests.base import SimpleTestCase
from hoch.lims.tests.test_dynamic_calculation_functional import \
    DYNAMIC_CALCULATION_TESTING
from plone.app.testing import TEST_USER_ID
from plone.app.testing import setRoles

UNIVERSAL = ex.UNIVERSAL_MODEL

RUN_INTERIMS = [
    {"keyword": "W_st_1", "title": "Pesada estándar 1", "unit": "mg"},
    {"keyword": "W_st_2", "title": "Pesada estándar 2", "unit": "mg"},
    {"keyword": "W_st_3", "title": "Pesada estándar 3", "unit": "mg"},
    {"keyword": "agua_st", "title": "Agua del estándar", "unit": "%"},
    {"keyword": "P_st", "title": "Potencia del estándar", "unit": "%"},
]


def set_model(calculation, model, aggregate=None):
    calculation.hplc_standard = model["standard"]
    calculation.hplc_amount = model["amount"]
    calculation.hplc_result = model["result"]
    calculation.hplc_injections_per_unit = model["injections_per_unit"]
    calculation.hplc_aggregate = aggregate or model["aggregate"]
    calculation.hplc_T = 100.0
    calculation.hplc_k = 2.4
    calculation.hplc_Q = 75.0
    calculation.hplc_derived = u"\n".join(
        u"{} = {}".format(k, v) for k, v in sorted(model["derived"].items()))
    calculation.setPythonImports([
        {"module": "hoch.lims.calc", "function": "calc_hplc_model"}])
    calculation.setFormula(ha.FORMULA)


class TestHPLCAnalysisFunctional(SimpleTestCase):
    layer = DYNAMIC_CALCULATION_TESTING

    def setUp(self):
        super(TestHPLCAnalysisFunctional, self).setUp()
        setRoles(self.portal, TEST_USER_ID, ["Manager", "LabManager"])
        setup = self.portal.setup
        bikasetup = api.get_bika_setup()
        self.client = api.create(
            self.portal.clients, "Client", Name="IFA", ClientID="IFA")
        self.contact = api.create(
            self.client, "Contact", Firstname="Lab", Lastname="Ifa")
        self.matrix = api.create(setup.samplematrices, "SampleMatrix",
                                 title="NN-55237")
        self.product = api.create(
            setup.sampletypes, "SampleType", title="NN-55237", Prefix="R")
        self.product.setSampleMatrix(self.matrix)
        category = api.create(
            setup.analysiscategories, "AnalysisCategory", title="Valoracion")

        calculations = setup.calculations
        self.assay_calc = api.create(
            calculations, "Calculation", title="HPLC Valoracion")
        self.assay_calc.setInterimFields(RUN_INTERIMS)
        set_model(self.assay_calc, UNIVERSAL)
        self.uc_calc = api.create(
            calculations, "Calculation", title="HPLC Uniformidad")
        set_model(self.uc_calc, UNIVERSAL, aggregate="uniformity")

        services = bikasetup.bika_analysisservices
        cat = api.get_uid(category)
        self.val = api.create(services, "AnalysisService",
                              title="Valoracion Rosuvastatina",
                              Keyword="VAL_ROSUVASTATINA", Category=cat)
        self.val.getField(inj.RECEIVES_FIELD).set(self.val, True)
        self.val.setCalculation(self.assay_calc)
        self.uc = api.create(services, "AnalysisService",
                             title="Uniformidad Rosuvastatina",
                             Keyword="UC_ROSUVASTATINA", Category=cat)
        self.uc.setCalculation(self.uc_calc)

        params = {"V_st": 50, "D_st": 25, "V_mue": 50, "D_mue": 25,
                  "LC": 20, "PM_st": 1001.14, "PM_decl": 481.54, "n_PM": 2,
                  "usa_agua": 1, "usa_PM": 1, "por_porcion": 0}
        self.matrix.hplc_parameters = [
            {"service": api.get_uid(self.val), "name": name,
             "value": float(value), "unit": u""}
            for name, value in params.items()]
        transaction.commit()

    def new_sample(self):
        values = {
            "Client": api.get_uid(self.client),
            "Contact": api.get_uid(self.contact),
            "DateSampled": DateTime().strftime("%Y-%m-%d"),
            "SampleType": api.get_uid(self.product),
        }
        sample = create_analysisrequest(
            self.client, self.request, values,
            [api.get_uid(self.val), api.get_uid(self.uc)])
        doActionFor(sample, "receive")
        return sample

    def get(self, sample, keyword):
        for analysis in sample.getAnalyses(full_objects=True):
            if analysis.getKeyword() == keyword:
                return analysis

    def set_run_data(self, analysis, **values):
        interims = analysis.getInterimFields()
        for interim in interims:
            if interim["keyword"] in values:
                interim["value"] = values[interim["keyword"]]
        analysis.setInterimFields(interims)

    def loaded_sample(self, **run_data):
        sample = self.new_sample()
        val = self.get(sample, "VAL_ROSUVASTATINA")
        rows = ex.injections(ex.ASSAY_STANDARD_AREAS, ex.ASSAY_SAMPLE_AREAS)
        inj.set_injections(val, rows)
        data = {"W_st_1": "20.84", "W_st_2": "20.84", "agua_st": "4.251",
                "P_st": "99.7"}
        data.update(run_data)
        self.set_run_data(val, **data)
        val.calculateResult(override=True)
        return sample

    def test_model_is_copied_into_the_analysis(self):
        sample = self.new_sample()
        val = self.get(sample, "VAL_ROSUVASTATINA")
        model = ha.get_model(val)
        self.assertEqual(model["standard"], UNIVERSAL["standard"])
        # editing the calculation does not change existing analyses
        self.assay_calc.hplc_result = u"cantidad * F_PM"
        self.assertEqual(ha.get_model(val)["result"], UNIVERSAL["result"])

    def test_assay_and_uniformity_from_the_spreadsheet(self):
        sample = self.loaded_sample()
        val = self.get(sample, "VAL_ROSUVASTATINA")
        uc = self.get(sample, "UC_ROSUVASTATINA")
        self.assertAlmostEqual(api.to_float(val.getResult()), 98.427166, 5)
        # content uniformity is recalculated from the assay data
        self.assertNotEqual(uc.getResult(), "", ha.get_trace(uc))
        self.assertAlmostEqual(api.to_float(uc.getResult()), 2.294124, 5)

        trace = ha.get_trace(val)
        self.assertIsNone(trace["error"])
        self.assertAlmostEqual(trace["output"]["C_st"], 15.91538346016, 8)
        self.assertEqual(trace["variables"]["W_st"][1], ha.DERIVED)
        self.assertEqual(trace["variables"]["agua_st"][1], ha.RUN)
        self.assertEqual(trace["variables"]["V_st"][1], ha.PRODUCT)
        self.assertEqual(ha.get_trace(uc)["variables"]["agua_st"][1],
                         ha.ASSAY)

    def test_missing_water_is_reported(self):
        sample = self.loaded_sample(agua_st="")
        val = self.get(sample, "VAL_ROSUVASTATINA")
        self.assertEqual(val.getResult(), "")
        trace = ha.get_trace(val)
        self.assertEqual(trace["missing"], ["agua_st"])

    def test_product_without_water_correction(self):
        rows = list(self.matrix.hplc_parameters)
        for row in rows:
            if row["name"] == "usa_agua":
                row["value"] = 0.0
        self.matrix.hplc_parameters = rows
        sample = self.loaded_sample(agua_st="")
        val = self.get(sample, "VAL_ROSUVASTATINA")
        self.assertAlmostEqual(api.to_float(val.getResult()), 102.797070, 5)

    def test_dissolution_with_product_parameters(self):
        # FLAMADIN PLUS lot 82618, paracetamol: separate dissolution sample,
        # 2 standard preparations x 3 injections, Q from the product
        model = ex.UNIVERSAL_V2
        dis_calc = api.create(self.portal.setup.calculations, "Calculation",
                              title="HPLC Disolucion")
        dis_calc.setInterimFields(RUN_INTERIMS)
        set_model(dis_calc, model, aggregate="dissolution")
        dis_calc.hplc_standard_injections_per_prep = 3
        dis = api.create(api.get_bika_setup().bika_analysisservices,
                         "AnalysisService", title="Disolucion Paracetamol",
                         Keyword="DIS_PARACETAMOL",
                         Category=self.val.getRawCategory())
        dis.getField(inj.RECEIVES_FIELD).set(dis, True)
        dis.setCalculation(dis_calc)
        params = dict(ex.FLAMADIN_DISSOLUTION_PARAMETERS, V_st=50, LC=500,
                      usa_agua=0, usa_PM=0, n_iny_mue=2)
        self.matrix.hplc_parameters = [
            {"service": api.get_uid(dis), "name": name,
             "value": float(value), "unit": u""}
            for name, value in params.items()]
        values = {
            "Client": api.get_uid(self.client),
            "Contact": api.get_uid(self.contact),
            "DateSampled": DateTime().strftime("%Y-%m-%d"),
            "SampleType": api.get_uid(self.product),
        }
        sample = create_analysisrequest(self.client, self.request, values,
                                        [api.get_uid(dis)])
        doActionFor(sample, "receive")
        analysis = self.get(sample, "DIS_PARACETAMOL")
        data = ex.FLAMADIN["dissolution"]["PARACETAMOL"]
        inj.set_injections(analysis, ex.injections(data["standard"],
                                                   data["samples"]))
        self.set_run_data(analysis, W_st_1="55.57", P_st="99.9")
        analysis.calculateResult(override=True)
        # the second preparation has no weight yet
        self.assertEqual(analysis.getResult(), "")
        self.assertEqual(ha.get_trace(analysis)["missing"], ["W_st_2"])

        self.set_run_data(analysis, W_st_2="55.57")
        analysis.calculateResult(override=True)
        self.assertAlmostEqual(api.to_float(analysis.getResult()),
                               97.436344, 5)
        output = ha.get_trace(analysis)["output"]
        self.assertEqual(output["Q"], 70.0)
        self.assertTrue(output["S1"])
        self.assertEqual(len(output["preparations"]), 2)
        html = analysis.restrictedTraverse("@@hplc_detail")()
        self.assertIn("111.02886", html)

    def test_detail_view_renders(self):
        sample = self.loaded_sample()
        val = self.get(sample, "VAL_ROSUVASTATINA")
        html = val.restrictedTraverse("@@hplc_detail")()
        self.assertIn("15.915383", html)
        self.assertIn("98.427166", html)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHPLCAnalysisFunctional))
    return suite
