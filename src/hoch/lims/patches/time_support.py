# -*- coding: utf-8 -*-

"""Compatibility hooks for time-valued results on SENAITE Core 2.x."""

from bika.lims import _
from bika.lims.browser.fields.interimfieldsfield import InterimFieldsField
from bika.lims.content import abstractbaseanalysis
from hoch.lims.utils import format_time_value
from Products.Archetypes.public import DisplayList
from senaite.core.config import vocabularies as config_vocabularies
from senaite.core.schema.vocabulary import to_simple_vocabulary
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory


TIME_RESULT_TYPE = ("time", _("Time"))


def append_time(items):
    """Return result type items with one time entry."""
    if "time" in [item[0] for item in items]:
        return tuple(items)
    return tuple(items) + (TIME_RESULT_TYPE,)


def enable_time_result_type():
    """Expose time through SENAITE's legacy result-type fields."""
    abstractbaseanalysis.RESULT_TYPES = append_time(
        abstractbaseanalysis.RESULT_TYPES)
    abstractbaseanalysis.ResultType.vocabulary = DisplayList(
        abstractbaseanalysis.RESULT_TYPES)

    vocabulary = InterimFieldsField._properties[
        "subfield_vocabularies"]["result_type"]
    if "time" not in list(vocabulary):
        vocabulary.add("time", _("Time"))

    config_vocabularies.RESULT_TYPES = append_time(
        config_vocabularies.RESULT_TYPES)


def format_analysis_result(self, *args, **kwargs):
    """Format time results and delegate all other types to SENAITE."""
    if self.getResultType() == "time":
        return format_time_value(self.getResult())
    return self._old_getFormattedResult(*args, **kwargs)


def format_listing_interim(self, interim):
    """Format time interims and delegate all other types to SENAITE."""
    if interim.get("result_type") == "time":
        return format_time_value(interim.get("value"))
    return self._old_get_formatted_interim(interim)


@implementer(IVocabularyFactory)
class TimeResultTypesVocabulary(object):
    """Modern result-type vocabulary extended with time."""

    def __call__(self, context):
        return to_simple_vocabulary(
            append_time(config_vocabularies.RESULT_TYPES))


enable_time_result_type()
