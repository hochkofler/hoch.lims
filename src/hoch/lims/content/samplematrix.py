# -*- coding: utf-8 -*-

from datetime import timedelta

from AccessControl import ClassSecurityInfo
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from Products.CMFCore import permissions
from senaite.core.interfaces import ISampleMatrix
from zope.component import adapter
from zope.interface import implementer
from zope.interface import provider
from zope import schema

from hoch.lims import messageFactory as _


@provider(IFormFieldProvider)
class ISampleMatrixSchemaExtender(model.Schema):
    """Extended schema fields
    """
    #directives.order_after(code="title")
    code = schema.TextLine(
        title=_(
            u"cod_sample_matrix",
            default=u"Code",
        ),
        required=True,
    )


@implementer(ISampleMatrixSchemaExtender)
@adapter(ISampleMatrix)
class SampleMatrixSchemaExtender(object):
    """Extends sample types with additional fields
    """
    security = ClassSecurityInfo()

    def __init__(self, context):
        self.context = context

    @security.protected(permissions.View)
    def get_code(self):
        accessor = self.context.accessor("code")
        raw_value = accessor(self.context)
        return raw_value

    @security.protected(permissions.ModifyPortalContent)
    def set_code(self, value):
        mutator = self.context.mutator("code")
        mutator(self.context, value)

    code = property(get_code, set_code)
