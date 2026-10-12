# -*- coding: utf-8 -*-

import unittest2 as unittest

from hoch.lims import dynamiccalculation as dc


class DummyCalculation(object):

    def __init__(self, title, rules):
        self.title = title
        setattr(self, dc.RULES_ATTR, rules)

    def __repr__(self):
        return "<Calculation {}>".format(self.title)


class DummyContext(object):
    """Match context with fixed texts per field path
    """

    def __init__(self, **values):
        self.values = dict(
            (key.lower(), map(dc.normalize, texts))
            for key, texts in values.items())

    def get_texts(self, path):
        return self.values.get(path.lower(), [])


def rule(keyword="", criteria=""):
    return {"keyword": keyword, "criteria": criteria}


class TestDynamicCalculation(unittest.TestCase):

    def setUp(self):
        self.original_get_title = dc.api.get_title
        dc.api.get_title = lambda obj: getattr(obj, "title", obj)

    def tearDown(self):
        dc.api.get_title = self.original_get_title

    def test_parse_criteria(self):
        self.assertEqual(
            dc.parse_criteria(u" Processes = Blisteado ; Batch.Product.code="
                              u"101-* ;; invalid ; Empty = "),
            [(u"Processes", u"blisteado"),
             (u"Batch.Product.code", u"101-*")])

    def test_pattern_keeps_equal_signs_after_the_first(self):
        self.assertEqual(dc.parse_criteria(u"Remarks = a=b"),
                         [(u"Remarks", u"a=b")])

    def test_empty_rules_are_ignored(self):
        calc = DummyCalculation("Empty", [rule(), rule(criteria=u"bad")])
        self.assertEqual(dc.get_rules(calc), [])

    def test_keyword_only_rule_is_valid(self):
        calc = DummyCalculation("Keyword", [rule("VAL_*")])
        self.assertEqual(len(dc.get_rules(calc)), 1)

    def test_rule_matches_keyword_and_all_criteria(self):
        context = DummyContext(
            Processes=[u"Preparado matriz de relleno", u"Blisteado"],
            SampleType=[u"NN-50864"])
        self.assertTrue(dc.rule_matches(
            rule("val_*", u"Processes = blisteado; SampleType = NN-*"),
            "VAL_PARACETAMOL", context))
        self.assertFalse(dc.rule_matches(
            rule("UC_*", u"Processes = Blisteado"),
            "VAL_PARACETAMOL", context))
        self.assertFalse(dc.rule_matches(
            rule("VAL_*", u"Processes = Blisteado; SampleType = NN-44533"),
            "VAL_PARACETAMOL", context))

    def test_multivalued_field_matches_any_value(self):
        context = DummyContext(Processes=[u"Acondicionado", u"Blisteado"])
        self.assertTrue(dc.rule_matches(
            rule(criteria=u"Processes = Blisteado"), "VAL_X", context))

    def test_unknown_or_empty_field_never_matches(self):
        context = DummyContext()
        self.assertFalse(dc.rule_matches(
            rule(criteria=u"Unknown = *"), "VAL_X", context))

    def test_specificity(self):
        generic = rule("VAL_*", u"Processes = Blisteado")
        keyword = rule("VAL_CLOTRIMAZOL", u"Processes = Blisteado")
        product = rule("VAL_*", u"Processes = Blisteado; SampleType = "
                                u"NN-44533")
        self.assertGreater(dc.rule_specificity(keyword),
                           dc.rule_specificity(generic))
        self.assertGreater(dc.rule_specificity(product),
                           dc.rule_specificity(keyword))

    def test_resolve_most_specific_rule(self):
        pt = DummyCalculation("Valoracion HPLC 20x6", [
            rule("VAL_*", u"Processes = Blisteado")])
        process = DummyCalculation("Valoracion matriz 6x6", [
            rule("VAL_*", u"Processes = Preparado matriz*")])
        vp = DummyCalculation("Valoracion HPLC 6x6", [
            rule("VAL_CLOTRIMAZOL", u"Processes = Blisteado; "
                                    u"SampleType = NN-44533")])
        calcs = [pt, process, vp]

        blister = DummyContext(Processes=[u"Blisteado"],
                               SampleType=[u"NN-50864"])
        mezcla = DummyContext(Processes=[u"Preparado matriz de relleno"],
                              SampleType=[u"NN-50864"])
        clotri = DummyContext(Processes=[u"Blisteado"],
                              SampleType=[u"NN-44533"])

        resolve = dc.resolve_calculation
        self.assertIs(resolve("VAL_PARACETAMOL", blister, calcs), pt)
        self.assertIs(resolve("VAL_PARACETAMOL", mezcla, calcs), process)
        self.assertIs(resolve("VAL_CLOTRIMAZOL", clotri, calcs), vp)
        self.assertIs(resolve("VAL_CLOTRIMAZOL", blister, calcs), pt)
        self.assertIsNone(resolve("ID_PARACETAMOL", blister, calcs))

    def test_ambiguous_rules_keep_service_default(self):
        one = DummyCalculation("One", [rule("VAL_*")])
        two = DummyCalculation("Two", [rule("VAL_*")])
        self.assertIsNone(dc.resolve_calculation(
            "VAL_PARACETAMOL", DummyContext(), [one, two]))

    def test_same_calculation_matching_twice_is_not_ambiguous(self):
        calc = DummyCalculation("One", [
            rule("VAL_*"), rule("VAL_?ARACETAMOL")])
        self.assertIs(dc.resolve_calculation(
            "VAL_PARACETAMOL", DummyContext(), [calc]), calc)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDynamicCalculation))
    return suite
