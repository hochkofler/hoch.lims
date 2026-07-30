# -*- coding: utf-8 -*-

import unittest2 as unittest

from hoch.lims.tests.base import SIMPLE_TESTING
from senaite.core.browser.samples import view as samples_view
from senaite.core.browser.samples.view import SamplesView


class TestSampleKeywordUnicode(unittest.TestCase):

    layer = SIMPLE_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]

    def test_non_ascii_byte_keyword_renders_filter_chip(self):
        view = SamplesView(self.portal, self.request)
        keyword = u"CONCENTRACIÓN".encode("utf-8")

        chip = view.render_keyword_filter_chip(keyword, [keyword])

        self.assertIsInstance(chip, unicode)
        self.assertIn(u"<code>CONCENTRACIÓN</code>", chip)
        self.assertIn(u'class="analysis-keyword-filter active"', chip)
        self.assertIn(u"samples_column_filters=", chip)

    def test_localized_filter_title_renders_for_ascii_keyword(self):
        view = SamplesView(self.portal, self.request)

        original_translate = samples_view.t
        samples_view.t = lambda message: \
            u"Filtrar muestras por este análisis".encode("utf-8")
        try:
            chip = view.render_keyword_filter_chip(u"CONC_ST_01", [])
        finally:
            samples_view.t = original_translate

        self.assertIsInstance(chip, unicode)
        self.assertIn(u"CONC_ST_01", chip)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestSampleKeywordUnicode)
