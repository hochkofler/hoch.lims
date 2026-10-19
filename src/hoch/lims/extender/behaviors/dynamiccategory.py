# -*- coding: utf-8 -*-

from Acquisition import aq_base
from hoch.lims import messageFactory as _
from hoch.lims.dynamiccalculation import EXCLUDE_ATTR
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from senaite.core.interfaces import IAnalysisCategory
from zope import schema
from zope.component import adapter
from zope.interface import implementer
from zope.interface import provider


@provider(IFormFieldProvider)
class IDynamicCategoryBehavior(model.Schema):
    """Conditions under which the analyses of the category are not done
    """

    model.fieldset(
        "dynamic",
        label=_(u"Dynamic"),
        fields=[EXCLUDE_ATTR],
    )

    dynamic_exclude_when = schema.Text(
        title=_(u"label_dynamic_exclude_when",
                default=u"Do not perform when"),
        description=_(
            u"description_dynamic_exclude_when",
            default=u"Analyses of this category are not added to samples "
                    u"that match one of these lines, e.g. 'Processes = "
                    u"Preparado matriz*'. Each line holds 'field = pattern' "
                    u"criteria separated by ';' that must all match, with "
                    u"the same syntax as the Dynamic rules of Calculations. "
                    u"Rules are evaluated when analyses are saved and when "
                    u"the sample is edited. Analyses with results are never "
                    u"removed. Leave empty to always perform them."),
        required=False,
        missing_value=u"",
        default=u"",
    )


@implementer(IDynamicCategoryBehavior)
@adapter(IAnalysisCategory)
class DynamicCategory(object):

    def __init__(self, context):
        self.context = context

    def _get_exclude_when(self):
        return getattr(aq_base(self.context), EXCLUDE_ATTR, None) or u""

    def _set_exclude_when(self, value):
        setattr(self.context, EXCLUDE_ATTR, value or u"")

    dynamic_exclude_when = property(_get_exclude_when, _set_exclude_when)
