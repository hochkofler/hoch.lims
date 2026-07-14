from collections import OrderedDict
from bika.lims.utils import formatDecimalMark
from bika.lims import api
import re
from hoch.lims import logger
from bika.lims.api import get_object_by_uid
from bika.lims.config import MAX_OPERATORS
from bika.lims.config import MIN_OPERATORS
from bika.lims.utils.analysis import _format_decimal_or_sci
_marker = object()

def is_interim_editable(interim):
    """Returns whether the interim is editable or not

    :param interim: interim field
    :type interim: dict
    :returns: True if user can edit this interim
    :rtype: bool
    """
    if is_interim_empty(interim):
        return True

    statuses = ["to_be_verified", "verified", "rejected"]
    for status in statuses:
        status_id = "status_{}".format(status)
        if interim.get(status_id, False):
            return False

    return True

def is_interim_empty(interim):
    """Returns whether an interim is empty or its value is considered empty

    :param interim: interim field
    :type interim: dict
    :returns: True if the value or text representation of this interim is empty
    :rtype: bool
    """
    text = get_interim_text(interim, default=None)
    return not text

def get_interim_text(interim, default=_marker):
    """Returns the text displayed for this interim field. Typically, the raw
    value when interim has no choices set and the choice text otherwise

    :param interim: interim field
    :type interim: dict
    :returns: The text representation of the value of this interim
    :rtype: string
    """
    value = interim.get("value", None)
    if value is None:
        if default is _marker:
            raise ValueError("Interim without value")
        return default
    
def get_interim_choices(interim):
        """Parse the interim choices field
        """
        choices = interim.get("choices")
        if not choices:
            return None
        items = choices.split("|")
        pairs = map(lambda item: item.strip().split(":"), items)
        return OrderedDict(pairs)
    
def is_multi_interim(interim):
    """Returns whether the interim stores a list of values instead of a
    single value
    """
    result_type = interim.get("result_type", "")
    return result_type.startswith("multi")
    
def get_formatted_interim(interim):
        """Returns the formatted value of the interim
        """
        # get the 'raw' value stored for this interim
        raw_value = interim.get("value")

        if is_multi_interim(interim):
            # value is a jsonified list of values
            values = api.to_list(raw_value)
        else:
            values = [raw_value]

        # remove empties
        values = filter(None, values)

        choices = get_interim_choices(interim)
        if choices:
            # values are predefined options for selection
            values = [choices.get(v) for v in values]
        elif interim.get('result_type', '') == 'time':
            values = [format_time_value(value) for value in values]
        else:
            dmk = get_decimal_mark()
            # values are captured directly by the user
            values = [formatDecimalMark(value, dmk) for value in values]

        # return the values as a single string
        values = filter(None, values)
        return "<br/>".join(values)

def separate_number_from_text(text):
    text.strip()
    match = re.search(r"[\d.,]+", text)
    if not match:
        logger.info("Separate retrun '%s'", {"number": None, "text": text})
        return {"number": None, "text": text}
    
    number = match.group(0)
    not_number = text[match.end():].strip()
    return {"number": number, "text": not_number}

def compute_variables_dict(obj):
    """Build variables_dict from variables_table"""
    data = {}
    cache = {}
    for row in (obj.variables_table or []):
        param = row.get("parameter")
        value = row.get("value")
        uids = row.get("service")
        unit = row.get("unit")
        if not uids:
            continue
        for uid in (uids if isinstance(uids, (list, tuple)) else [uids]):
            if uid not in cache:
                service = get_object_by_uid(uid)
                cache[uid] = service.getKeyword() if service else uid
            code = cache[uid]
            
            if param and value is not None:
                data.setdefault(code, {})[param] = (value, unit)
    return data

def get_formatted_specs(analysis, with_shoulder_range=False,
                            lt_operator=None, leq_operator=None, 
                            gt_operator=None, geq_operator=None):
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
        
        OPERATORS = {}
        OPERATORS["gt"] = gt_operator or MAX_OPERATORS.getValue("gt", ">")
        OPERATORS["geq"] = geq_operator or MAX_OPERATORS.getValue("geq", ">=")
        OPERATORS["lt"] = lt_operator or MIN_OPERATORS.getValue("lt", "<")
        OPERATORS["leq"] = leq_operator or MIN_OPERATORS.getValue("leq", "<=")
        # Get min and max operators (default values if missing)
        min_operator = specs.get("min_operator") or ""
        min_operator = OPERATORS.get(min_operator, ">=")
        max_operator = specs.get("max_operator") or ""
        max_operator = OPERATORS.get(max_operator, "<=")

        # Helper function to evaluate the operator condition
        def matches_operator(value, limit, operator):
            value = float(value)
            limit = float(limit)
            if operator == OPERATORS["geq"]:
                return value >= limit
            elif operator == OPERATORS["gt"]:
                return value > limit
            elif operator == OPERATORS["leq"]:
                return value <= limit
            elif operator == OPERATORS["lt"]:
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
        
        valid_min_specs = specs_min or specs_min == "0" or specs_min == 0
        valid_max_specs = specs_max or specs_max == "0" or specs_max == 0
        
        if (is_choice_type or values_texts) and (valid_min_specs or valid_max_specs):
            filtered_texts = []
            for num, text in values_texts.items():
                if (not valid_min_specs or matches_operator(num, specs_min, min_operator)) and \
                (not valid_max_specs or matches_operator(num, specs_max, max_operator)):
                    filtered_texts.append(text)

            # Optional: if all choices are included, return a single label
            # if len(filtered_texts) == len(values_texts):
            #     return "All"

            return ", ".join(filtered_texts)

        # --- Default numeric range case ---
        fs = ""
        threshold = analysis.getExponentialFormatPrecision()
        precision = analysis.getPrecision()
        setup = api.get_setup()
        sci_notation = int(setup.getScientificNotationReport())
        formated_max = ""
        formated_min = ""
        if specs_min:
            formated_min = _format_decimal_or_sci(specs_min, precision, threshold, sci_notation)
        
        if specs_max:
            formated_max = _format_decimal_or_sci(specs_max, precision, threshold, sci_notation)
            
        if specs_min and specs_max:
            fs = "%s - %s" % (formated_min, formated_max)
        elif specs_min:
            fs = "%s %s" % (min_operator, formated_min)
        elif specs_max:
            fs = "%s %s" % (max_operator, formated_max)

        return formatDecimalMark(fs, get_decimal_mark())
    
def get_decimal_mark():
        """Returns the decimal mark
        """
        setup = api.get_setup()
        return setup.getDecimalMark()