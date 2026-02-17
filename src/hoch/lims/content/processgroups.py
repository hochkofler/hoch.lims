# -*- coding: utf-8 -*-

from bika.lims.interfaces import IDoNotSupportSnapshots
from plone.supermodel import model
from senaite.core.content.base import Container
from senaite.core.interfaces import IHideActionsMenu
from zope.interface import implementer
from hoch.lims.interfaces import IProcessGroups

class IProcessGroupsSchema(model.Schema):
    """Folder Interface for Process Groups"""
    pass

@implementer(IProcessGroups, IDoNotSupportSnapshots, IHideActionsMenu)
class ProcessGroups(Container):
    """Process Groups Folder"""
    pass
