from hoch.lims import check_installed
from bika.lims.config import MAX_OPERATORS
from bika.lims.config import MIN_OPERATORS
from bika.lims.utils import formatDecimalMark

@check_installed(None)
def get_formatted_specs2(self, analysis):
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

    # --- If it's a choice type, filter by range and return the matching texts ---
    if (is_choice_type or values_texts) and (specs.get("min") or specs.get("max")):
        filtered_texts = []
        for num, text in values_texts.items():
            if (not specs.get("min") or matches_operator(num, specs["min"], min_operator)) and \
               (not specs.get("max") or matches_operator(num, specs["max"], max_operator)):
                filtered_texts.append(text)

        # Optional: if all choices are included, return a single label
        if len(filtered_texts) == len(values_texts):
            return "All"

        return ", ".join(filtered_texts)

    # --- Default numeric range case ---
    fs = ""
    if specs.get('min') is not None and specs.get('max') is not None:
        fs = "%s - %s" % (specs['min'], specs['max'])
    elif specs.get('min') is not None:
        fs = "%s %s" % (min_operator, specs['min'])
    elif specs.get('max') is not None:
        fs = "%s %s" % (max_operator, specs['max'])

    return formatDecimalMark(fs, self.decimal_mark)