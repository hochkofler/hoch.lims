# -*- coding: utf-8 -*-
import collections
from bika.lims import api
from bika.lims.utils import get_link
from senaite.app.listing.view import ListingView
from hoch.lims import messageFactory as _
from hoch.lims.catalog import HOCHLIMS_CATALOG
from hoch.lims.permissions import AddOOSInvestigation


class OOSInvestigationsView(ListingView):
    """Listing view for OOS Investigations folder"""

    def __init__(self, context, request):
        super(OOSInvestigationsView, self).__init__(context, request)

        self.catalog = HOCHLIMS_CATALOG

        self.contentFilter = {
            "portal_type": "OOSInvestigation",
            "sort_on": "oos_detection_date",
            "sort_order": "descending",
        }

        self.context_actions = {
            _("Add"): {
                "url": "++add++OOSInvestigation",
                "permission": AddOOSInvestigation,
                "icon": "++resource++bika.lims.images/add.png",
            }
        }

        self.icon = "{}/{}".format(
            self.portal_url, "senaite_theme/icon/analysisrequest")

        self.title = self.context.translate(_("OOS Investigations"))
        self.description = self.context.Description()
        self.show_select_column = True
        self.pagesize = 25

        self.columns = collections.OrderedDict((
            ("OOS_Number", {
                "title": _(
                    u"label_oos_number",
                    default=u"OOS Number",
                ),
                "index": "sortable_title",
                "toggle": True,
            }),
            ("Detection_date", {
                "title": _(
                    u"label_oos_detection_date",
                    default=u"Detection Date",
                ),
                "index": "oos_detection_date",
                "toggle": True,
            }),
            ("Analysis_service", {
                "title": _(
                    u"label_oos_analysis_service",
                    default=u"Analysis",
                ),
                "toggle": True,
            }),
            ("Result_value", {
                "title": _(
                    u"label_oos_result_value",
                    default=u"Result",
                ),
                "toggle": True,
            }),
            ("Specification_range", {
                "title": _(
                    u"label_oos_specification_range",
                    default=u"Specification",
                ),
                "toggle": True,
            }),
            ("OOS_Category", {
                "title": _(
                    u"label_oos_category",
                    default=u"Category",
                ),
                "index": "oos_category",
                "toggle": True,
            }),
            ("Sample", {
                "title": _(
                    u"label_oos_sample",
                    default=u"Sample",
                ),
                "toggle": True,
            }),
            ("Batch", {
                "title": _(
                    u"label_oos_batch",
                    default=u"Batch",
                ),
                "toggle": True,
            }),
            ("Disposition", {
                "title": _(
                    u"label_oos_disposition",
                    default=u"Disposition",
                ),
                "index": "oos_disposition",
                "toggle": False,
            }),
            ("Phase", {
                "title": _(
                    u"label_oos_phase",
                    default=u"Phase",
                ),
                "index": "oos_investigation_phase",
                "toggle": True,
            }),
            ("Due_date", {
                "title": _(
                    u"label_oos_due_date",
                    default=u"Due Date",
                ),
                "index": "oos_due_date",
                "toggle": False,
            }),
            ("Investigator", {
                "title": _(
                    u"label_oos_investigator",
                    default=u"Investigator",
                ),
                "toggle": False,
            }),
        ))

        self.review_states = [
            {
                "id": "default",
                "title": _("All Open"),
                "contentFilter": {
                    "review_state": [
                        "recorded", "phase1", "phase2", "review",
                    ],
                },
                "columns": self.columns.keys(),
            },
            {
                "id": "recorded",
                "title": _("Recorded"),
                "contentFilter": {"review_state": "recorded"},
                "columns": self.columns.keys(),
            },
            {
                "id": "phase1",
                "title": _("Phase I"),
                "contentFilter": {"review_state": "phase1"},
                "columns": self.columns.keys(),
            },
            {
                "id": "phase2",
                "title": _("Phase II"),
                "contentFilter": {"review_state": "phase2"},
                "columns": self.columns.keys(),
            },
            {
                "id": "review",
                "title": _("Under Review"),
                "contentFilter": {"review_state": "review"},
                "columns": self.columns.keys(),
            },
            {
                "id": "closed",
                "title": _("Closed"),
                "contentFilter": {"review_state": "closed"},
                "columns": self.columns.keys(),
            },
            {
                "id": "cancelled",
                "title": _("Cancelled"),
                "contentFilter": {"review_state": "cancelled"},
                "columns": self.columns.keys(),
            },
            {
                "id": "all",
                "title": _("All"),
                "contentFilter": {},
                "columns": self.columns.keys(),
            },
        ]

    def update(self):
        super(OOSInvestigationsView, self).update()

    def before_render(self):
        super(OOSInvestigationsView, self).before_render()

    def folderitem(self, obj, item, index):
        obj = api.get_object(obj)
        url = api.get_url(obj)

        # OOS Number with link
        oos_id = api.get_id(obj)
        item["OOS_Number"] = oos_id
        item["replace"]["OOS_Number"] = get_link(url, value=oos_id)

        # Snapshots
        item["Analysis_service"] = obj.getAnalysisServiceTitle() or ""
        item["Result_value"] = obj.getResultValue() or ""
        item["Specification_range"] = obj.getSpecificationRange() or ""

        # Detection date
        detection_date = obj.getDetectionDate()
        if detection_date:
            from senaite.core.api import dtime
            item["Detection_date"] = dtime.to_localized_time(
                dtime.to_DT(detection_date))
        else:
            item["Detection_date"] = ""

        # Due date
        due_date = obj.getDueDate()
        if due_date:
            from senaite.core.api import dtime
            item["Due_date"] = dtime.to_localized_time(
                dtime.to_DT(due_date))
        else:
            item["Due_date"] = ""

        # Category, disposition, phase
        item["OOS_Category"] = obj.getOosCategory() or ""
        item["Disposition"] = obj.getDisposition() or ""
        item["Phase"] = obj.getInvestigationPhase() or ""
        item["Investigator"] = obj.getInvestigator() or ""

        # Derived: Sample
        sample = obj.getSample()
        if sample:
            sample_url = api.get_url(sample)
            sample_id = api.get_id(sample)
            item["Sample"] = sample_id
            item["replace"]["Sample"] = get_link(
                sample_url, value=sample_id)
        else:
            item["Sample"] = ""

        # Derived: Batch
        batch = obj.getBatch()
        if batch:
            batch_url = api.get_url(batch)
            batch_id = api.get_id(batch)
            item["Batch"] = batch_id
            item["replace"]["Batch"] = get_link(batch_url, value=batch_id)
        else:
            item["Batch"] = ""

        return item
