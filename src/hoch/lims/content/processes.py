# -*- coding: utf-8 -*-

from bika.lims.interfaces import IDoNotSupportSnapshots
from plone.supermodel import model
from senaite.core.content.base import Container
from senaite.core.interfaces import IHideActionsMenu
from zope.interface import implementer
from hoch.lims.interfaces import IProcesses

class IProcessesSchema(model.Schema):
    """Folder Interface for Processes"""
    pass

@implementer(IProcesses, IDoNotSupportSnapshots, IHideActionsMenu)
class Processes(Container):
    """Processes Folder"""
    pass
