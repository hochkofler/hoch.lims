# -*- coding: utf-8 -*-
from bika.lims.interfaces import IDoNotSupportSnapshots
from plone.supermodel import model
from senaite.core.content.base import Container
from senaite.core.interfaces import IHideActionsMenu
from zope.interface import implementer
from hoch.lims.interfaces import IOOSFolder


class IOOSFolderSchema(model.Schema):
    """OOS Investigations Folder Schema"""
    pass


@implementer(IOOSFolder, IDoNotSupportSnapshots, IHideActionsMenu)
class OOSFolder(Container):
    """OOS Investigations folder"""
    pass
