# -*- coding: utf-8 -*-

from StringIO import StringIO

import transaction
import unittest2 as unittest
from bika.lims import api
from bika.lims.utils.analysisrequest import create_analysisrequest
from bika.lims.utils.analysisrequest import create_partition
from bika.lims.workflow import doActionFor
from DateTime import DateTime
from hoch.lims import injections as inj
from hoch.lims.exportimport.instruments.shimadzu.nexera import \
    quantitativeResultsImportInterface
from hoch.lims.exportimport.instruments.shimadzu.nexera import \
    quantitiveResultParser
from hoch.lims.tests.base import SimpleTestCase
from hoch.lims.tests.test_dynamic_calculation_functional import \
    DYNAMIC_CALCULATION_TESTING
from plone.app.testing import TEST_USER_ID
from plone.app.testing import setRoles
from senaite.core.exportimport.instruments.importer import \
    AnalysisResultsImporter

HEADER = (u"Data Filename\tSample Name\tSample ID\tSample Type\tVial#\t"
          u"Date Acquired\tRet. Time\tArea\tConc.\tNTP(USP)")


def run_file(sample_id, injections, peak=u"PARACETAMOL"):
    """Returns the text of a Nexera quantitative export

    :param injections: list of (type, number, conc) tuples
    """
    lines = [u"ID#\t1", u"Name\t{}".format(peak), HEADER]
    for index, (kind, number, conc) in enumerate(injections, 1):
        name = u"{}_{:02d}".format(kind == "ST" and u"ST" or u"MUESTRA",
                                   number)
        sample_type = kind == "ST" and u"Standard" or u"Unknown"
        lines.append(u"\t".join([
            u"{}".format(index), u"run_{}.lcd".format(index), name,
            sample_id, sample_type, u"{}".format(10 + index),
            u"15/10/2026 10:{:02d}:00".format(index), u"2.10",
            u"{}".format(1000 + index), u"{}".format(conc), u"8100"]))
    return u"\n".join(lines) + u"\n"


class UploadedFile(StringIO):
    filename = "nexera_run.txt"


class TestInjectionsFunctional(SimpleTestCase):
    layer = DYNAMIC_CALCULATION_TESTING

    def setUp(self):
        super(TestInjectionsFunctional, self).setUp()
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

        calculations = setup.calculations
        self.assay_calc = api.create(
            calculations, "Calculation", title="Valoracion HPLC")
        self.assay_calc.setPythonImports([
            {"module": "hoch.lims.calc", "function": "calc_assay"}])
        self.assay_calc.setInterimFields([
            {"keyword": "potencia_declarada_m", "title": "Potencia"},
            {"keyword": "n_unk", "title": "N muestra"},
            {"keyword": "n_st", "title": "N estandar"}])
        self.assay_calc.setFormula("calc_assay(context=%(context_uid)s)")
        self.uc_calc = api.create(
            calculations, "Calculation", title="Uniformidad HPLC")
        self.uc_calc.setPythonImports([
            {"module": "hoch.lims.calc",
             "function": "calc_content_uniformity"}])
        self.uc_calc.setInterimFields([
            {"keyword": "potencia_declarada_m", "title": "Potencia"},
            {"keyword": "mean", "title": "Media"},
            {"keyword": "std", "title": "Desviacion"},
            {"keyword": "m", "title": "M"}])
        self.uc_calc.setFormula(
            "calc_content_uniformity(context=%(context_uid)s, T=100, k=2.4)")

        services = bikasetup.bika_analysisservices
        cat = api.get_uid(category)
        self.val = api.create(services, "AnalysisService",
                              title="Valoracion Paracetamol",
                              Keyword="VAL_PARACETAMOL", Category=cat)
        self.val.getField(inj.RECEIVES_FIELD).set(self.val, True)
        self.val.setCalculation(self.assay_calc)
        self.uc = api.create(services, "AnalysisService",
                             title="Uniformidad Paracetamol",
                             Keyword="UC_PARACETAMOL", Category=cat)
        self.uc.setCalculation(self.uc_calc)
        for service in (self.val, self.uc):
            service.setInterimFields([{
                "keyword": "potencia_declarada_m", "title": "Potencia",
                "value": "50"}])
        # services of samples created before the injections table
        self.conc = api.create(services, "AnalysisService",
                               title="Conc muestra 01", Keyword="CONC_UNK_01",
                               Category=cat)
        transaction.commit()

    def new_sample(self, services):
        values = {
            "Client": api.get_uid(self.client),
            "Contact": api.get_uid(self.contact),
            "DateSampled": DateTime().strftime("%Y-%m-%d"),
            "SampleType": api.get_uid(self.product),
        }
        sample = create_analysisrequest(
            self.client, self.request, values, map(api.get_uid, services))
        doActionFor(sample, "receive")
        return sample

    def new_partitioned_sample(self):
        sample = self.new_sample([self.val, self.uc])
        partition = create_partition(
            sample, self.request, sample.getAnalyses(full_objects=True),
            sample_type=self.api_type)
        return sample, partition

    def get_analysis(self, sample, keyword):
        for analysis in sample.getAnalyses(full_objects=True):
            if analysis.getKeyword() == keyword:
                return analysis
        return None

    def import_text(self, text, override=None):
        infile = UploadedFile(text.encode("utf-8"))
        parser = quantitiveResultParser(infile)
        importer = quantitativeResultsImportInterface(self.portal)
        AnalysisResultsImporter.__init__(
            importer, parser, self.portal,
            override=override or [False, False],
            allowed_sample_states=["sample_received"])
        importer.process()
        return importer

    def test_fields_exist(self):
        self.assertTrue(inj.receives_injections(self.val))
        self.assertFalse(inj.receives_injections(self.uc))
        sample = self.new_sample([self.val])
        val = self.get_analysis(sample, "VAL_PARACETAMOL")
        self.assertEqual(inj.get_injections(val), [])

    def test_no_injection_analyses_are_created(self):
        sample, partition = self.new_partitioned_sample()
        keywords = sorted(an.getKeyword()
                          for an in partition.objectValues("Analysis"))
        self.assertEqual(keywords, ["UC_PARACETAMOL", "VAL_PARACETAMOL"])

    def test_import_stores_rows_and_calculates(self):
        sample, partition = self.new_partitioned_sample()
        text = run_file(sample.getId(), [
            ("ST", 1, 25.1), ("ST", 2, 25.0),
            ("UNK", 1, 51.0), ("UNK", 2, 49.0),
            ("UNK", 3, 50.0), ("UNK", 4, 50.0)])
        importer = self.import_text(text)
        self.assertFalse(importer.errors, importer.errors)

        val = self.get_analysis(partition, "VAL_PARACETAMOL")
        rows = inj.get_injections(val)
        self.assertEqual(len(rows), 6)
        self.assertEqual([(r["type"], r["number"]) for r in rows], [
            ("UNK", "01"), ("UNK", "02"), ("UNK", "03"), ("UNK", "04"),
            ("ST", "01"), ("ST", "02")])
        first = rows[0]
        self.assertEqual(first["conc"], 51.0)
        self.assertEqual(first["ret_time"], 2.1)
        self.assertEqual(first["peak"], u"PARACETAMOL")
        self.assertTrue(first["data_file"].endswith(".lcd"))

        # (51 + 49 + 50 + 50) / 4 / 50 * 100
        self.assertAlmostEqual(api.to_float(val.getResult()), 100.0)
        interims = dict((i["keyword"], i.get("value"))
                        for i in val.getInterimFields())
        self.assertEqual(interims.get("n_unk"), 4)
        self.assertEqual(interims.get("n_st"), 2)

        # content uniformity reads the injections of the assay
        uc = self.get_analysis(partition, "UC_PARACETAMOL")
        self.assertEqual(inj.get_injections(uc), [])
        self.assertAlmostEqual(api.to_float(uc.getResult()), 0.0)

    def test_any_number_of_injections(self):
        sample, partition = self.new_partitioned_sample()
        injections = [("UNK", n, 50.0) for n in range(1, 13)]
        self.import_text(run_file(sample.getId(), injections))
        val = self.get_analysis(partition, "VAL_PARACETAMOL")
        self.assertEqual(len(inj.get_injections(val)), 12)
        self.assertAlmostEqual(api.to_float(val.getResult()), 100.0)

    def test_reinjection_respects_override(self):
        sample, partition = self.new_partitioned_sample()
        self.import_text(run_file(sample.getId(), [
            ("UNK", 1, 50.0), ("UNK", 2, 50.0)]))
        val = self.get_analysis(partition, "VAL_PARACETAMOL")

        # without override, the existing injection is kept
        importer = self.import_text(run_file(sample.getId(), [
            ("UNK", 2, 40.0), ("UNK", 3, 50.0)]))
        rows = dict((r["number"], r["conc"])
                    for r in inj.get_injections(val))
        self.assertEqual(rows, {"01": 50.0, "02": 50.0, "03": 50.0})
        self.assertTrue(importer.warns)

        # with override, the reinjection replaces it
        self.import_text(run_file(sample.getId(), [("UNK", 2, 40.0)]),
                         override=[True, False])
        rows = dict((r["number"], r["conc"])
                    for r in inj.get_injections(val))
        self.assertEqual(rows["02"], 40.0)
        # (50 + 40 + 50) / 3 / 50 * 100
        self.assertAlmostEqual(api.to_float(val.getResult()), 93.3333, 3)

    def test_samples_with_injection_analyses_keep_working(self):
        sample = self.new_sample([self.conc])
        self.import_text(run_file(sample.getId(), [("UNK", 1, 50.5)]))
        conc = self.get_analysis(sample, "CONC_UNK_01")
        self.assertEqual(api.to_float(conc.getResult()), 50.5)

    def test_declared_potency_from_product_matrix(self):
        for service in (self.val, self.uc):
            service.setInterimFields([])
        matrix = api.create(self.portal.setup.samplematrices, "SampleMatrix",
                            title="NN-50864")
        matrix.variables_table = [{
            "service": api.get_uid(self.val), "parameter": "declared_potency",
            "value": 25.0, "unit": "mg"}]
        self.product.setSampleMatrix(matrix)

        sample, partition = self.new_partitioned_sample()
        self.import_text(run_file(sample.getId(), [
            ("UNK", 1, 25.0), ("UNK", 2, 25.0)]))
        val = self.get_analysis(partition, "VAL_PARACETAMOL")
        self.assertAlmostEqual(api.to_float(val.getResult()), 100.0)
        interims = dict((i["keyword"], i.get("value"))
                        for i in val.getInterimFields())
        self.assertEqual(interims.get("potencia_declarada_m"), 25.0)

    def test_correction_from_the_view_recalculates(self):
        sample, partition = self.new_partitioned_sample()
        self.import_text(run_file(sample.getId(), [
            ("UNK", 1, 50.0), ("UNK", 2, 50.0)]))
        val = self.get_analysis(partition, "VAL_PARACETAMOL")
        view = val.restrictedTraverse("@@injections")
        self.assertTrue(view.can_edit())
        rows = view.get_rows()
        rows[1]["conc"] = 40.0
        view.save(rows)
        # (50 + 40) / 2 / 50 * 100
        self.assertAlmostEqual(api.to_float(val.getResult()), 90.0)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestInjectionsFunctional))
    return suite
