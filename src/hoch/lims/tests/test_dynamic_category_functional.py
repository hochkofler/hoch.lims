# -*- coding: utf-8 -*-

import transaction
import unittest2 as unittest
from bika.lims import api
from bika.lims.utils.analysisrequest import create_analysisrequest
from bika.lims.utils.analysisrequest import create_partition
from bika.lims.workflow import doActionFor
from DateTime import DateTime
from hoch.lims.dynamiccalculation import get_requested_services
from hoch.lims.extender.behaviors.dynamiccalculation import \
    IDynamicCalculationRulesBehavior
from hoch.lims.extender.behaviors.dynamiccategory import \
    IDynamicCategoryBehavior
from hoch.lims.tests.base import SimpleTestCase
from hoch.lims.tests.test_dynamic_calculation_functional import \
    DYNAMIC_CALCULATION_TESTING
from hoch.lims.tests.test_dynamic_calculation_functional import FORMULA_2X1
from hoch.lims.tests.test_dynamic_calculation_functional import FORMULA_4X2
from hoch.lims.tests.test_dynamic_calculation_functional import INJECTIONS
from plone.app.testing import TEST_USER_ID
from plone.app.testing import setRoles
from Products.Archetypes.event import ObjectEditedEvent
from zope.event import notify

# Real case: content uniformity is not done on the filling matrix, so its
# analyses (and the injections only it needs) must not be created
MATRIX = "MEZ-*"
PROCESS_INJECTIONS = ["CONC_ST_01", "CONC_UNK_01", "CONC_UNK_02"]


class TestDynamicCategoryFunctional(SimpleTestCase):
    layer = DYNAMIC_CALCULATION_TESTING

    def setUp(self):
        super(TestDynamicCategoryFunctional, self).setUp()
        setRoles(self.portal, TEST_USER_ID, ["Manager", "LabManager"])
        setup = self.portal.setup
        bikasetup = api.get_bika_setup()

        self.client = api.create(
            self.portal.clients, "Client", Name="IFA", ClientID="IFA")
        self.contact = api.create(
            self.client, "Contact", Firstname="Lab", Lastname="Ifa")
        self.product = api.create(
            setup.sampletypes, "SampleType", title="NN-50864", Prefix="P")
        self.api_type = api.create(
            setup.sampletypes, "SampleType", title="PARACETAMOL", Prefix="A")

        categories = setup.analysiscategories
        support = api.create(categories, "AnalysisCategory", title="Soporte")
        assay = api.create(categories, "AnalysisCategory", title="Valoracion")
        self.uniformity = api.create(
            categories, "AnalysisCategory", title="Uniformidad de contenido")
        self.set_exclusion(self.uniformity,
                           u"ClientSampleID = {}".format(MATRIX))

        services = bikasetup.bika_analysisservices
        for keyword in INJECTIONS:
            api.create(services, "AnalysisService", title=keyword,
                       Keyword=keyword, Category=api.get_uid(support))
        self.val = api.create(
            services, "AnalysisService", title="Valoracion Paracetamol",
            Keyword="VAL_PARACETAMOL", Category=api.get_uid(assay))
        self.uc = api.create(
            services, "AnalysisService", title="Uniformidad Paracetamol",
            Keyword="UC_PARACETAMOL", Category=api.get_uid(self.uniformity))

        calculations = setup.calculations
        self.calc_4x2 = api.create(
            calculations, "Calculation", title="Valoracion HPLC 4x2")
        self.calc_4x2.setFormula(FORMULA_4X2)
        self.calc_uc = api.create(
            calculations, "Calculation", title="Uniformidad 4x2")
        self.calc_uc.setFormula(FORMULA_4X2)
        self.calc_2x1 = api.create(
            calculations, "Calculation", title="Valoracion proceso 2x1")
        self.calc_2x1.setFormula(FORMULA_2X1)
        IDynamicCalculationRulesBehavior(self.calc_2x1) \
            .dynamic_calculation_rules = [
                {"keyword": "VAL_*",
                 "criteria": u"ClientSampleID = {}".format(MATRIX)}]
        self.val.setCalculation(self.calc_4x2)
        self.uc.setCalculation(self.calc_uc)
        transaction.commit()

    def set_exclusion(self, category, text):
        IDynamicCategoryBehavior(category).dynamic_exclude_when = text

    def new_sample(self, client_sample_id=""):
        values = {
            "Client": api.get_uid(self.client),
            "Contact": api.get_uid(self.contact),
            "DateSampled": DateTime().strftime("%Y-%m-%d"),
            "SampleType": api.get_uid(self.product),
            "ClientSampleID": client_sample_id,
        }
        services = [api.get_uid(self.val), api.get_uid(self.uc)]
        sample = create_analysisrequest(
            self.client, self.request, values, services)
        doActionFor(sample, "receive")
        return sample

    def get_analysis(self, sample, keyword):
        for analysis in sample.getAnalyses(full_objects=True):
            if analysis.getKeyword() == keyword:
                return analysis
        return None

    def keywords(self, sample):
        return sorted([analysis.getKeyword()
                       for analysis in sample.getAnalyses(full_objects=True)])

    def edit(self, sample, client_sample_id):
        sample.setClientSampleID(client_sample_id)
        notify(ObjectEditedEvent(sample))

    def test_behavior_is_enabled_on_category(self):
        fti = api.get_tool("portal_types").get("AnalysisCategory")
        self.assertIn(
            "hoch.lims.extender.behaviors.dynamiccategory"
            ".IDynamicCategoryBehavior", fti.behaviors)

    def test_finished_product_keeps_all_analyses(self):
        sample = self.new_sample("PT-001")
        self.assertEqual(self.keywords(sample), sorted(
            INJECTIONS + ["UC_PARACETAMOL", "VAL_PARACETAMOL"]))

    def test_matrix_excludes_category_and_its_injections(self):
        sample = self.new_sample("MEZ-001")
        self.assertEqual(self.keywords(sample),
                         sorted(PROCESS_INJECTIONS + ["VAL_PARACETAMOL"]))
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_2x1)
        # the request is remembered, so the analysis can come back
        self.assertIn(api.get_uid(self.uc), get_requested_services(sample))

    def test_criteria_set_after_sampling_removes_category(self):
        sample = self.new_sample()
        self.assertIsNotNone(self.get_analysis(sample, "UC_PARACETAMOL"))
        self.edit(sample, "MEZ-001")
        self.assertEqual(self.keywords(sample),
                         sorted(PROCESS_INJECTIONS + ["VAL_PARACETAMOL"]))

    def test_excluded_analyses_come_back(self):
        sample = self.new_sample("MEZ-001")
        self.edit(sample, "PT-001")
        self.assertEqual(self.keywords(sample), sorted(
            INJECTIONS + ["UC_PARACETAMOL", "VAL_PARACETAMOL"]))
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_4x2)

    def test_analysis_with_result_is_never_removed(self):
        sample = self.new_sample()
        self.get_analysis(sample, "UC_PARACETAMOL").setResult("7")
        self.edit(sample, "MEZ-001")
        uc = self.get_analysis(sample, "UC_PARACETAMOL")
        self.assertIsNotNone(uc)
        self.assertEqual(uc.getResult(), "7")

    def test_any_line_excludes(self):
        self.set_exclusion(self.uniformity, u"ClientSampleID = OTRO-*\n"
                                            u"ClientSampleID = MEZ-*")
        sample = self.new_sample("MEZ-001")
        self.assertIsNone(self.get_analysis(sample, "UC_PARACETAMOL"))

    def test_empty_exclusion_keeps_default_behaviour(self):
        self.set_exclusion(self.uniformity, u"")
        sample = self.new_sample("MEZ-001")
        self.assertIsNotNone(self.get_analysis(sample, "UC_PARACETAMOL"))

    def test_partitions_with_excluded_category(self):
        sample = self.new_sample("MEZ-001")
        analyses = sample.getAnalyses(full_objects=True)
        partition = create_partition(
            sample, self.request, analyses, sample_type=self.api_type)
        own = sorted([an.getKeyword()
                      for an in partition.objectValues("Analysis")])
        self.assertEqual(own, sorted(PROCESS_INJECTIONS +
                                     ["VAL_PARACETAMOL"]))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDynamicCategoryFunctional))
    return suite
