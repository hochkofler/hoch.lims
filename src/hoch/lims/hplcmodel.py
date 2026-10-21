# -*- coding: utf-8 -*-
"""Configurable HPLC calculation model (external standard).

A model computes a result from the injections of a run in fixed stages,
each defined by an editable expression::

    1. Standard        C_st = <standard expression>              (e.g. ug/mL)
    2. Per injection   C_i  = A_i * C_st / A_st                  (fixed)
    3. Per unit        C_u  = mean of the C_i of the unit
                       cantidad = <amount expression>            (e.g. mg/unit)
    4. Per unit        resultado = <result expression>           (e.g. %)
    5. Aggregate       mean | uniformity (acceptance value) | dissolution

Factors are variables. Inserting a factor means writing it in an expression
and giving it a value from one of the sources (run data, product data,
standard lot, other analyses, derived variables). Every value used is
returned in the trace, so a result can be reconstructed step by step.

Expressions only allow numbers, variables, + - * / ** and parentheses and
the functions in FUNCTIONS. Dotted names (``valoracion.agua_st``) are
variables too, so values of other analyses can be referenced.

Two functions make factors optional, so a single model can serve products
with and without a given correction:

- ``opcional(x, default)``: the value of the variable x, or the default
  when x has no value (e.g. ``opcional(D_mue, 1)``)
- ``si(condition, a, b)``: a when the condition is not 0, otherwise b. Only
  the chosen branch needs values, so a product flag turns a factor on and
  makes its data mandatory: ``si(usa_agua, agua_st, 0)`` requires agua_st
  only for products with usa_agua = 1
"""

import ast
import math
import operator

# Variables provided by the model itself
BUILTIN = ("A_i", "A_st", "C_st", "C_i", "C_u", "A_u", "W_mue", "unidad",
           "cantidad", "preparacion")

# Variables that override the model parameters, e.g. from the product
# (a dissolution test defines its own Q, a method its own injections)
SAMPLE_INJECTIONS = "n_iny_mue"
STANDARD_INJECTIONS = "n_iny_st"
DISSOLUTION_Q = "Q"
# Standard concentration from the instrument (Std. Conc. of the file)
STANDARD_FROM_INSTRUMENT = "usa_std_equipo"
STANDARD_FACTOR = "f_std_equipo"
STANDARD_TOLERANCE = "tol_std_equipo"

# Functions evaluated lazily (only the needed arguments)
OPTIONAL = ("opcional", "optional")
CONDITIONAL = ("si", "if_")
LAZY = OPTIONAL + CONDITIONAL

FUNCTIONS = {
    "mean": lambda *v: sum(v) / float(len(v)),
    "min": min,
    "max": max,
    "abs": abs,
    "sqrt": math.sqrt,
    "round": round,
}

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

UNARY = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

MEAN = "mean"
UNIFORMITY = "uniformity"
DISSOLUTION = "dissolution"
AGGREGATES = (MEAN, UNIFORMITY, DISSOLUTION)

SAMPLE = "UNK"
STANDARD = "ST"


class ModelError(Exception):
    """The model can not be calculated (a message for the analyst)"""


class StandardMismatch(ModelError):
    """The standard concentration of the instrument does not match the one
    expected from the selected reference standard
    """

    def __init__(self, check):
        self.check = check
        super(StandardMismatch, self).__init__(
            "Std. Conc. of the instrument ({instrument:.6g}) differs "
            "{difference:.3f} % from the expected one ({expected:.6g}), "
            "tolerance {tolerance:g} %".format(**check))


class MissingVariables(ModelError):

    def __init__(self, names, stage):
        self.names = sorted(set(names))
        self.stage = stage
        super(MissingVariables, self).__init__(
            "Missing values for {}: {}".format(stage, ", ".join(self.names)))


def dotted_name(node):
    """Returns the dotted name of a Name/Attribute node, or None
    """
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def parse(expression):
    """Parses and validates an expression

    :raises ModelError: if the expression is not valid or not allowed
    """
    expression = (expression or "").strip()
    if not expression:
        raise ModelError("Empty expression")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ModelError("Invalid expression '{}': {}".format(
            expression, exc.msg))
    check(tree.body, expression)
    return tree.body


def check(node, expression):
    if isinstance(node, ast.Num):
        return
    if isinstance(node, (ast.Name, ast.Attribute)):
        if dotted_name(node) is None:
            raise ModelError("Not allowed in '{}'".format(expression))
        return
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        check(node.left, expression)
        check(node.right, expression)
        return
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        check(node.operand, expression)
        return
    if isinstance(node, ast.Call):
        name = isinstance(node.func, ast.Name) and node.func.id
        if name not in FUNCTIONS and name not in LAZY or node.keywords or \
                getattr(node, "starargs", None) or \
                getattr(node, "kwargs", None):
            raise ModelError("Function not allowed in '{}'".format(
                expression))
        if name in OPTIONAL and (len(node.args) != 2 or dotted_name(
                node.args[0]) is None):
            raise ModelError("opcional() needs a variable and a default "
                             "value in '{}'".format(expression))
        if name in CONDITIONAL and len(node.args) != 3:
            raise ModelError("si() needs a condition and two values in "
                             "'{}'".format(expression))
        for arg in node.args:
            check(arg, expression)
        return
    raise ModelError("Not allowed in '{}': {}".format(
        expression, type(node).__name__))


def names(expression):
    """Returns the variable names used by the expression
    """
    found = set()

    def visit(node):
        if isinstance(node, (ast.Name, ast.Attribute)):
            found.add(dotted_name(node))
        elif isinstance(node, ast.BinOp):
            visit(node.left)
            visit(node.right)
        elif isinstance(node, ast.UnaryOp):
            visit(node.operand)
        elif isinstance(node, ast.Call):
            for arg in node.args:
                visit(arg)

    visit(parse(expression))
    return found


def evaluate(expression, variables, stage="expression"):
    """Evaluates the expression with the given variables

    :raises MissingVariables: when a needed variable has no value
    """
    tree = parse(expression)
    missing = []

    def has(name):
        return variables.get(name) is not None

    def ev(node):
        if isinstance(node, ast.Num):
            return float(node.n)
        if isinstance(node, (ast.Name, ast.Attribute)):
            name = dotted_name(node)
            if not has(name):
                missing.append(name)
                return 1.0
            return float(variables[name])
        if isinstance(node, ast.BinOp):
            return OPERATORS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp):
            return UNARY[type(node.op)](ev(node.operand))
        if isinstance(node, ast.Call):
            name = node.func.id
            if name in OPTIONAL:
                if has(dotted_name(node.args[0])):
                    return ev(node.args[0])
                return ev(node.args[1])
            if name in CONDITIONAL:
                before = len(missing)
                condition = ev(node.args[0])
                if len(missing) > before:
                    # without the condition, the branch is unknown
                    return 1.0
                return ev(node.args[1]) if condition else ev(node.args[2])
            return float(FUNCTIONS[name](*map(ev, node.args)))
        raise ModelError("Not allowed")

    try:
        value = ev(tree)
    except ZeroDivisionError:
        if missing:
            raise MissingVariables(missing, stage)
        raise ModelError("Division by zero in {}: {}".format(
            stage, expression))
    if missing:
        raise MissingVariables(missing, stage)
    return value


def mean(values):
    return sum(values) / float(len(values))


def stdev(values):
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def acceptance_value(values, T=100.0, k=2.4):
    """USP <905> acceptance value (L1) of the units in % of label claim
    """
    m = mean(values)
    s = stdev(values)
    if T <= 101.5:
        reference = min(max(m, 98.5), 101.5)
    else:
        reference = min(max(m, 98.5), T)
    return abs(reference - m) + k * s, reference


def sort_key(row):
    number = u"{}".format(row.get("number") or u"")
    return number.zfill(4) if number.isdigit() else number


def resolve_derived(derived, variables):
    """Evaluates the derived variables, in any order of dependency
    """
    values = dict(variables)
    pending = dict(derived or {})
    trace = {}
    while pending:
        progress = False
        for name, expression in sorted(pending.items()):
            try:
                values[name] = evaluate(expression, values, stage=name)
            except MissingVariables as exc:
                if set(exc.names) & set(pending):
                    continue
                raise
            trace[name] = values[name]
            del pending[name]
            progress = True
        if not progress:
            raise ModelError("Circular derived variables: {}".format(
                ", ".join(sorted(pending))))
    return values, trace


def calculate(model, variables, injections):
    """Calculates the model

    :param model: dict with the keys
        - standard: expression of the standard concentration
        - amount: expression of the amount per unit
        - result: expression of the result per unit
        - injections_per_unit: sample injections averaged per unit
          (overridden by the variable n_iny_mue)
        - standard_injections_per_prep: standard injections of each
          preparation, each preparation with its own weight W_st_1,
          W_st_2...; 0 or missing = one concentration for all the standard
          injections (overridden by the variable n_iny_st)
        - aggregate: mean, uniformity or dissolution
        - derived: optional {name: expression} of derived variables
        - T, k: uniformity parameters, Q: dissolution parameter (%),
          overridden by the variable Q
        - standard_from_instrument: use the Std. Conc. of the standard
          injections (x standard_factor, default 1000: mg/mL to ug/mL)
          once it matches the concentration of the standard expression
          within standard_tolerance % (default 0.1); otherwise the
          calculation is blocked (StandardMismatch). Overridden by the
          variables usa_std_equipo, f_std_equipo and tol_std_equipo
    :param variables: {name: value} from all the sources
    :param injections: rows with type (UNK/ST), number, area and an
        optional weight (sample weight of the unit, W_mue)
    :returns: dict with the result and the full trace
    """
    aggregate = model.get("aggregate") or MEAN
    if aggregate not in AGGREGATES:
        raise ModelError("Unknown aggregate: {}".format(aggregate))

    values, derived = resolve_derived(model.get("derived"), variables)

    def parameter(name, key, default):
        value = values.get(name)
        if value is None:
            value = model.get(key)
        return default if value in (None, "") else value

    per_unit = int(parameter(SAMPLE_INJECTIONS, "injections_per_unit", 1))
    per_prep = int(parameter(STANDARD_INJECTIONS,
                             "standard_injections_per_prep", 0))

    standards = [r for r in injections
                 if r.get("type") == STANDARD and r.get("area")]
    samples = sorted([r for r in injections
                      if r.get("type") == SAMPLE and r.get("area")],
                     key=sort_key)
    if not standards:
        raise ModelError("No standard injections")
    if not samples:
        raise ModelError("No sample injections")
    if len(samples) % per_unit:
        raise ModelError(
            "{} sample injections can not be grouped in units of {}".format(
                len(samples), per_unit))

    # 1. standard: one concentration per preparation, each with its own
    # weight (W_st_1, W_st_2...), or a single one for all the injections
    standards = sorted(standards, key=sort_key)
    preparations = []
    if per_prep:
        if len(standards) % per_prep:
            raise ModelError(
                "{} standard injections can not be grouped in preparations "
                "of {}".format(len(standards), per_prep))
        for index in range(0, len(standards), per_prep):
            rows = standards[index:index + per_prep]
            preparations.append({"preparacion": len(preparations) + 1,
                                 "rows": rows})
        missing = []
        for prep in preparations:
            number = prep["preparacion"]
            # X_<n> is the value of X for preparation n (W_st_1, W_st_2...)
            prep_values = dict(values, preparacion=number)
            suffix = "_{}".format(number)
            for name, value in values.items():
                if name.endswith(suffix) and value is not None:
                    prep_values[name[:-len(suffix)]] = value
            if values.get("W_st" + suffix) is None:
                # the weight of each preparation is its own
                prep_values.pop("W_st", None)
            prep["W_st"] = prep_values.get("W_st")
            try:
                prep["C_st"] = evaluate(model["standard"], prep_values,
                                        stage="standard")
            except MissingVariables as exc:
                for name in exc.names:
                    per_preparation = name == "W_st" or any(
                        n.startswith(name + "_") for n in values)
                    missing.append(name + suffix if per_preparation
                                   else name)
                continue
            areas = [float(r["area"]) for r in prep.pop("rows")]
            prep.update({"areas": areas, "A_st": mean(areas),
                         "rsd": stdev(areas) / mean(areas) * 100})
        if missing:
            raise MissingVariables(missing, "standard")
        C_st = mean([prep["C_st"] for prep in preparations])
    else:
        C_st = evaluate(model["standard"], values, stage="standard")
    A_st = mean([float(r["area"]) for r in standards])

    # The instrument concentration is used once it matches the expected one
    check = None
    if parameter(STANDARD_FROM_INSTRUMENT, "standard_from_instrument", 0):
        reported = [r.get("std_conc") for r in standards
                    if r.get("std_conc") not in (None, "")]
        if not reported:
            raise ModelError("The instrument file has no Std. Conc. for the "
                             "standard injections")
        factor = float(parameter(STANDARD_FACTOR, "standard_factor", 1000))
        tolerance = float(parameter(STANDARD_TOLERANCE,
                                    "standard_tolerance", 0.1))
        instrument = mean([float(v) for v in reported]) * factor
        difference = abs(instrument - C_st) / C_st * 100 if C_st else 100.0
        check = {
            "instrument": instrument,
            "reported": mean([float(v) for v in reported]),
            "factor": factor,
            "expected": C_st,
            "difference": difference,
            "tolerance": tolerance,
            "passed": difference <= tolerance,
        }
        if not check["passed"]:
            raise StandardMismatch(check)
        C_st = instrument
    values.update({"C_st": C_st, "A_st": A_st})

    # 2-4. per injection and per unit
    units = []
    for index in range(0, len(samples), per_unit):
        rows = samples[index:index + per_unit]
        C_i = [float(r["area"]) * C_st / A_st for r in rows]
        weights = [r.get("weight") for r in rows if r.get("weight")]
        unit = dict(values)
        unit.update({
            "unidad": len(units) + 1,
            "A_u": mean([float(r["area"]) for r in rows]),
            "C_u": mean(C_i),
            "W_mue": weights and float(weights[0]) or None,
        })
        unit["cantidad"] = evaluate(model["amount"], unit, stage="amount")
        unit["resultado"] = evaluate(model["result"], unit, stage="result")
        units.append({
            "unidad": unit["unidad"],
            "injections": [r.get("number") for r in rows],
            "areas": [float(r["area"]) for r in rows],
            "C_i": C_i,
            "C_u": unit["C_u"],
            "W_mue": unit["W_mue"],
            "cantidad": unit["cantidad"],
            "resultado": unit["resultado"],
        })

    results = [u["resultado"] for u in units]
    output = {
        "C_st": C_st,
        "A_st": A_st,
        "rsd_st": stdev([float(r["area"]) for r in standards]) / A_st * 100,
        "preparations": preparations,
        "standard_check": check,
        "injections_per_unit": per_unit,
        "standard_injections_per_prep": per_prep,
        "derived": derived,
        "units": units,
        "mean": mean(results),
        "s": stdev(results),
        "aggregate": aggregate,
    }
    output["cv"] = output["s"] / output["mean"] * 100 if output["mean"] else 0
    if aggregate == UNIFORMITY:
        av, reference = acceptance_value(
            results, T=float(model.get("T", 100)), k=float(model.get("k", 2.4)))
        output.update({"result": av, "M": reference})
    elif aggregate == DISSOLUTION:
        Q = float(parameter(DISSOLUTION_Q, "Q", 75))
        output.update({
            "result": output["mean"],
            "Q": Q,
            "S1": all(r >= Q + 5 for r in results),
        })
    else:
        output["result"] = output["mean"]
    used = used_variables(model)
    for prep in preparations:
        suffix = "_{}".format(prep["preparacion"])
        used |= set(name for name in values if name.endswith(suffix))
    used |= set([SAMPLE_INJECTIONS, STANDARD_INJECTIONS,
                 STANDARD_FROM_INSTRUMENT, STANDARD_FACTOR,
                 STANDARD_TOLERANCE])
    if aggregate == DISSOLUTION:
        used.add(DISSOLUTION_Q)
    if preparations:
        used.discard("W_st")
    output["variables"] = dict(
        (name, values[name]) for name in used
        if values.get(name) is not None and name not in BUILTIN)
    return output


def used_variables(model):
    """Returns the variables used by the expressions of the model
    """
    found = set()
    for key in ("standard", "amount", "result"):
        if model.get(key):
            found |= names(model[key])
    for expression in (model.get("derived") or {}).values():
        found |= names(expression)
    return found
