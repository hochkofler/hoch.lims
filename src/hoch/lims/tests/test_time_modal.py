# -*- coding: utf-8 -*-

import unittest2 as unittest

from hoch.lims.browser.analysis.edit import HochEditAnalysisForm
from hoch.lims.tests.base import SIMPLE_TESTING
from hoch.lims.tests.base import SimpleTestCase


class DummyModalView(object):

    def __init__(self, context, request, result_type="numeric", interims=None):
        self.context = context
        self.request = request
        self.result_type = result_type
        self.interims = interims or []

    def get_result_type(self):
        return self.result_type

    def get_result(self):
        return "01:02:03"

    def get_interims(self):
        return self.interims

    def is_field_visible(self, name):
        return name == "result"

    def is_calculated(self):
        return False

    def parse_multi_value(self, value):
        return []

    def parse_date(self, value):
        return ""

    def parse_time(self, value):
        return value

    def __getattr__(self, name):
        if name in (
                "get_result_options", "get_methods", "get_instruments",
                "get_analysts", "get_unit_choices", "get_result_values"):
            return lambda *args, **kwargs: []
        if name.startswith("is_"):
            return lambda *args, **kwargs: False
        if name.startswith("get_"):
            return lambda *args, **kwargs: ""
        raise AttributeError(name)


class DummyRequest(dict):

    @property
    def form(self):
        return self


class DummyTimeInterimAnalysis(object):

    def getInterimFields(self):
        return [{
            "keyword": "IncubationTime",
            "result_type": "time",
        }]


class TestTimeModal(SimpleTestCase):
    layer = SIMPLE_TESTING

    def render_modal(self, result_type="numeric", interims=None):
        view = DummyModalView(
            self.portal, self.request, result_type=result_type,
            interims=interims)
        template = HochEditAnalysisForm.__dict__["template"]
        return template.__get__(view, DummyModalView)()

    def test_time_result_renders_time_control(self):
        rendered = self.render_modal(result_type="time")
        self.assertIn('type="time" name="Result"', rendered)
        self.assertIn('step="1"', rendered)
        self.assertNotIn(
            'type="text" name="Result" class="form-control numeric"',
            rendered)

    def test_time_interim_renders_visible_and_hidden_controls(self):
        interims = [{
            "keyword": "IncubationTime",
            "title": "Incubation time",
            "value": "01:02:03",
            "result_type": "time",
            "options": [],
            "hidden": False,
            "unit": "",
        }]
        rendered = self.render_modal(interims=interims)
        self.assertIn('type="time"', rendered)
        self.assertIn('name="IncubationTime-time"', rendered)
        self.assertIn('type="hidden" name="IncubationTime"', rendered)

    def test_time_interim_visible_value_is_normalized_for_submission(self):
        form = HochEditAnalysisForm.__new__(HochEditAnalysisForm)
        form._analysis = DummyTimeInterimAnalysis()
        form.request = DummyRequest({
            "IncubationTime-time": "01:02:03",
            "IncubationTime": "",
        })
        form._synchronize_time_interims()
        self.assertEqual("01:02:03", form.request.form["IncubationTime"])


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(TestTimeModal)
