# -*- coding: utf-8 -*-
"""Runs the HPLC calculation model (hoch.lims.hplcmodel) for an analysis.

The model of the Calculation is copied into the analysis when the analysis
is linked to the calculation, so later edits of the Calculation never change
analyses that already exist, as for the calculation formula.

Variables are collected from these sources, the later ones win:

1. Product: HPLC parameters of the sample matrix of the product (rows
   without service, then rows of the service whose injections are used,
   then rows of the service of the analysis)
2. Assay of the same sample: interims of the analysis that receives the
   injections (e.g. content uniformity uses the standard weights and the
   water entered in the assay). Also available as ``valoracion.<name>``
3. Run data: interims of the analysis itself
4. Other analyses of the sample: ``<KEYWORD>`` is the result of that
   analysis and ``<KEYWORD>.<interim>`` one of its interims

Variables X_1, X_2... define X as their mean when X is not set, so the
number of standard weighings is free.

The last calculation (values used, their origin and every stage) is kept in
the analysis, so the result can be reviewed step by step.
"""

import copy
import re
from datetime import datetime

from Acquisition import aq_base
from bika.lims import api
from bika.lims import logger
from bika.lims.interfaces import ISubmitted
from hoch.lims import hplcmodel as hm
from hoch.lims import injections as inj

MODEL_ATTR = "_hplc_model"
TRACE_ATTR = "_hplc_trace"

# Function used by the calculation formula
FORMULA = "calc_hplc_model(context=%(context_uid)s)"

# Origins of the variables, as shown to the user
PRODUCT = u"product"
ASSAY = u"assay"
RUN = u"run"
ANALYSIS = u"analysis"
DERIVED = u"derived"
INJECTIONS = u"injections"

# Prefix to read the variables of the assay of the same sample
ASSAY_PREFIX = u"valoracion"

# UIDs of the analyses being calculated, to avoid re-entrant recalculation
_CALCULATING = set()


def get_calculation_model(calculation):
    """Returns the HPLC model of the calculation as a dict, or None
    """
    if calculation is None:
        return None
    obj = aq_base(calculation)
    standard = getattr(obj, "hplc_standard", None)
    if not standard:
        return None
    derived = {}
    for line in (getattr(obj, "hplc_derived", None) or u"").splitlines():
        if "=" not in line:
            continue
        name, expression = line.split("=", 1)
        if name.strip() and expression.strip():
            derived[name.strip()] = expression.strip()
    return {
        "standard": standard,
        "amount": getattr(obj, "hplc_amount", None) or u"",
        "result": getattr(obj, "hplc_result", None) or u"",
        "injections_per_unit": getattr(obj, "hplc_injections_per_unit",
                                       None) or 1,
        "aggregate": getattr(obj, "hplc_aggregate", None) or hm.MEAN,
        "T": getattr(obj, "hplc_T", None) or 100.0,
        "k": getattr(obj, "hplc_k", None) or 2.4,
        "Q": getattr(obj, "hplc_Q", None) or 75.0,
        "derived": derived,
        "calculation": api.get_title(calculation),
        "version": api.get_version(calculation) or 0,
    }


def snapshot_model(analysis, calculation):
    """Copies the HPLC model of the calculation into the analysis
    """
    setattr(analysis, MODEL_ATTR, get_calculation_model(calculation))


def get_model(analysis):
    """Returns the HPLC model of the analysis, or None
    """
    model = getattr(aq_base(analysis), MODEL_ATTR, None)
    if model is None and not hasattr(aq_base(analysis), MODEL_ATTR):
        # analysis linked before the model existed
        model = get_calculation_model(analysis.getCalculation())
        setattr(analysis, MODEL_ATTR, model)
    return copy.deepcopy(model) if model else None


def get_trace(analysis):
    return getattr(aq_base(analysis), TRACE_ATTR, None)


def interim_values(analysis):
    values = {}
    for interim in analysis.getInterimFields() or []:
        value = inj.to_float(interim.get("value"))
        if interim.get("keyword") and value is not None:
            values[interim["keyword"]] = value
    return values


def same(obj, other):
    """Returns whether both are the same object, whatever their wrapper
    """
    if obj is None or other is None:
        return False
    return api.get_uid(obj) == api.get_uid(other)


def get_root_sample(sample):
    parent = sample.getParentAnalysisRequest()
    while parent:
        sample = parent
        parent = sample.getParentAnalysisRequest()
    return sample


def product_parameters(analysis, source):
    """Returns the HPLC parameters of the product for the analysis

    :returns: dict name -> (value, origin detail)
    """
    sample = get_root_sample(analysis.getRequest())
    sampletype = sample.getSampleType()
    matrix = sampletype and sampletype.getSampleMatrix() or None
    rows = getattr(aq_base(matrix), "hplc_parameters", None) or [] \
        if matrix else []
    services = [None]
    if source is not None:
        services.append(source.getServiceUID())
    services.append(analysis.getServiceUID())
    found = {}
    for service in services:
        for row in rows:
            uid = row.get("service")
            if isinstance(uid, (list, tuple)):
                uid = uid and uid[0] or None
            if (uid or None) != service:
                continue
            value = inj.to_float(row.get("value"))
            name = (row.get("name") or u"").strip()
            if name and value is not None:
                found[name] = (value, api.get_title(matrix))
    return found


def collect_variables(analysis, source):
    """Returns the variables for the model and the origin of each one

    :returns: (values, origins) dicts
    """
    values, origins = {}, {}

    def put(name, value, origin):
        values[name] = value
        origins[name] = origin

    for name, (value, detail) in product_parameters(analysis, source).items():
        put(name, value, PRODUCT)

    if source is not None and not same(source, analysis):
        for name, value in interim_values(source).items():
            put(name, value, ASSAY)
    if source is not None:
        for name, value in interim_values(source).items():
            values[u"{}.{}".format(ASSAY_PREFIX, name)] = value
            origins[u"{}.{}".format(ASSAY_PREFIX, name)] = ASSAY

    for name, value in interim_values(analysis).items():
        put(name, value, RUN)

    sample = analysis.getRequest()
    for other in sample.getAnalyses(full_objects=True):
        if same(other, analysis):
            continue
        keyword = other.getKeyword()
        result = inj.to_float(other.getResult())
        if result is not None:
            values.setdefault(keyword, result)
            origins.setdefault(keyword, ANALYSIS)
        for name, value in interim_values(other).items():
            key = u"{}.{}".format(keyword, name)
            values[key] = value
            origins[key] = ANALYSIS

    # X_1, X_2... -> X (mean), when X is not set
    groups = {}
    for name, value in values.items():
        match = re.match(r"^(.+)_(\d+)$", name)
        if match and "." not in name:
            groups.setdefault(match.group(1), []).append(value)
    for base, items in groups.items():
        if base not in values:
            put(base, sum(items) / float(len(items)), DERIVED)
    return values, origins


def get_rows(source):
    rows = []
    for row in inj.get_injections(source):
        rows.append({
            "type": row.get("type"),
            "number": row.get("number"),
            "area": row.get("area"),
            "weight": row.get("weight"),
        })
    return rows


def to_plain(value):
    """Returns a copy of the value with plain python types only
    """
    if isinstance(value, dict):
        return dict((k, to_plain(v)) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return [to_plain(v) for v in value]
    return value


def calculate(analysis):
    """Calculates the analysis with its HPLC model

    :returns: the result, or "" when it can not be calculated yet
    """
    model = get_model(analysis)
    if not model:
        return ""
    source = inj.get_source_analysis(analysis)
    trace = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": model,
        "source": source and source.getKeyword() or None,
    }
    try:
        if source is None:
            raise hm.ModelError("No analysis of this sample receives the "
                                "HPLC injections")
        values, origins = collect_variables(analysis, source)
        output = hm.calculate(model, values, get_rows(source))
        used = dict((name, [value, origins.get(name, DERIVED)])
                    for name, value in output["variables"].items())
        for name, value in output["derived"].items():
            used[name] = [value, DERIVED]
        trace.update({"output": output, "variables": used, "error": None})
        result = output["result"]
    except hm.ModelError as exc:
        trace.update({"output": None, "variables": {},
                      "error": api.safe_unicode(str(exc)),
                      "missing": getattr(exc, "names", None)})
        logger.info("HPLC model: {} of {} not calculated: {}".format(
            analysis.getKeyword(), api.get_id(analysis.getRequest()), exc))
        result = ""
    setattr(analysis, TRACE_ATTR, to_plain(trace))

    # analyses reading these injections (e.g. content uniformity)
    if same(source, analysis):
        recalculate_readers(analysis)
    return result


def recalculate_readers(source):
    """Recalculates the analyses of the sample that read the source
    """
    sample = source.getRequest()
    for analysis in sample.objectValues("Analysis"):
        if same(analysis, source) or ISubmitted.providedBy(analysis):
            continue
        if api.get_uid(analysis) in _CALCULATING:
            continue
        if "calc_hplc_model" not in (analysis.getCalculationFormula() or ""):
            continue
        if not same(inj.get_source_analysis(analysis), source):
            continue
        _CALCULATING.add(api.get_uid(analysis))
        try:
            analysis.calculateResult(override=True, cascade=False)
            analysis.reindexObject()
        finally:
            _CALCULATING.discard(api.get_uid(analysis))
