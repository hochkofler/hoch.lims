# -*- coding: utf-8 -*-

from plone.supermodel import model
from senaite.core.content.base import Item
from hoch.lims.interfaces import IProcess
from zope.interface import implementer
from hoch.lims.catalog import HOCHLIMS_CATALOG

import zope.schema as schema
from hoch.lims import messageFactory as _

class IProcessSchema(model.Schema):
    """Process Schema"""

    result_product = schema.TextLine(
        title=_("label_process_result_product", default=u"Product Result"),
        description=_("description_process_result_product", default=u"The resulting product of this process (e.g., Blister, Capsule)."),
        required=False,
    )

    result_unit = schema.TextLine(
        title=_("label_process_result_unit", default=u"Result Unit"),
        description=_("description_process_result_unit", default=u"The unit of the resulting product."),
        required=False,
    )

@implementer(IProcess, IProcessSchema)
class Process(Item):
    """Process content type"""
    _catalogs = [HOCHLIMS_CATALOG]
