# -*- coding: utf-8 -*-
"""
Monkey patches for WorksheetsView:
- is_privileged_user: adds LabClerk role so they can see all worksheets
- __init__: registers the getSampleIDs column
- folderitem: populates getSampleIDs with linked sample IDs
"""

import collections

from bika.lims import api
from bika.lims import senaiteMessageFactory as _
from bika.lims.utils import get_link
from senaite.core.browser.worksheets.view import WorksheetsView


# ---------------------------------------------------------------------------
# is_privileged_user
# ---------------------------------------------------------------------------

_original_is_privileged_user = WorksheetsView.is_privileged_user


def is_privileged_user(self):
    """Returns whether the current user is a privileged member.

    Adds LabClerk to the list of privileged roles so they can see all
    worksheets, not just their own.
    """
    privileged = ["Manager", "LabManager", "LabClerk", "RegulatoryInspector"]
    user_roles = self.member.getRoles()
    if set(privileged).intersection(user_roles):
        return True
    return False


WorksheetsView.is_privileged_user = is_privileged_user


# ---------------------------------------------------------------------------
# __init__: inject getSampleIDs column after getNumberOfRegularSamples
# ---------------------------------------------------------------------------

_original_init = WorksheetsView.__init__


def patched_init(self, context, request):
    _original_init(self, context, request)

    new_columns = collections.OrderedDict()
    for key, value in self.columns.items():
        new_columns[key] = value
        if key == "getNumberOfRegularSamples":
            new_columns["getSampleIDs"] = {
                "title": _(
                    u"listing_worksheets_column_sample_ids",
                    default=u"Sample IDs",
                ),
            }
    self.columns = new_columns

    for rs in self.review_states:
        cols = list(rs.get("columns", []))
        if "getSampleIDs" not in cols and "getNumberOfRegularSamples" in cols:
            idx = cols.index("getNumberOfRegularSamples")
            cols.insert(idx + 1, "getSampleIDs")
            rs["columns"] = cols


WorksheetsView.__init__ = patched_init


# ---------------------------------------------------------------------------
# folderitem: populate getSampleIDs
# ---------------------------------------------------------------------------

_original_folderitem = WorksheetsView.folderitem


def patched_folderitem(self, obj, item, index):
    item = _original_folderitem(self, obj, item, index)

    samples = _get_unique_samples(api.get_object(obj))
    item["getSampleIDs"] = u", ".join([api.get_id(s) for s in samples])
    item["replace"]["getSampleIDs"] = u" ".join(
        [get_link(api.get_url(s), value=api.get_id(s)) for s in samples]
    )

    return item


def _get_unique_samples(worksheet):
    """Returns unique AnalysisRequest objects from the worksheet's regular analyses."""
    seen = set()
    samples = []
    for analysis in worksheet.getRegularAnalyses():
        uid = api.safe_getattr(analysis, "getRequestUID", None)
        if callable(uid):
            uid = uid()
        if not uid or uid in seen:
            continue
        seen.add(uid)
        sample = api.get_object_by_uid(uid, default=None)
        if sample:
            samples.append(sample)
    return samples


WorksheetsView.folderitem = patched_folderitem
