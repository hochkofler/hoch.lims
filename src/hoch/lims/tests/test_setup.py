# -*- coding: utf-8 -*-

from Products.CMFPlone.utils import get_installer
from senaite.impress.interfaces import ITemplateFinder
from zope.component import getUtility

from hoch.lims.tests.base import SimpleTestCase
from hoch.lims.interfaces import IHochLims


class TestSetup(SimpleTestCase):
    """Test Setup
    """

    def test_is_addon_installed(self):
        qi = get_installer(self.portal)
        self.assertTrue(qi.is_product_installed("hoch.lims"))

    def test_browser_layer_active(self):
        self.assertTrue(IHochLims.providedBy(self.request))

    def test_custom_report_templates(self):
        finder = getUtility(ITemplateFinder)
        record = {}
        for resource in finder.resources:
            if resource.get("name") == "hoch.lims":
                record = resource
        self.assertTrue(len(record.get("contents", [])) > 0)

    def test_jsonapi_registered(self):
        endpoint = "hoch.lims/version"
        response = self.get_json(endpoint)
        self.assertEquals(response.get("version"), "1.0.0")


def test_suite():
    from unittest import TestSuite
    from unittest import makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestSetup))
    return suite
