# -*- coding: utf-8 -*-

from Acquisition import aq_base
from hoch.lims import messageFactory as _
from hoch.lims.dynamiccalculation import RULES_ATTR
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from senaite.core.interfaces import ICalculation
from senaite.core.schema.fields import DataGridField
from senaite.core.schema.fields import DataGridRow
from senaite.core.z3cform.widgets.datagrid import DataGridWidgetFactory
from zope import schema
from zope.component import adapter
from zope.interface import Interface
from zope.interface import implementer
from zope.interface import provider


class IDynamicCalculationRuleSchema(Interface):
    """A rule that makes analyses use the Calculation
    """

    keyword = schema.TextLine(
        title=_(u"label_dynamic_calculation_keyword",
                default=u"Service keyword"),
        description=_(u"description_dynamic_calculation_keyword",
                      default=u"e.g. VAL_*. Empty matches any service"),
        required=False,
    )

    criteria = schema.TextLine(
        title=_(u"label_dynamic_calculation_criteria",
                default=u"Criteria"),
        description=_(u"description_dynamic_calculation_criteria",
                      default=u"e.g. Processes = Blisteado; "
                              u"Batch.Product.code = 101-*"),
        required=False,
    )


@provider(IFormFieldProvider)
class IDynamicCalculationRulesBehavior(model.Schema):
    """Rules that make analyses use this Calculation, and its dependencies,
    instead of the Calculation of their service
    """

    model.fieldset(
        "dynamic",
        label=_(u"Dynamic"),
        fields=[RULES_ATTR],
    )

    directives.widget(
        RULES_ATTR,
        DataGridWidgetFactory,
        auto_append=True)
    dynamic_calculation_rules = DataGridField(
        title=_(u"label_dynamic_calculation_rules",
                default=u"Apply dynamically when"),
        description=_(
            u"description_dynamic_calculation_rules",
            default=u"Analyses that match one of these rules use this "
                    u"calculation, and its dependencies, instead of the "
                    u"calculation of their service. Criteria are "
                    u"'field = pattern' pairs separated by ';'. A field is "
                    u"a path of fields of the primary sample (or its batch), "
                    u"e.g. 'Processes', 'SampleType' or 'Batch.Product.code'. "
                    u"Prefix it with 'Sample.', 'Analysis.' or 'Batch.' to "
                    u"read another object, or use 'Condition.<title>' for an "
                    u"analysis condition. Patterns are case-insensitive and "
                    u"accept * and ? wildcards. When several rules match, "
                    u"the most specific one wins. Rules are evaluated when "
                    u"analyses are saved, when the sample is edited and when "
                    u"analysis conditions are set, as long as neither the "
                    u"analysis nor its dependencies have results."),
        value_type=DataGridRow(
            title=u"Rule",
            schema=IDynamicCalculationRuleSchema),
        required=False,
        missing_value=[],
        default=[],
    )


@implementer(IDynamicCalculationRulesBehavior)
@adapter(ICalculation)
class DynamicCalculationRules(object):

    def __init__(self, context):
        self.context = context

    def _get_rules(self):
        return getattr(aq_base(self.context), RULES_ATTR, None) or []

    def _set_rules(self, value):
        setattr(self.context, RULES_ATTR, value or [])

    dynamic_calculation_rules = property(_get_rules, _set_rules)
