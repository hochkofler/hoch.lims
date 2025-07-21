import collections
from bika.lims import api
from bika.lims.utils import get_link_for
from senaite.app.listing import ListingView
from senaite.core.catalog import SETUP_CATALOG
from hoch.lims import messageFactory as _
from bika.lims import senaiteMessageFactory as _s
from senaite.core import PloneMessageFactory as _p

class ProductsListingView(ListingView):
    """Products listing view
    """

    def __init__(self, context, request):
        super(ProductsListingView, self).__init__(context, request)

        self.catalog = SETUP_CATALOG

        self.contentFilter = {
            "portal_type": "Product",
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }

        self.context_actions = {
            _s("Add"): {
                "url": "++add++Product",
                "icon": "add.png"}
            }

        self.show_select_column = True

        self.columns = collections.OrderedDict((
            ("Title", {
                "title": _("column_products_code", default="Code"),
                "index": "sortable_title"
            }),
            ("Description", {
                "title": _("column_products_name", default="Item Name"),
                "index": "Description"
            }),
            ("SampleMatrix", {
                "title": _("Minimum Unit"),
                "index": "samplematrix",
                "sortable": True,
            }),
        ))

        self.review_states = [
            {
                "id": "default",
                "title": _s("Active"),
                "contentFilter": {"is_active": True},
                "transitions": [],
                "columns": self.columns.keys(),
            }, {
                "id": "inactive",
                "title": _s("Inactive"),
                "contentFilter": {'is_active': False},
                "transitions": [],
                "columns": self.columns.keys(),
            }, {
                "id": "all",
                "title": _s("All"),
                "contentFilter": {},
                "columns": self.columns.keys(),
            },
        ]

    def update(self):
        """Update hook
        """
        super(ProductsListingView, self).update()

    def before_render(self):
        """Before template render hook
        """
        super(ProductsListingView, self).before_render()

    def folderitem(self, obj, item, index):
        """Service triggered each time an item is iterated in folderitems.
        The use of this service prevents the extra-loops in child objects.
        :obj: the instance of the class to be foldered
        :item: dict containing the properties of the object to be used by
            the template
        :index: current index of the item
        """
        obj = api.get_object(obj)
        item["Title"] = obj.Title()
        item["replace"]["Title"] = get_link_for(obj)
        item["Description"] = obj.Description()
        item["SampleMatrix"] = obj.samplematrix
        return item

    def get_children_hook(self, parent_uid, child_uids=None):
        """Hook to get the children of an item
        """
        super(ProductsListingView, self).get_children_hook(
            parent_uid, child_uids=child_uids)
