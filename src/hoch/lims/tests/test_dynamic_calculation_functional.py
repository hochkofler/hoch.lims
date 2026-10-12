# -*- coding: utf-8 -*-

import transaction
import unittest2 as unittest
from bika.lims import api
from bika.lims.utils.analysisrequest import create_analysisrequest
from bika.lims.utils.analysisrequest import create_partition
from bika.lims.workflow import doActionFor
from DateTime import DateTime
from hoch.lims.dynamiccalculation import reapply
from hoch.lims.extender.behaviors.dynamiccalculation import \
    IDynamicCalculationRulesBehavior
from hoch.lims.tests.base import SimpleTestCase
from hoch.lims.tests.base import SimpleTestLayer
from plone.app.testing import FunctionalTesting
from plone.app.testing import TEST_USER_ID
from plone.app.testing import setRoles
from Products.Archetypes.event import ObjectEditedEvent
from zope.configuration import xmlconfig
from zope.event import notify


class DynamicCalculationLayer(SimpleTestLayer):
    """Simple layer plus hoch.lims' overrides.zcml

    In an instance, overrides.zcml is loaded by z3c.autoinclude
    """

    def setUpZope(self, app, configurationContext):
        super(DynamicCalculationLayer, self).setUpZope(
            app, configurationContext)
        import hoch.lims
        xmlconfig.includeOverrides(
            configurationContext, "overrides.zcml", package=hoch.lims)
        configurationContext.execute_actions()


DYNAMIC_CALCULATION_FIXTURE = DynamicCalculationLayer()
DYNAMIC_CALCULATION_TESTING = FunctionalTesting(
    bases=(DYNAMIC_CALCULATION_FIXTURE, ),
    name="hoch.lims:DynamicCalculationTesting"
)

# Service calculation: 4 sample injections x 2 standard injections
FORMULA_4X2 = ("([CONC_UNK_01] + [CONC_UNK_02] + [CONC_UNK_03] "
               "+ [CONC_UNK_04]) / 4 + 0 * ([CONC_ST_01] + [CONC_ST_02])")

# Dynamic calculation for the process stage: 2 x 1
FORMULA_2X1 = "([CONC_UNK_01] + [CONC_UNK_02]) / 2 + 0 * [CONC_ST_01]"

INJECTIONS = ["CONC_UNK_01", "CONC_UNK_02", "CONC_UNK_03", "CONC_UNK_04",
              "CONC_ST_01", "CONC_ST_02"]


class TestDynamicCalculationFunctional(SimpleTestCase):
    layer = DYNAMIC_CALCULATION_TESTING

    def setUp(self):
        super(TestDynamicCalculationFunctional, self).setUp()
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
        category = api.create(
            setup.analysiscategories, "AnalysisCategory", title="Valoracion")

        services = bikasetup.bika_analysisservices
        self.injections = {}
        for keyword in INJECTIONS:
            self.injections[keyword] = api.create(
                services, "AnalysisService", title=keyword, Keyword=keyword,
                Category=api.get_uid(category))
        self.val = api.create(
            services, "AnalysisService", title="Valoracion Paracetamol",
            Keyword="VAL_PARACETAMOL", Category=api.get_uid(category))

        calculations = setup.calculations
        self.calc_4x2 = api.create(
            calculations, "Calculation", title="Valoracion HPLC 4x2")
        self.calc_4x2.setFormula(FORMULA_4X2)
        self.calc_2x1 = api.create(
            calculations, "Calculation", title="Valoracion proceso 2x1")
        self.calc_2x1.setFormula(FORMULA_2X1)
        self.set_rules(self.calc_2x1, [
            {"keyword": "VAL_*", "criteria": "Template = *-MEZCLA"}])
        self.val.setCalculation(self.calc_4x2)

        self.mezcla = api.create(
            setup.sampletemplates, "SampleTemplate",
            title="NN-50864-MEZCLA", SampleType=self.product)
        self.pt = api.create(
            setup.sampletemplates, "SampleTemplate",
            title="NN-50864-PT", SampleType=self.product)
        transaction.commit()

    def set_rules(self, calculation, rules):
        behavior = IDynamicCalculationRulesBehavior(calculation)
        behavior.dynamic_calculation_rules = rules

    def new_sample(self, template=None, **extra):
        values = {
            "Client": api.get_uid(self.client),
            "Contact": api.get_uid(self.contact),
            "DateSampled": DateTime().strftime("%Y-%m-%d"),
            "SampleType": api.get_uid(self.product),
        }
        if template:
            values["Template"] = api.get_uid(template)
        values.update(extra)
        sample = create_analysisrequest(
            self.client, self.request, values, [api.get_uid(self.val)])
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

    def test_behavior_is_enabled_on_calculation(self):
        fti = api.get_tool("portal_types").get("Calculation")
        self.assertIn(
            "hoch.lims.extender.behaviors.dynamiccalculation"
            ".IDynamicCalculationRulesBehavior", fti.behaviors)

    def test_without_matching_rule_service_calculation_is_kept(self):
        sample = self.new_sample(self.pt)
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_4x2)
        self.assertEqual(self.keywords(sample),
                         sorted(INJECTIONS + ["VAL_PARACETAMOL"]))

    def test_matching_rule_sets_calculation_and_dependencies(self):
        sample = self.new_sample(self.mezcla)
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_2x1)
        self.assertEqual(self.keywords(sample), [
            "CONC_ST_01", "CONC_UNK_01", "CONC_UNK_02", "VAL_PARACETAMOL"])

    def test_dynamic_calculation_computes_with_its_dependencies(self):
        sample = self.new_sample(self.mezcla)
        for keyword, result in (("CONC_UNK_01", "98"), ("CONC_UNK_02", "102"),
                                ("CONC_ST_01", "25")):
            self.get_analysis(sample, keyword).setResult(result)
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertTrue(val.calculateResult(override=True))
        self.assertEqual(api.to_float(val.getResult()), 100.0)

    def test_rule_needing_more_dependencies_than_service(self):
        # the service calculation is the small one, the rule the big one
        self.val.setCalculation(self.calc_2x1)
        self.set_rules(self.calc_2x1, [])
        self.set_rules(self.calc_4x2, [
            {"keyword": "VAL_PARACETAMOL", "criteria": "SampleType = NN-50864"}])
        sample = self.new_sample(self.pt)
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_4x2)
        self.assertEqual(self.keywords(sample),
                         sorted(INJECTIONS + ["VAL_PARACETAMOL"]))

    def test_saving_analyses_keeps_dynamic_dependencies_and_results(self):
        self.val.setCalculation(self.calc_2x1)
        self.set_rules(self.calc_2x1, [])
        self.set_rules(self.calc_4x2, [
            {"keyword": "VAL_*", "criteria": "Template = *-PT"}])
        sample = self.new_sample(self.pt)
        unk_04 = self.get_analysis(sample, "CONC_UNK_04")
        unk_04.setResult("101")

        # "Manage analyses" saves the selected services again
        sample.setAnalyses([api.get_uid(self.val)])

        self.assertEqual(self.keywords(sample),
                         sorted(INJECTIONS + ["VAL_PARACETAMOL"]))
        unk_04 = self.get_analysis(sample, "CONC_UNK_04")
        self.assertEqual(unk_04.getResult(), "101")

    def test_partition_keeps_dynamic_calculation(self):
        sample = self.new_sample(self.mezcla)
        analyses = sample.getAnalyses(full_objects=True)
        partition = create_partition(
            sample, self.request, analyses, sample_type=self.api_type)

        val = self.get_analysis(partition, "VAL_PARACETAMOL")
        self.assertEqual(api.get_parent(val), partition)
        self.assertEqual(val.getCalculation(), self.calc_2x1)
        own = sorted([an.getKeyword()
                      for an in partition.objectValues("Analysis")])
        self.assertEqual(own, [
            "CONC_ST_01", "CONC_UNK_01", "CONC_UNK_02", "VAL_PARACETAMOL"])

    def test_rule_changes_apply_while_no_data_captured(self):
        sample = self.new_sample(self.mezcla)
        self.set_rules(self.calc_2x1, [])
        sample.setAnalyses([api.get_uid(self.val)])
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_4x2)
        self.assertEqual(self.keywords(sample),
                         sorted(INJECTIONS + ["VAL_PARACETAMOL"]))

    def test_calculation_is_frozen_once_a_dependency_has_result(self):
        sample = self.new_sample(self.mezcla)
        self.get_analysis(sample, "CONC_UNK_01").setResult("98")
        self.set_rules(self.calc_2x1, [])
        sample.setAnalyses([api.get_uid(self.val)])
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_2x1)
        self.assertEqual(self.keywords(sample), [
            "CONC_ST_01", "CONC_UNK_01", "CONC_UNK_02", "VAL_PARACETAMOL"])

    def test_field_set_after_sampling_reapplies_on_edit(self):
        self.set_rules(self.calc_2x1, [
            {"keyword": "VAL_*", "criteria": "ClientSampleID = MEZ-*"}])
        sample = self.new_sample()
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_4x2)

        # the field is set after sampling, e.g. from the sample header
        sample.setClientSampleID("MEZ-001")
        notify(ObjectEditedEvent(sample))

        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_2x1)
        self.assertEqual(self.keywords(sample), [
            "CONC_ST_01", "CONC_UNK_01", "CONC_UNK_02", "VAL_PARACETAMOL"])

    def test_reapply_keeps_price_and_hidden(self):
        self.set_rules(self.calc_2x1, [
            {"keyword": "VAL_*", "criteria": "ClientSampleID = MEZ-*"}])
        sample = self.new_sample()
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        val.setHidden(True)
        val.setPrice("42.00")
        sample.setClientSampleID("MEZ-001")
        self.assertTrue(reapply(sample))
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_2x1)
        self.assertTrue(val.getHidden())
        self.assertEqual(api.to_float(val.getPrice()), 42.0)

    def test_batch_field_criterion(self):
        batch = api.create(self.client, "Batch", title="LOTE-PROCESO-7")
        self.set_rules(self.calc_2x1, [
            {"keyword": "VAL_*", "criteria": "Batch.title = lote-proceso-*"}])
        sample = self.new_sample(Batch=api.get_uid(batch))
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_2x1)

    def test_analysis_condition_criterion(self):
        self.val.setConditions([{
            "title": "Esquema", "description": "", "type": "text",
            "choices": "", "default": "", "required": False,
            "report": False}])
        self.set_rules(self.calc_2x1, [
            {"keyword": "VAL_*", "criteria": "Condition.Esquema = 2x1"}])
        sample = self.new_sample()
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_4x2)

        conditions = val.getConditions(empties=True)
        for condition in conditions:
            condition["value"] = "2x1"
        val.setConditions(conditions)
        self.assertTrue(reapply(sample))

        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_2x1)
        self.assertEqual(self.keywords(sample), [
            "CONC_ST_01", "CONC_UNK_01", "CONC_UNK_02", "VAL_PARACETAMOL"])

    def test_entered_interim_values_survive_relinking(self):
        self.val.setInterimFields([{
            "keyword": "potencia_declarada_m", "title": "Potencia",
            "value": "500"}])
        self.set_rules(self.calc_2x1, [
            {"keyword": "VAL_*", "criteria": "ClientSampleID = MEZ-*"}])
        sample = self.new_sample()
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        interims = val.getInterimFields()
        interims[0]["value"] = "650"
        val.setInterimFields(interims)

        sample.setClientSampleID("MEZ-001")
        self.assertTrue(reapply(sample))
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(val.getCalculation(), self.calc_2x1)
        values = dict((i["keyword"], i.get("value"))
                      for i in val.getInterimFields())
        self.assertEqual(values.get("potencia_declarada_m"), "650")

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDynamicCalculationFunctional))
    return suite
