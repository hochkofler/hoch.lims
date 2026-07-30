# -*- coding: utf-8 -*-

import unittest2 as unittest

from hoch.lims.patches.exportimport import setupdata


class DummySetup(object):

    instrumenttypes = object()
    sampleconditions = object()


class DummyContext(object):

    setup = DummySetup()


class DummyImporter(object):

    def __init__(self, rows):
        self.context = DummyContext()
        self.rows = rows

    def get_rows(self, start_row):
        return self.rows


class TestSetupDataUnicode(unittest.TestCase):

    def setUp(self):
        self.created = []
        self.original_create = setupdata.api.create
        setupdata.api.create = self.create

    def tearDown(self):
        setupdata.api.create = self.original_create

    def create(self, container, portal_type, **kwargs):
        self.created.append((container, portal_type, kwargs))

    def test_instrument_type_title_is_unicode(self):
        importer = DummyImporter([{
            "title": u"Espectrómetro Óptico".encode("utf-8"),
            "description": "unchanged",
        }])

        setupdata.import_instrument_types(importer)

        container, portal_type, kwargs = self.created[0]
        self.assertIs(importer.context.setup.instrumenttypes, container)
        self.assertEqual("InstrumentType", portal_type)
        self.assertIsInstance(kwargs["title"], unicode)
        self.assertEqual(u"Espectrómetro Óptico", kwargs["title"])
        self.assertEqual("unchanged", kwargs["description"])

    def test_sample_condition_title_is_unicode_and_empty_title_is_skipped(self):
        importer = DummyImporter([
            {"title": "", "description": "ignored"},
            {
                "title": u"Condición Térmica Óptima".encode("utf-8"),
                "description": "unchanged",
            },
        ])

        setupdata.import_sample_conditions(importer)

        self.assertEqual(1, len(self.created))
        container, portal_type, kwargs = self.created[0]
        self.assertIs(importer.context.setup.sampleconditions, container)
        self.assertEqual("SampleCondition", portal_type)
        self.assertIsInstance(kwargs["title"], unicode)
        self.assertEqual(u"Condición Térmica Óptima", kwargs["title"])
        self.assertEqual("unchanged", kwargs["description"])


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestSetupDataUnicode)
