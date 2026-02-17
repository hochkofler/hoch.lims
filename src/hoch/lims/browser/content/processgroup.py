# -*- coding: utf-8 -*-
import collections
from bika.lims import api
from bika.lims.utils import get_link
from senaite.app.listing.view import ListingView
from hoch.lims import messageFactory as _
from hoch.lims.catalog import HOCHLIMS_CATALOG
from bika.lims.utils import safe_unicode

class ProcessGroupView(ListingView):
    """View for a single Process Group (lists child Processes)
    """

    def __init__(self, context, request):
        super(ProcessGroupView, self).__init__(context, request)

        self.catalog = HOCHLIMS_CATALOG

        self.contentFilter = {
            "portal_type": "Process",
            "sort_on": "getObjPositionInParent",
            "sort_order": "ascending",
        }

        self.context_actions = {
            _("Add"): {
                "url": "++add++Process",
                "permission": "cmf.AddPortalContent",
                "icon": "++resource++bika.lims.images/add.png"}
            }

        self.icon = "{}/{}".format(
            self.portal_url, "senaite_theme/icon/setup")

        self.title = safe_unicode(self.context.Title())
        self.description = self.context.Description()
        self.show_select_column = True
        self.pagesize = 25

        self.columns = collections.OrderedDict((
            ("Title", {
                "title": _(u"label_process_title",
                            default=u"Title"),
                "index": "sortable_title",
                "toggle": True}),
            ("Description", {
                "title": _(u"label_process_description",
                            default=u"Description"),
                "index": "description",
                "toggle": True}),
        ))

        self.review_states = [
            {
                "id": "default",
                "title": _("Active"),
                "contentFilter": {"is_active": True},
                "columns": self.columns.keys(),
            }, {
                "id": "inactive",
                "title": _("Inactive"),
                "contentFilter": {'is_active': False},
                "columns": self.columns.keys(),
            }, 
            {
                "id": "all",
                "title": _("All"),
                "contentFilter": {},
                "columns": self.columns.keys(),
            },
        ]

    def folderitem(self, obj, item, index):
        obj = api.get_object(obj)
        url = api.get_url(obj)
        item["Title"] = safe_unicode(obj.Title())
        item["replace"]["Title"] = get_link(url, value=item["Title"])
        item["Description"] = safe_unicode(obj.Description())
        return item
