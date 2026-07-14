# -*- coding: utf-8 -*-
from bika.lims import api
from bika.lims.browser.batchfolder import BatchFolderContentsView as BaseView
from hoch.lims import messageFactory as _


class BatchFolderContentsView(BaseView):
    """Extends the core batch listing to show ExpirationDate and BatchSize.
    """

    def __init__(self, context, request):
        super(BatchFolderContentsView, self).__init__(context, request)

        self.columns["ExpirationDate"] = {
            "title": _(u"label_batch_expirationdate", default=u"Expire date"),
            "sortable": False,
            "toggle": True,
        }
        self.columns["BatchSize"] = {
            "title": _(u"label_batch_batchsize", default=u"Batch size"),
            "sortable": False,
            "toggle": True,
        }

        for review_state in self.review_states:
            cols = list(review_state["columns"])
            if "state_title" in cols:
                idx = cols.index("state_title")
                cols.insert(idx, "ExpirationDate")
                cols.insert(idx, "BatchSize")
            else:
                cols.extend(["BatchSize", "ExpirationDate"])
            review_state["columns"] = cols

    def folderitem(self, obj, item, index):
        item = super(BatchFolderContentsView, self).folderitem(obj, item, index)
        obj = api.get_object(obj)

        expiration = obj.getField("ExpirationDate")
        if expiration:
            val = expiration.get(obj)
            item["ExpirationDate"] = self.ulocalized_time(val) if val else ""
        else:
            item["ExpirationDate"] = ""

        batch_size = obj.getField("BatchSize")
        if batch_size:
            item["BatchSize"] = batch_size.get(obj) or ""
        else:
            item["BatchSize"] = ""

        return item
