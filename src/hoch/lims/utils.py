from collections import OrderedDict
from bika.lims.utils import formatDecimalMark
from bika.lims import api

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
    
def get_formatted_interim(interim, dmk=","):
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
        else:
            # values are captured directly by the user
            values = [formatDecimalMark(value, dmk) for value in values]

        # return the values as a single string
        values = filter(None, values)
        return "<br/>".join(values)

def compute_variables_dict(obj):
    """Build variables_dict from variables_table"""
    data = {}
    cache = {}
    for row in (obj.variables_table or []):
        param = row.get("parameter")
        value = row.get("value")
        uids = row.get("service")
        if not uids:
            continue
        for uid in (uids if isinstance(uids, (list, tuple)) else [uids]):
            if uid not in cache:
                service = api.get_object_by_uid(uid)
                cache[uid] = service.getKeyword() if service else uid
            code = cache[uid]
            
            if param and value is not None:
                data.setdefault(code, {})[param] = value
    return data