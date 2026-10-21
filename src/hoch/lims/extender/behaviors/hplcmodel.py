# -*- coding: utf-8 -*-
"""HPLC calculation model of a Calculation, and HPLC parameters of a product.

See hoch.lims.hplcmodel for the stages and the expression syntax.
"""

from Acquisition import aq_base
from hoch.lims import messageFactory as _
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from senaite.core.config.widgets import get_default_columns
from senaite.core.interfaces import ICalculation
from senaite.core.interfaces import ISampleMatrix
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.schema import UIDReferenceField
from senaite.core.schema.fields import DataGridField
from senaite.core.schema.fields import DataGridRow
from senaite.core.z3cform.widgets.datagrid import DataGridWidgetFactory
from senaite.core.z3cform.widgets.uidreference import \
    UIDReferenceWidgetFactory
from zope import schema
from zope.component import adapter
from zope.interface import Interface
from zope.interface import implementer
from zope.interface import provider
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

AGGREGATES = SimpleVocabulary([
    SimpleTerm(value="mean", title=_(u"Mean (assay)")),
    SimpleTerm(value="uniformity",
               title=_(u"Content uniformity (acceptance value)")),
    SimpleTerm(value="dissolution", title=_(u"Dissolution (per vessel, S1)")),
])

# Attributes on the Calculation, in the order of the model stages
MODEL_FIELDS = (
    "hplc_standard", "hplc_amount", "hplc_result", "hplc_injections_per_unit",
    "hplc_standard_injections_per_prep", "hplc_aggregate", "hplc_T",
    "hplc_k", "hplc_Q", "hplc_derived",
)


@provider(IFormFieldProvider)
class IHPLCModelBehavior(model.Schema):
    """External standard HPLC model of the calculation
    """

    model.fieldset(
        "hplc",
        label=_(u"HPLC model"),
        fields=list(MODEL_FIELDS),
    )

    hplc_standard = schema.TextLine(
        title=_(u"label_hplc_standard",
                default=u"1. Standard concentration"),
        description=_(
            u"description_hplc_standard",
            default=u"e.g. W_st * (1 - agua_st/100) * P_st/100 / "
                    u"(V_st * D_st) * 1000. Leave empty if this calculation "
                    u"does not use the HPLC model."),
        required=False,
    )

    hplc_amount = schema.TextLine(
        title=_(u"label_hplc_amount", default=u"3. Amount per unit"),
        description=_(
            u"description_hplc_amount",
            default=u"e.g. C_u * V_mue * D_mue / 1000. C_u is the mean "
                    u"concentration of the injections of the unit, W_mue "
                    u"the weight of the unit"),
        required=False,
    )

    hplc_result = schema.TextLine(
        title=_(u"label_hplc_result", default=u"4. Result per unit"),
        description=_(
            u"description_hplc_result",
            default=u"e.g. cantidad / LC * 100 * F_PM"),
        required=False,
    )

    hplc_injections_per_unit = schema.Int(
        title=_(u"label_hplc_injections_per_unit",
                default=u"Injections per unit"),
        default=2,
        min=1,
        required=False,
    )

    hplc_standard_injections_per_prep = schema.Int(
        title=_(u"label_hplc_standard_injections_per_prep",
                default=u"Standard injections per preparation"),
        description=_(
            u"description_hplc_standard_injections_per_prep",
            default=u"Each preparation uses its own weight (W_st_1, W_st_2"
                    u"...). Leave empty for a single concentration for all "
                    u"the standard injections. The product parameter n_iny_st"
                    u" overrides it, as n_iny_mue does for the injections "
                    u"per unit and Q for dissolution."),
        min=0,
        required=False,
    )

    hplc_aggregate = schema.Choice(
        title=_(u"label_hplc_aggregate", default=u"5. Aggregate"),
        vocabulary=AGGREGATES,
        default="mean",
        required=False,
    )

    hplc_T = schema.Float(
        title=_(u"label_hplc_T", default=u"Uniformity: T"),
        default=100.0,
        required=False,
    )

    hplc_k = schema.Float(
        title=_(u"label_hplc_k", default=u"Uniformity: k"),
        default=2.4,
        required=False,
    )

    hplc_Q = schema.Float(
        title=_(u"label_hplc_Q", default=u"Dissolution: Q (%)"),
        default=75.0,
        required=False,
    )

    hplc_derived = schema.Text(
        title=_(u"label_hplc_derived", default=u"Derived variables"),
        description=_(
            u"description_hplc_derived",
            default=u"One per line, e.g. F_PM = n_PM * PM_decl / PM_st. "
                    u"Variables X_1, X_2... also define X as their mean."),
        required=False,
    )


@implementer(IHPLCModelBehavior)
@adapter(ICalculation)
class HPLCModel(object):

    def __init__(self, context):
        self.__dict__["context"] = context

    def __getattr__(self, name):
        if name not in MODEL_FIELDS:
            raise AttributeError(name)
        field = IHPLCModelBehavior[name]
        return getattr(aq_base(self.context), name, field.default)

    def __setattr__(self, name, value):
        if name not in MODEL_FIELDS:
            raise AttributeError(name)
        setattr(self.context, name, value)


class IHPLCParameterSchema(Interface):
    """A product parameter of the HPLC model
    """

    directives.widget(
        "service",
        UIDReferenceWidgetFactory,
        catalog=SETUP_CATALOG,
        query={
            "portal_type": "AnalysisService",
            "is_active": True,
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        },
        display_template="<a href='${url}'>${Title}</a>",
        columns=get_default_columns)
    service = UIDReferenceField(
        title=_(u"label_hplc_parameter_service", default=u"Service"),
        description=_(u"description_hplc_parameter_service",
                      default=u"Empty applies to all the services"),
        allowed_types=("AnalysisService", ),
        multi_valued=False,
        required=False)

    name = schema.TextLine(
        title=_(u"label_hplc_parameter_name", default=u"Variable"),
        required=True,
    )

    value = schema.Float(
        title=_(u"label_hplc_parameter_value", default=u"Value"),
        required=True,
    )

    unit = schema.TextLine(
        title=_(u"label_hplc_parameter_unit", default=u"Unit"),
        required=False,
    )


@provider(IFormFieldProvider)
class IHPLCParametersBehavior(model.Schema):
    """HPLC parameters of the product (volumes, dilutions, label claim...)
    """

    model.fieldset(
        "hplc",
        label=_(u"HPLC parameters"),
        fields=["hplc_parameters"],
    )

    directives.widget(
        "hplc_parameters",
        DataGridWidgetFactory,
        auto_append=True)
    hplc_parameters = DataGridField(
        title=_(u"label_hplc_parameters", default=u"HPLC parameters"),
        description=_(
            u"description_hplc_parameters",
            default=u"Values of the variables used by the HPLC model "
                    u"expressions for this product, e.g. V_st, D_st, LC, "
                    u"PM_st. A row with a service only applies to that "
                    u"service."),
        value_type=DataGridRow(
            title=u"Parameter",
            schema=IHPLCParameterSchema),
        required=False,
        missing_value=[],
        default=[],
    )


@implementer(IHPLCParametersBehavior)
@adapter(ISampleMatrix)
class HPLCParameters(object):

    def __init__(self, context):
        self.context = context

    def _get(self):
        return getattr(aq_base(self.context), "hplc_parameters", None) or []

    def _set(self, value):
        self.context.hplc_parameters = value or []

    hplc_parameters = property(_get, _set)
