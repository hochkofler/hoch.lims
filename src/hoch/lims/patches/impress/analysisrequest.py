# -*- coding: utf-8 -*-
from hoch.lims import messageFactory as _
from hoch.lims import check_installed, logger
from bika.lims.api import to_float, float_to_string
from bika.lims.api.analysis import is_out_of_range
from bika.lims.config import MAX_OPERATORS
from bika.lims.config import MIN_OPERATORS
from bika.lims.utils import formatDecimalMark
from bika.lims.utils.analysis import _format_decimal_or_sci
import json
import cgi
from collections import OrderedDict
from senaite.core.api import dtime
from senaite.core.i18n import get_dt_format
from senaite.core.i18n import translate as t
from senaite.impress.analysisrequest.reportview import ReportView as view
from senaite.impress.analysisrequest.model import SuperModel

@check_installed(None)
def get_formatted_specs2(self, analysis, with_shoulder_range=False):
    specs = analysis.getResultsRange()

    # Get possible choice options (for choice-type results)
    choices = analysis.getResultOptions()
    values_texts = {}
    if choices:
        # Map: ResultValue -> ResultText (both as strings for easier comparison)
        values_texts = dict(map(
            lambda c: (str(c["ResultValue"]), c["ResultText"]),
            choices
        ))

    result_type = analysis.getResultType()
    is_choice_type = result_type in [
        "select", "multiselect", "multiselect_duplicates", "multichoice"
    ]

    # Get min and max operators (default values if missing)
    min_operator = specs.get("min_operator") or ""
    min_operator = MIN_OPERATORS.getValue(min_operator, default=">=")
    max_operator = specs.get("max_operator") or ""
    max_operator = MAX_OPERATORS.getValue(max_operator, default="<=")

    # Helper function to evaluate the operator condition
    def matches_operator(value, limit, operator):
        value = float(value)
        limit = float(limit)
        if operator == ">=":
            return value >= limit
        elif operator == ">":
            return value > limit
        elif operator == "<=":
            return value <= limit
        elif operator == "<":
            return value < limit
        elif operator == "==":
            return value == limit
        elif operator == "!=":
            return value != limit
        return False

    specs_min = specs.get("min")
    specs_max = specs.get("max")
    # --- If it's a choice type, filter by range and return the matching texts ---
    if with_shoulder_range:
        specs_min = specs.get("warn_min")
        specs_max = specs.get("warn_max")
        
    if (is_choice_type or values_texts) and (specs_min or specs_max):
        filtered_texts = []
        for num, text in values_texts.items():
            if (not specs_min or matches_operator(num, specs_min, min_operator)) and \
               (not specs_max or matches_operator(num, specs_max, max_operator)):
                filtered_texts.append(text)

        # Optional: if all choices are included, return a single label
        if len(filtered_texts) == len(values_texts):
            return "All"

        return ", ".join(filtered_texts)

    # --- Default numeric range case ---
    fs = ""
    threshold = analysis.getExponentialFormatPrecision()
    precision = analysis.getPrecision()
    
    if specs_min:
        formated_min = _format_decimal_or_sci(specs_min, precision, threshold, 1)
    
    if specs_max:
        formated_max = _format_decimal_or_sci(specs_max, precision, threshold, 1)
    if specs_min and specs_max:
        fs = "%s - %s" % (formated_min, formated_max)
    elif specs_min:
        fs = "%s %s" % (min_operator, formated_min)
    elif specs_max:
        fs = "%s %s" % (max_operator, formated_max)

    return formatDecimalMark(fs, self.decimal_mark)

@check_installed(None)
def getFormattedResultForService(self, analyses, specs=None, decimalmark='.', sciformat=1, html=True, is_max_date=True):
    """
    Evaluates a set of analyses for the same analysis service and provides:
      - Formatted results
      - Final result interpretation
      - Out-of-range evaluation

    Rules:
    0. If analyses are not from the same service, return None.
    1. If the result type is string/text → concat unique results.
    2. If the result type has choices → concat results and interpretation=True 
       only if ALL results belong to the valid specification options.
    3. If the result type is date → return max or min date (based on is_max_date).
    4. If the result type is numeric (floatable):
         - All or mean < LDL → "<LDL"
         - All or mean > UDL → ">UDL"
         - Otherwise → formatted mean numeric value.
    5. Out-of-range interpretation is False if ANY result is out of shoulder.

    Returns:
        dict with keys:
            results,interpretations, result_types, formatted_results,
            result, interpretation
    """

    result_dict = {}

    # Collect raw results, result types and pre-formatted values
    results = [a.getResult() for a in analyses]
    result_types = [a.getResultType() for a in analyses]
    out_of_range_flags = [is_out_of_range(a) for a in analyses]
    formatted_results = [a.getFormattedResult(specs=a.getResultsRange(), decimalmark=decimalmark,sciformat=sciformat, html=html) for a in analyses]

    result_dict["results"] = results
    result_dict["result_types"] = result_types
    result_dict["interpretations"] = [(not x, not y) for (x, y) in out_of_range_flags]
    result_dict["formatted_results"] = formatted_results

    # Default interpretation: True only if all in range
    interpretation = all(not(flag[0]) for flag in out_of_range_flags), all(not(flag[1]) for flag in out_of_range_flags)

    # Case 1: String / Text
    if all(rt in ["string", "text"] for rt in result_types):
        result_dict["result"] = ",".join(set(formatted_results))
        result_dict["interpretation"] = interpretation
        result_dict["mean_interpretation"] = interpretation
        return result_dict

    # Case 2: Choices (select, multiselect, multiselect_duplicates, multichoice)
    if all(rt in ["select", "multiselect", "multiselect_duplicates", "multichoice"] for rt in result_types):
        concat = ",".join(set(formatted_results))
        # Validate all results against the allowed options (from ResultRange)
        result_dict["result"] = concat
        result_dict["interpretation"] = interpretation
        result_dict["mean_interpretation"] = interpretation
        return result_dict

    # Case 3: Date
    if all(rt == "date" for rt in result_types):
        dates = [r for r in results if r]
        if not dates:
            result_dict["result"] = None
            result_dict["interpretation"] = (False, False)
            result_dict["mean_interpretation"] = (False, False)
        else:
            result_dict["result"] = max(dates) if is_max_date else min(dates)
            result_dict["interpretation"] = (True, True)
            result_dict["mean_interpretation"] = (True, True)
        return result_dict

    # Case 4: Numeric (floatable)
    try:
        numeric_results = [float(r) for r in results if r is not None]
    except Exception:
        numeric_results = []

    if numeric_results:
        mean_value = sum(numeric_results) / len(numeric_results)
        result_dict["interpretation"] = interpretation

        # Get detection/spec limits from first valid analysis
        analysis = next((a for a in analyses if a is not None), None)
        
        result_dict["mean_interpretation"] =tuple(not x for x in is_out_of_range(analysis, result=mean_value))
        ldl = analysis.getLowerDetectionLimit() if hasattr(analysis, "getLowerDetectionLimit") else None
        udl = analysis.getUpperDetectionLimit() if hasattr(analysis, "getUpperDetectionLimit") else None
        spec = specs if specs else analysis.getResultsRange()

        # Spec limits and flags
        min_value = spec.get("min") if spec else None
        max_value = spec.get("max") if spec else None
        hidemin = spec.get("hidemin", False) if spec else False
        hidemax = spec.get("hidemax", False) if spec else False
        
        
        try:
            belowmin = hidemin and mean_value < float(hidemin) or False
        except (TypeError, ValueError):
            belowmin = False
        try:
            abovemax = hidemax and mean_value > float(hidemax) or False
        except (TypeError, ValueError):
            abovemax = False
            
        # If below min and hidemin enabled, return '<min'
        if belowmin:
            fdm = formatDecimalMark('< %s' % hidemin, decimalmark)
            result_dict["result"] = fdm.replace('< ', '&lt; ', 1) if html else fdm
            return result_dict
        # If above max and hidemax enabled, return '>max'
        if abovemax:
            fdm = formatDecimalMark('> %s' % hidemax, decimalmark)
            result_dict["result"] = fdm.replace('> ', '&gt; ', 1) if html else fdm
            return result_dict
        
        # Lower Limits of Detection and Quantification (LLOD and LLOQ)
        llod = to_float(analysis.getLowerDetectionLimit())
        lloq = to_float(analysis.getLowerLimitOfQuantification())
        if mean_value < llod:
            if llod != lloq:
                # Display "Not detected"
                result_str = t(_("result_below_llod", default="Not detected"))
                result_dict["result"] = cgi.escape(result_str) if html else result_str
                return result_dict

            # Display < LLOD
            ldl = float_to_string(llod)
            result_str = formatDecimalMark("< %s" % ldl, decimalmark)
            result_dict["result"] = cgi.escape(result_str) if html else result_str
            return result_dict

        if mean_value < lloq:
            lloq = float_to_string(lloq)
            lloq = formatDecimalMark(lloq, decimalmark)
            result_str = t(_("result_below_lloq", default="Detected but < ${LLOQ}",
                         mapping={"LLOQ": lloq}))
            result_dict["result"] = cgi.escape(result_str) if html else result_str
            return result_dict

        # Upper Limit of Quantification (ULOQ)
        uloq = to_float(analysis.getUpperLimitOfQuantification())
        if mean_value > uloq:
            uloq = float_to_string(uloq)
            result_str = formatDecimalMark('> %s' % uloq, decimalmark)
            result_dict["result"] = cgi.escape(result_str) if html else result_str
            return result_dict

        # Render numerical values
        threshold = analysis.getExponentialFormatPrecision()
        precision = analysis.getPrecision()
        mean_formatted = _format_decimal_or_sci(mean_value, precision, threshold, sciformat)
        mean_str_with_decimal = formatDecimalMark(mean_formatted, decimalmark)
        result_dict["result"] = mean_str_with_decimal
        return result_dict

    # Fallback: just return unique formatted results
    result_dict["result"] = ",".join(set(formatted_results))
    result_dict["interpretation"] = interpretation
    result_dict["mean_interpretation"] = interpretation
    
    return result_dict

@check_installed(None)
def getFormattedResultForServices(
    self,
    hidden=False,
    retracted=False,
    rejected=False,
    specs=None,
    decimalmark=".",
    sciformat=1,
    html=True,
    is_max_date=True,
):
    """Patched version of ReportView.getFormattedResultForServices

    Groups analyses by category and then by service, formatting
    the results with our custom getFormattedResultForService.
    """

    analyses = self.get_analyses_by(
        model_or_collection=self.collection,
        hidden=hidden,
        retracted=retracted,
        rejected=rejected,
    )
    logger.info("len of analyses '%s'", len(analyses))
    analysis_by_category_and_service = OrderedDict()
    
    categories = self.group_items_by("Category", analyses)
    logger.info("len of categories '%s'", len(categories))
    for category in categories:
        services = self.group_items_by('AnalysisService',categories[category])
        logger.info("len of analysis in category '%s': '%s'",category, len(categories[category]))
        analysis_by_category_and_service[category] = OrderedDict()
        for service in services:
                formatted = getFormattedResultForService(self.model,
                    analyses=services[service], decimalmark=decimalmark, specs=specs, sciformat=sciformat, html=html, is_max_date=is_max_date
                )
                analysis_by_category_and_service[category][service] = {}
                analysis_by_category_and_service[category][service]["analyses"] = services[service]
                analysis_by_category_and_service[category][service]["results_formatted"] = formatted

    return analysis_by_category_and_service

def generateId(self):
    import uuid
    return uuid.uuid4()