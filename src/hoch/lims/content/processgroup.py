# -*- coding: utf-8 -*-

from plone.supermodel import model
import zope.schema as schema
from hoch.lims import messageFactory as _
from senaite.core.content.base import Container
from hoch.lims.interfaces import IProcessGroup
from zope.interface import implementer
from hoch.lims.catalog import HOCHLIMS_CATALOG
from AccessControl import ClassSecurityInfo
from Products.CMFCore import permissions
from plone.autoform import directives
from senaite.core.z3cform.widgets.uidreference import UIDReferenceWidgetFactory
from hoch.lims.content.fields import UIDReferenceFieldDx

class IProcessGroupSchema(model.Schema):
    """Process Group Schema"""

    directives.widget(
        "processes",
        UIDReferenceWidgetFactory,
        catalog=HOCHLIMS_CATALOG,
        query={
            "is_active": True,
            "sort_on": "title",
            "sort_order": "ascending",
        },
    )
    processes = UIDReferenceFieldDx(
        title=_(
            u"title_processgroup_processes",
            default=u"Processes"
        ),
        description=_(
            u"description_processgroup_processes",
            default=u"Select the processes that belong to this group. "
        ),
        relationship="ProcessGroupProcesses",
        allowed_types=("Process", ),
        multi_valued=True,
        required=True,
    )

@implementer(IProcessGroup, IProcessGroupSchema)
class ProcessGroup(Container):
    """Process Group content type"""
    _catalogs = [HOCHLIMS_CATALOG]
    security = ClassSecurityInfo()

    @security.protected(permissions.View)
    def getProcesses(self):
        """Return the titles of referenced Process objects"""
        accessor = self.accessor("processes")
        processes = accessor(self) or []
        return [obj.Title() for obj in processes]
