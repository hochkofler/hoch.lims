# -*- coding: utf-8 -*-
"""Dynamic Calculation: pick the Calculation of an analysis by criteria.

A Calculation declares *when it applies* through the rules stored by the
``IDynamicCalculationRulesBehavior`` behavior (see
``extender/behaviors/dynamiccalculation.py``). A rule has:

- ``keyword``: a pattern for the keyword of the AnalysisService
  (e.g. ``VAL_*``). Empty matches any service.
- ``criteria``: zero or more ``<field> = <pattern>`` pairs separated by
  ``;``, e.g. ``Processes = Blisteado; Batch.Product.code = 101-*``.

A field is a path of field names, accessors or attributes, followed through
references. The first name selects where the path starts:

- ``Analysis.<path>``: the analysis itself
- ``Condition.<title>``: the value of an analysis condition
- ``Sample.<path>``: the sample (or partition) the analysis lives in
- ``Batch.<path>``: the batch of the primary sample
- ``<path>``: the primary sample, then its batch. Partitions carry the
  SampleType of the active ingredient and no template, so the product and
  stage are read from the primary sample by default

Patterns are case-insensitive shell-style patterns (``*``, ``?``). A
reference matches by its title or id, a multi-valued field matches when any
of its values matches, and an empty or unknown field never matches. When
several rules match, the most specific one wins (see ``rule_specificity``).
When no rule matches, the AnalysisService keeps its own Calculation, so the
default SENAITE behaviour is unchanged.

Because SENAITE resolves the dependencies of an analysis from the
Calculation linked to the analysis (``bika.lims.api.analysis
.get_dependencies``), choosing the Calculation also chooses which dependent
analyses (e.g. ``CONC_UNK_*`` injections) the sample needs.

Rules are evaluated when analyses are added or saved, when the sample is
edited and when analysis conditions are set (see ``reapply``). An analysis
is only (re)linked while neither it nor its dependencies have results, so
captured data never changes of Calculation.
"""

from fnmatch import fnmatchcase

from Acquisition import aq_base
from AccessControl import Unauthorized
from bika.lims import api
from bika.lims import logger
from senaite.core.catalog import SETUP_CATALOG

# Attribute where the behavior stores the rules on the Calculation
RULES_ATTR = "dynamic_calculation_rules"

# Separators of the criteria of a rule
CRITERIA_SEPARATOR = ";"
CRITERION_OPERATOR = "="

# Wildcard characters of fnmatch patterns
WILDCARDS = "*?["

# Names that select where a field path starts
SCOPE_ANALYSIS = "analysis"
SCOPE_CONDITION = "condition"
SCOPE_SAMPLE = "sample"
SCOPE_BATCH = "batch"

# Request key to avoid re-entrant re-evaluations
REAPPLY_KEY = "_hoch_dynamic_calculation_reapply"

marker = object()


def normalize(value):
    """Returns the value as a lowercase unicode string for matching
    """
    if value is None:
        return u""
    return api.safe_unicode(value).strip().lower()


def parse_criteria(text):
    """Returns the list of (field, pattern) pairs of the criteria text

    Pairs without field or pattern are skipped
    """
    criteria = []
    for chunk in api.safe_unicode(text or u"").split(CRITERIA_SEPARATOR):
        if CRITERION_OPERATOR not in chunk:
            continue
        field, pattern = chunk.split(CRITERION_OPERATOR, 1)
        field = field.strip()
        pattern = normalize(pattern)
        if field and pattern:
            criteria.append((field, pattern))
    return criteria


def get_rules(calculation):
    """Returns the dynamic rules declared by the calculation

    Only rules with a keyword or at least one valid criterion are returned
    """
    # aq_base: never acquire the rules from a parent container
    rules = getattr(aq_base(calculation), RULES_ATTR, None) or []
    return filter(lambda rule: normalize(rule.get("keyword"))
                  or parse_criteria(rule.get("criteria")), rules)


def get_root_sample(sample):
    """Returns the root sample (primary) of the given sample or partition
    """
    parent = sample.getParentAnalysisRequest()
    while parent:
        sample = parent
        parent = sample.getParentAnalysisRequest()
    return sample


def get_batch(sample):
    getter = getattr(sample, "getBatch", None)
    return getter() if getter else None


def get_attribute(obj, name):
    """Returns the value of the field, accessor or attribute `name` of obj
    """
    if obj is None:
        return None
    field = api.get_fields(obj).get(name)
    if field is not None:
        accessor = field.getAccessor(obj) if hasattr(
            field, "getAccessor") else None
        return accessor() if accessor else field.get(obj)
    getter = getattr(obj, "get{}".format(name), marker)
    if getter is not marker and callable(getter):
        return getter()
    value = getattr(aq_base(obj), name, marker)
    if value is marker:
        return None
    # bind the attribute to the object (acquisition) if needed
    value = getattr(obj, name)
    return value() if callable(value) else value


def as_list(value):
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def as_object(value):
    """Returns the object of a UID, or the value itself
    """
    if isinstance(value, basestring) and api.is_uid(value) and value != "0":
        return api.get_object_by_uid(value, default=value)
    return value


def follow(objs, names):
    """Follows the field path `names` from the given objects
    """
    values = objs
    for name in names:
        next_values = []
        for value in values:
            value = as_object(value)
            if not api.is_object(value):
                continue
            next_values.extend(as_list(get_attribute(value, name)))
        values = next_values
    return map(as_object, values)


def to_texts(value):
    """Returns the texts a value is matched by
    """
    if api.is_object(value):
        texts = [api.get_title(value), api.get_id(value)]
    elif isinstance(value, dict):
        texts = []
    elif isinstance(value, bool):
        texts = [value and u"true" or u"false"]
    else:
        texts = [value]
    return filter(None, map(normalize, texts))


class MatchContext(object):
    """The objects a rule is evaluated against

    :param sample: the sample (or partition) the analysis lives or will live
    :param analysis: the analysis, None when it does not exist yet
    """

    def __init__(self, sample, analysis=None):
        self.sample = sample
        self.analysis = analysis
        self.root = get_root_sample(sample)
        self._cache = {}

    def get_texts(self, path):
        """Returns the texts of the values of the field path
        """
        key = path.lower()
        if key not in self._cache:
            self._cache[key] = self._resolve(path)
        return self._cache[key]

    def _resolve(self, path):
        names = filter(None, map(lambda n: n.strip(), path.split(".")))
        if not names:
            return []
        scope, rest = names[0].lower(), names[1:]

        if scope == SCOPE_CONDITION:
            return self._condition_texts(".".join(rest))

        if scope == SCOPE_ANALYSIS:
            starts = [self.analysis] if self.analysis else []
        elif scope == SCOPE_SAMPLE:
            starts = [self.sample]
        elif scope == SCOPE_BATCH:
            starts = [get_batch(self.root)]
        else:
            # primary sample first, then its batch
            rest = names
            for start in (self.root, get_batch(self.root)):
                values = follow(filter(None, [start]), rest)
                texts = self._texts(values)
                if texts:
                    return texts
            return []

        if not rest:
            return self._texts(filter(None, starts))
        return self._texts(follow(filter(None, starts), rest))

    def _condition_texts(self, title):
        if not self.analysis or not title:
            return []
        title = normalize(title)
        for condition in self.analysis.getConditions() or []:
            if normalize(condition.get("title")) == title:
                return self._texts(as_list(condition.get("value")))
        return []

    def _texts(self, values):
        texts = []
        for value in values:
            texts.extend(to_texts(value))
        return texts


def rule_matches(rule, keyword, context):
    """Returns whether the keyword and all criteria of the rule match
    """
    pattern = normalize(rule.get("keyword"))
    if pattern and not fnmatchcase(normalize(keyword), pattern):
        return False
    for path, pattern in parse_criteria(rule.get("criteria")):
        texts = context.get_texts(path)
        if not any(map(lambda text: fnmatchcase(text, pattern), texts)):
            return False
    return True


def rule_specificity(rule):
    """Returns a sortable specificity score for the rule.

    A rule is more specific the more conditions (keyword and criteria) it
    sets and, for the same number of conditions, the more literal
    (non-wildcard) characters its patterns have. So ``VAL_PARACETAMOL``
    beats ``VAL_*``, which in turn beats a rule without keyword.
    """
    patterns = [pattern for path, pattern in parse_criteria(
        rule.get("criteria"))]
    keyword = normalize(rule.get("keyword"))
    if keyword:
        patterns.append(keyword)
    literals = sum(len([c for c in p if c not in WILDCARDS]) for p in patterns)
    return (len(patterns), literals)


def get_dynamic_calculations():
    """Returns the active calculations that declare dynamic rules
    """
    query = {"portal_type": "Calculation", "is_active": True}
    calculations = map(api.get_object, api.search(query, SETUP_CATALOG))
    return filter(get_rules, calculations)


def resolve_calculation(keyword, context, calculations=None):
    """Returns the calculation whose rules best match, or None.

    :param keyword: keyword of the AnalysisService
    :param context: the `MatchContext` the criteria are evaluated against
    :param calculations: candidate calculations. All the active calculations
        with dynamic rules are used if not set
    :returns: the matching calculation or None if no rule matches or the best
        match is ambiguous
    """
    if calculations is None:
        calculations = get_dynamic_calculations()

    candidates = []
    for calculation in calculations:
        for rule in get_rules(calculation):
            if rule_matches(rule, keyword, context):
                candidates.append((rule_specificity(rule), calculation))

    if not candidates:
        return None

    best = max(score for score, calc in candidates)
    winners = set(calc for score, calc in candidates if score == best)
    if len(winners) > 1:
        # Two different calculations are equally specific. Do not guess:
        # keep the service default and make the conflict visible
        logger.error(
            "Dynamic calculation: ambiguous rules for '{}': {}".format(
                keyword, ", ".join(map(api.get_title, winners))))
        return None

    return winners.pop()


def get_calculation_dependencies(calculation):
    """Returns the services the calculation depends on
    """
    if not calculation:
        return []
    return calculation.getDependentServices() or []


def get_lineage_analyses(sample):
    """Returns the analyses of the sample and of all its partitions
    """
    analyses = list(sample.objectValues("Analysis"))
    for descendant in sample.getDescendants(all_descendants=True):
        analyses.extend(descendant.objectValues("Analysis"))
    return analyses


def reapply(sample):
    """Re-evaluates the dynamic rules for the analyses of the sample lineage

    Call it after changing data the rules depend on, e.g. a sample field set
    after sampling. Analyses or dependencies with results are not changed.
    Returns whether the rules were evaluated.
    """
    if sample is None or not api.is_active(sample):
        return False
    if not get_dynamic_calculations():
        return False

    request = api.get_request()
    if request is not None and request.get(REAPPLY_KEY):
        return False

    root = get_root_sample(sample)
    if api.is_temporary(root) or root.checkCreationFlag():
        # the sample is being created, the data manager already handles it
        return False

    # Read the analyses from the containers, not from the catalog: right
    # after changes the catalog might not be up to date yet, and an empty
    # list would make setAnalyses remove all the analyses
    analyses = get_lineage_analyses(root)
    if not analyses:
        return False
    dependencies = set()
    for analysis in analyses:
        for calculation in (analysis.getCalculation(),
                            analysis.getAnalysisService().getCalculation()):
            dependencies.update(map(
                api.get_uid, get_calculation_dependencies(calculation)))
    requested = [an.getServiceUID() for an in analyses
                 if an.getServiceUID() not in dependencies]

    # keep the current prices and hidden flags, otherwise they are reset to
    # the values of the service
    prices = dict((an.getServiceUID(), an.getPrice()) for an in analyses)
    hidden = [{"uid": an.getServiceUID(), "hidden": an.getHidden()}
              for an in analyses]

    if request is not None:
        request.set(REAPPLY_KEY, True)
    try:
        root.setAnalyses(requested, prices=prices, hidden=hidden)
    except Unauthorized:
        logger.warn("Dynamic calculation: not allowed to update the "
                    "analyses of {}".format(api.get_id(root)))
        return False
    finally:
        if request is not None:
            request.set(REAPPLY_KEY, False)
    return True


def on_sample_edited(sample, event):
    """Re-evaluates the dynamic rules after the sample has been edited
    """
    from hoch.lims import is_installed
    if not is_installed():
        return
    reapply(sample)
