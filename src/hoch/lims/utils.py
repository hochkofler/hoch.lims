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

    choices = interim.get("choices", None)
    if not choices:
        # Value is the text
        return value