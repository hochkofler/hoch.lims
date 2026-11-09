# -*- coding: utf-8 -*-
"""HPLC injections stored as a table inside an analysis.

Instead of one analysis per injection (``CONC_UNK_01`` … ``CONC_ST_06``),
the injections of a chromatographic run are rows of the ``Injections`` field
of the analysis whose service is flagged with ``ReceivesInjections`` (the
assay, e.g. ``VAL_PARACETAMOL``). Each row keeps the data of the injection
(number, type, concentration, retention time, area, plate count, vial,
acquisition date and data file), so the number of injections is whatever the
run delivered.

Other analyses of the same sample (e.g. content uniformity) read the rows of
that analysis, so the data is never duplicated. Samples created before this
change keep their ``CONC_*`` analyses and the calculations keep reading them.
"""

import re

from bika.lims import api
from bika.lims import logger
from bika.lims.interfaces import IRoutineAnalysis
from bika.lims.interfaces import ISubmitted

# Field names (schema extenders, see extender/injections.py)
INJECTIONS_FIELD = "Injections"
RECEIVES_FIELD = "ReceivesInjections"

# Injection types
SAMPLE = "UNK"
STANDARD = "ST"
TYPES = (SAMPLE, STANDARD)

# Columns of a row, in display order
COLUMNS = (
    "type", "number", "conc", "std_conc", "ret_time", "area", "ntp_usp",
    "vial_number", "weight", "acquired", "sample_name", "data_file", "peak",
)

# Columns holding numbers
NUMERIC = ("conc", "std_conc", "ret_time", "area", "ntp_usp", "weight")

# Columns entered in the LIMS, kept when an instrument reimports the row
KEPT_ON_REIMPORT = ("weight",)


def get_field(obj, name):
    return api.get_fields(obj).get(name) if obj is not None else None


def receives_injections(obj):
    """Returns whether the analysis (or service) receives HPLC injections
    """
    if obj is None:
        return False
    if IRoutineAnalysis.providedBy(obj):
        obj = obj.getAnalysisService()
    field = get_field(obj, RECEIVES_FIELD)
    return bool(field and field.get(obj))


def normalize_type(value):
    """Returns UNK or ST for the given injection type
    """
    value = api.safe_unicode(value or u"").strip().upper()
    if value.startswith(u"ST"):
        return STANDARD
    return SAMPLE


# Injection number <preparation or unit>.<injection>, e.g. 2.3
GROUPED_NUMBER = re.compile(r"^0*(\d+)\.0*(\d+)$")


def normalize_number(value):
    """Returns the injection number: zero padded, e.g. "07", or as
    <preparation or unit>.<injection>, e.g. "2.3"
    """
    value = api.safe_unicode(value or u"").strip()
    if value.isdigit():
        return value.zfill(2)
    match = GROUPED_NUMBER.match(value)
    if match:
        return u"{}.{}".format(int(match.group(1)), int(match.group(2)))
    return value


def grouped(rows):
    """Whether the rows are numbered <group>.<injection>
    """
    return any(GROUPED_NUMBER.match(r.get("number") or u"") for r in rows)


def number_key(number):
    """Sort key of an injection number: 9 before 10 and 1.2 before 1.10
    """
    number = api.safe_unicode(number or u"")
    parts = number.split(u".")
    if all(part.isdigit() for part in parts):
        return (0, ) + tuple(int(part) for part in parts)
    return (1, number)


def to_float(value):
    """Returns the value as float, accepting a decimal comma, or None
    """
    if value in (None, ""):
        return None
    if isinstance(value, basestring):
        value = value.strip().replace(",", ".")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_row(row):
    """Returns a clean copy of the injection row
    """
    clean = {}
    for column in COLUMNS:
        value = row.get(column)
        if column in NUMERIC:
            value = to_float(value)
        elif column == "type":
            value = normalize_type(value)
        elif column == "number":
            value = normalize_number(value)
        elif value is None:
            value = u""
        else:
            value = api.safe_unicode(value)
        clean[column] = value
    return clean


def row_key(row):
    return (row.get("type"), row.get("number"))


def sort_rows(rows):
    def key(row):
        return (TYPES.index(row.get("type", SAMPLE)),
                number_key(row.get("number")))
    return sorted(rows, key=key)


def get_injections(analysis):
    """Returns the injection rows stored in the analysis
    """
    field = get_field(analysis, INJECTIONS_FIELD)
    if field is None:
        return []
    return [dict(row) for row in (field.get(analysis) or [])]


def set_injections(analysis, rows):
    """Stores the injection rows in the analysis
    """
    field = get_field(analysis, INJECTIONS_FIELD)
    if field is None:
        raise ValueError("{} has no injections field".format(
            api.get_id(analysis)))
    field.set(analysis, sort_rows(map(normalize_row, rows)))


def merge_injections(existing, new, override=False):
    """Merges new injection rows into the existing ones

    A new row replaces an existing row with the same type and number only
    when `override` is set.

    :returns: tuple of (rows, added, replaced, skipped)
    """
    existing = map(normalize_row, existing)
    new = map(normalize_row, new)
    added = replaced = skipped = 0
    # numbers 1.1, 1.2... and 01, 02... can not be mixed in a type: the new
    # numbering replaces the old one when overriding, otherwise it is skipped
    for kind in set(row["type"] for row in new):
        old_rows = [r for r in existing if r["type"] == kind]
        if not old_rows or grouped(old_rows) == grouped(
                [r for r in new if r["type"] == kind]):
            continue
        if override:
            existing = [r for r in existing if r["type"] != kind]
            replaced += len(old_rows)
        else:
            skipped += len([r for r in new if r["type"] == kind])
            new = [r for r in new if r["type"] != kind]
    rows = dict((row_key(r), r) for r in existing)
    for row in new:
        key = row_key(row)
        if key in rows:
            if not override:
                skipped += 1
                continue
            for column in KEPT_ON_REIMPORT:
                if row.get(column) is None:
                    row[column] = rows[key].get(column)
            replaced += 1
        else:
            added += 1
        rows[key] = row
    return sort_rows(rows.values()), added, replaced, skipped


def get_target_analyses(sample, states=None):
    """Returns the analyses of the sample that receive injections

    :param states: if set, only analyses in these review states
    """
    analyses = []
    for analysis in sample.objectValues("Analysis"):
        if not receives_injections(analysis):
            continue
        if states and api.get_review_status(analysis) not in states:
            continue
        analyses.append(analysis)
    return analyses


def get_source_analysis(analysis):
    """Returns the analysis whose injections the given analysis uses

    This is the analysis itself when it receives injections, otherwise the
    analysis of the same sample (or partition) that receives them.
    """
    if receives_injections(analysis):
        return analysis
    sample = analysis.getRequest()
    targets = filter(lambda an: not api.get_review_status(an) in (
        "cancelled", "retracted", "rejected"), get_target_analyses(sample))
    return targets and targets[0] or None


def get_values(analysis, injection_type=SAMPLE):
    """Returns the concentrations of the injections of the given type

    :returns: list of floats, sorted by injection number, or None when the
        analysis has no injection source or no injection rows at all
    """
    source = get_source_analysis(analysis)
    if source is None:
        return None
    rows = get_injections(source)
    if not rows:
        return None
    rows = filter(lambda r: r.get("type") == injection_type, sort_rows(rows))
    return [r.get("conc") for r in rows if r.get("conc") is not None]


def recalculate(sample, override=True):
    """Recalculates the analyses of the sample that are not submitted yet

    Analyses reading injections do not declare dependencies, so SENAITE does
    not recalculate them on its own when injections change.
    """
    updated = []
    for analysis in sample.objectValues("Analysis"):
        if ISubmitted.providedBy(analysis):
            continue
        if not analysis.getCalculationFormula():
            continue
        try:
            if analysis.calculateResult(override=override, cascade=False):
                updated.append(analysis)
                analysis.reindexObject()
        except Exception as exc:
            logger.error("Injections: cannot calculate {} of {}: {}".format(
                analysis.getKeyword(), api.get_id(sample), exc))
    return updated
