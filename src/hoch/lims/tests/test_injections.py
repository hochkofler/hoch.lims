# -*- coding: utf-8 -*-

import unittest2 as unittest

from hoch.lims import calc
from hoch.lims import injections as inj


def row(kind, number, conc):
    return {"type": kind, "number": number, "conc": conc}


class TestInjections(unittest.TestCase):

    def test_normalize_row(self):
        clean = inj.normalize_row({"type": "standard", "number": "3",
                                   "conc": "25,10", "area": "1000"})
        self.assertEqual(clean["type"], inj.STANDARD)
        self.assertEqual(clean["number"], "03")
        self.assertEqual(clean["area"], 1000.0)
        self.assertEqual(clean["vial_number"], u"")

    def test_sort_rows_samples_first_then_by_number(self):
        rows = inj.sort_rows(map(inj.normalize_row, [
            row("ST", "1", 1), row("UNK", "10", 1), row("UNK", "2", 1)]))
        self.assertEqual([(r["type"], r["number"]) for r in rows],
                         [("UNK", "02"), ("UNK", "10"), ("ST", "01")])

    def test_merge_without_override_keeps_existing(self):
        rows, added, replaced, skipped = inj.merge_injections(
            [row("UNK", "1", 50)], [row("UNK", "1", 40), row("UNK", "2", 50)])
        self.assertEqual((added, replaced, skipped), (1, 0, 1))
        self.assertEqual([r["conc"] for r in rows], [50.0, 50.0])

    def test_merge_with_override_replaces(self):
        rows, added, replaced, skipped = inj.merge_injections(
            [row("UNK", "1", 50)], [row("UNK", "1", 40)], override=True)
        self.assertEqual((added, replaced, skipped), (0, 1, 0))
        self.assertEqual(rows[0]["conc"], 40.0)

    def test_same_number_different_type_are_different_injections(self):
        rows, added, replaced, skipped = inj.merge_injections(
            [row("UNK", "1", 50)], [row("ST", "1", 25)])
        self.assertEqual(added, 1)
        self.assertEqual(len(rows), 2)

    def test_content_uniformity_math(self):
        # two units, duplicates: (51 + 49) / 2 and (52 + 48) / 2 -> 100 %
        result = calc.content_uniformity([51, 49, 52, 48], potency=50)
        self.assertAlmostEqual(result["mean"], 100.0)
        self.assertAlmostEqual(result["std"], 0.0)
        self.assertAlmostEqual(result["result"], 0.0)

    def test_content_uniformity_needs_all_units(self):
        self.assertIsNone(calc.content_uniformity([50, 0, 50, 50],
                                                  potency=50))
        self.assertIsNone(calc.content_uniformity([50, 50], potency=50))

    def test_legacy_uniformity_keeps_its_result(self):
        kwargs = dict(("CONC_UNK_{:02d}".format(i + 1), value)
                      for i, value in enumerate([51, 49, 54, 50]))
        result = calc.calc_uniformidad_contenido(
            T=100, k=2.4, SUBGROUPS=2, POTENCIA_DECLARADA=50, **kwargs)
        # units: 100 % and 104 %; mean 102, std 2.828; M = 101.5
        self.assertAlmostEqual(result, 0.5 + 2.4 * 8 ** 0.5, 6)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestInjections))
    return suite
