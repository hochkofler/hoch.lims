# -*- coding: utf-8 -*-
"""Worked examples of the HPLC calculation model.

Data of cases 1-4 come from the release spreadsheet of ROSUVAST 20 mg soft
capsules, lot 52614L ("valoracion rosuvastatina.xlsx", sheet
92638-dosificado), and their expected values are the ones of that sheet.
The other cases reuse the same data to show how factors are inserted or
removed; their expected values come from the model itself.
"""

import copy

# Standard and sample preparation of the assay / content uniformity run
ASSAY_STANDARD_AREAS = [791854, 793043, 792758, 794814, 795462, 795634]
ASSAY_SAMPLE_AREAS = [825354, 826428, 818742, 820729, 822442, 819919,
                      810035, 807699, 822630, 825715, 814542, 815982,
                      821808, 821357, 818348, 818975, 802101, 802563,
                      807854, 809596]
# Weight of each soft capsule (column K), not used by the assay itself
ASSAY_UNIT_WEIGHTS = [671.51, 655.49, 669.06, 670.93, 663.11, 655.78,
                      655.43, 659.62, 655.22, 668.81]

DISSOLUTION_STANDARD_AREAS = [562757, 569308, 571012, 562949, 569002, 569433]
DISSOLUTION_SAMPLE_AREAS = [604791, 603703, 572566, 571062, 609250, 608122,
                            624815, 623801, 601626, 602734, 601734, 600256]


def injections(standard_areas, sample_areas, per_unit=2, weights=None):
    rows = []
    for number, area in enumerate(standard_areas, 1):
        rows.append({"type": "ST", "number": u"%02d" % number, "area": area})
    for number, area in enumerate(sample_areas, 1):
        row = {"type": "UNK", "number": u"%02d" % number, "area": area}
        unit = (number - 1) // per_unit
        if weights and number % per_unit == 1:
            row["weight"] = weights[unit]
        rows.append(row)
    return rows


# Sources of the variables, as they would be found in the LIMS
RUN = "run data"
PRODUCT = "product"
STANDARD_LOT = "standard lot"
ANALYSIS = "other analysis"

ASSAY_VARIABLES = {
    # run data (entered by the analyst)
    "W_st_1": (20.84, RUN),
    "W_st_2": (20.84, RUN),
    "agua_st": (4.251, RUN),
    # standard lot RSNR25006
    "P_st": (99.7, STANDARD_LOT),
    # product (once per product)
    "V_st": (50, PRODUCT),
    "D_st": (25, PRODUCT),
    "V_mue": (50, PRODUCT),
    "D_mue": (25, PRODUCT),
    "LC": (20, PRODUCT),
    "PM_st": (1001.14, PRODUCT),
    "PM_decl": (481.54, PRODUCT),
    "n_PM": (2, PRODUCT),
}

DERIVED = {
    "W_st": "mean(W_st_1, W_st_2)",
    "F_PM": "n_PM * PM_decl / PM_st",
}

ASSAY_MODEL = {
    "standard": "W_st * (1 - agua_st/100) * P_st/100 / (V_st * D_st) * 1000",
    "amount": "C_u * V_mue * D_mue / 1000",
    "result": "cantidad / LC * 100 * F_PM",
    "injections_per_unit": 2,
    "aggregate": "mean",
    "derived": DERIVED,
}


def variant(model=None, variables=None, drop=None, **changes):
    """Returns a copy of the assay model and variables with changes
    """
    new_model = copy.deepcopy(ASSAY_MODEL)
    new_model.update(changes)
    new_model.update(model or {})
    new_variables = dict(ASSAY_VARIABLES)
    new_variables.update(variables or {})
    for name in (drop or []):
        new_variables.pop(name, None)
    return new_model, new_variables


def case(key, title, description, model, variables, rows, expected,
         reference=None, source=u"Planilla 52614L", error=None):
    return {
        "key": key,
        "title": title,
        "description": description,
        "model": model,
        "variables": variables,
        "injections": rows,
        "expected": expected,
        "reference": reference,
        "source": source,
        "error": error,
    }


# A single model for every product: factors are switched on by product flags
UNIVERSAL_MODEL = {
    "standard": "W_st * (1 - si(usa_agua, agua_st, 0)/100) * P_st/100 / "
                "(V_st * D_st) * 1000",
    "amount": "C_u * V_mue * opcional(D_mue, 1) / 1000 * "
              "si(por_porcion, peso_prom / opcional(W_mue, 1), 1)",
    "result": "cantidad / LC * 100 * F_PM",
    "injections_per_unit": 2,
    "aggregate": "mean",
    "derived": {"F_PM": "si(usa_PM, n_PM * PM_decl / PM_st, 1)"},
}


def universal(flags, variables=None, drop=None):
    model = copy.deepcopy(UNIVERSAL_MODEL)
    new_variables = dict(ASSAY_VARIABLES)
    new_variables["W_st"] = (20.84, RUN)
    new_variables.pop("W_st_1")
    new_variables.pop("W_st_2")
    for name, value in flags.items():
        new_variables[name] = (value, PRODUCT)
    new_variables.update(variables or {})
    for name in (drop or []):
        new_variables.pop(name, None)
    return model, new_variables


# Universal model with dilutions as aliquot -> volumetric flask, the same
# expressions for assay, content uniformity and dissolution. Standard
# injections are grouped per preparation, each with its own weight.
UNIVERSAL_V2 = {
    "standard": "W_st * (1 - si(usa_agua, agua_st, 0)/100) * P_st/100 / V_st"
                " * V_alicuota_st / V_aforo_st * 1000",
    "amount": "C_u * V_mue * V_aforo_mue / V_alicuota_mue / 1000",
    "result": "cantidad / LC * 100 * F_PM",
    "injections_per_unit": 2,
    "standard_injections_per_prep": 3,
    "aggregate": "mean",
    "derived": {"F_PM": "si(usa_PM, n_PM * PM_decl / PM_st, 1)"},
}

# FLAMADIN PLUS soft capsules (paracetamol 500 mg + diclofenac sodium 50 mg),
# lot 82618, sheet "82618 NOTIFICACION 2026" of "TEST DE DISOLUCION.xlsx"
FLAMADIN = {
    "assay": {
        "PARACETAMOL": {
            "standard": [5011049, 5002213, 5000046, 5012810, 5012899, 5017703],
            "samples": [4919029, 4916611, 4839508, 4844432, 4875903, 4878808,
                        4879178, 4881011, 4887744, 4887098, 4809235, 4810215,
                        4898895, 4897669, 4832062, 4834988, 4889717, 4881697,
                        4894356, 4897300],
            "weights": [250.25, 250.25], "potency": 99.9, "LC": 500},
        "DICLOFENACO SODICO": {
            "standard": [1314873, 1312982, 1313487, 1299315, 1299096, 1299833],
            "samples": [1337351, 1335564, 1355031, 1355426, 1355860, 1357346,
                        1367351, 1368856, 1364051, 1365284, 1255887, 1256853,
                        1347482, 1347274, 1345019, 1346735, 1386838, 1385500,
                        1375853, 1377149],
            "weights": [25.13, 25.13], "potency": 99.5, "LC": 50},
    },
    "dissolution": {
        "PARACETAMOL": {
            "standard": [1201180, 1200994, 1197875, 1198350, 1198983, 1201147],
            "samples": [1158618, 1164979, 1194969, 1188144, 1162231, 1161777,
                        1155794, 1158074, 1186259, 1186930, 1160074, 1160510],
            "weights": [55.57, 55.57], "potency": 99.9, "LC": 500,
            "V_st": 50},
        "DICLOFENACO SODICO": {
            "standard": [308065, 308104, 307456, 307432, 308250, 308045],
            "samples": [318463, 318465, 322686, 329964, 320396, 320384,
                        318257, 319117, 328801, 328819, 319508, 319315],
            "weights": [11.17, 11.17], "potency": 99.5, "LC": 50,
            "V_st": 100},
    },
}

FLAMADIN_ASSAY_PARAMETERS = {"V_st": 50, "V_alicuota_st": 1.5,
                             "V_aforo_st": 25, "V_mue": 100,
                             "V_alicuota_mue": 1.5, "V_aforo_mue": 25}
FLAMADIN_DISSOLUTION_PARAMETERS = {"V_alicuota_st": 1, "V_aforo_st": 10,
                                   "V_mue": 900, "V_alicuota_mue": 2,
                                   "V_aforo_mue": 10, "Q": 70}


def flamadin(test, active, aggregate="mean", drop=None):
    data = FLAMADIN[test][active]
    model = copy.deepcopy(UNIVERSAL_V2)
    model["aggregate"] = aggregate
    variables = {"usa_agua": (0, PRODUCT), "usa_PM": (0, PRODUCT),
                 "n_iny_st": (3, PRODUCT), "n_iny_mue": (2, PRODUCT),
                 "LC": (data["LC"], PRODUCT), "P_st": (data["potency"], RUN)}
    parameters = FLAMADIN_ASSAY_PARAMETERS if test == "assay" \
        else dict(FLAMADIN_DISSOLUTION_PARAMETERS, V_st=data["V_st"])
    for name, value in parameters.items():
        variables[name] = (value, PRODUCT)
    for number, weight in enumerate(data["weights"], 1):
        variables["W_st_{}".format(number)] = (weight, RUN)
    for name in (drop or []):
        variables.pop(name, None)
    return model, variables, injections(data["standard"], data["samples"])


def get_cases():
    assay_rows = injections(ASSAY_STANDARD_AREAS, ASSAY_SAMPLE_AREAS,
                            weights=ASSAY_UNIT_WEIGHTS)
    dissolution_rows = injections(DISSOLUTION_STANDARD_AREAS,
                                  DISSOLUTION_SAMPLE_AREAS)
    illustrative = u"Variante sobre los datos de la planilla 52614L"
    cases = []

    model, variables = variant()
    cases.append(case(
        "valoracion", u"1. Valoración de Rosuvastatina (% del declarado)",
        u"Estándar de rosuvastatina cálcica corregido por agua y potencia; "
        u"resultado como rosuvastatina base (factor de peso molecular).",
        model, variables, assay_rows, 98.427166, reference=u"Celda L64"))

    model, variables = variant(aggregate="uniformity", T=100, k=2.4)
    cases.append(case(
        "uniformidad", u"2. Uniformidad de contenido (valor de aceptación)",
        u"Mismo modelo y mismos datos que la valoración; cambia solo el "
        u"agregado. La planilla tiene 14.9 escrito a mano en E54.",
        model, variables, assay_rows, 2.294124,
        reference=u"Calculado con L64 y L65 (E54 está escrito a mano)"))

    model, variables = variant(aggregate="mean", result="cantidad * F_PM")
    cases.append(case(
        "mg_unidad", u"3. Resultado en mg por unidad",
        u"Misma corrida; el resultado se expresa en mg de rosuvastatina "
        u"base por cápsula en lugar de % del declarado.",
        model, variables, assay_rows, 19.685433, reference=u"Celda N62"))

    model, variables = variant(
        model={
            "standard": "W_st * (1 - agua_st/100) * P_st/100 / "
                        "(V_st * D_st) * 1000",
            "amount": "C_u * V_medio * (V_aforo / V_alicuota) / 1000",
            "aggregate": "dissolution",
            "Q": 75,
            "derived": dict(DERIVED),
        },
        variables={
            "W_st_1": (57.95, RUN), "W_st_2": (57.92, RUN),
            "V_st": (100, PRODUCT), "D_st": (50, PRODUCT),
            "V_medio": (900, PRODUCT), "V_alicuota": (5, PRODUCT),
            "V_aforo": (10, PRODUCT),
            "valoracion.agua_st": (4.251, ANALYSIS),
        },
        drop=["V_mue", "D_mue"])
    model["standard"] = model["standard"].replace(
        "agua_st", "valoracion.agua_st")
    variables.pop("agua_st")
    cases.append(case(
        "disolucion", u"4. Disolución (6 vasos, etapa S1)",
        u"Mismo modelo con otra cantidad por unidad (medio de 900 mL, "
        u"alícuota de 5 mL llevada a 10 mL). El agua se toma de la "
        u"valoración de la misma muestra.",
        model, variables, dissolution_rows, 101.610246,
        reference=u"Celda L149"))

    model, variables = variant(
        standard="W_st * (1 - agua_st) * P_st/100 / (V_st * D_st) * 1000",
        variables={"agua_st": (0.04251, RUN)})
    cases.append(case(
        "agua_fraccion", u"5. Agua cargada como fracción",
        u"El método escribe el agua como fracción (0.04251) en lugar de %; "
        u"solo cambia la expresión del estándar. Mismo resultado que el "
        u"caso 1.",
        model, variables, assay_rows, 98.427166, source=illustrative))

    model, variables = variant(
        standard="W_st * P_st/100 / (V_st * D_st) * 1000", drop=["agua_st"])
    cases.append(case(
        "sin_agua", u"6. Sin corrección por agua",
        u"Quitando el factor de agua de la expresión del estándar. Muestra "
        u"cuánto pesa la corrección (unos 4.4 puntos).",
        model, variables, assay_rows, 102.797070, source=illustrative))

    model, variables = variant(result="cantidad / LC * 100")
    cases.append(case(
        "sin_pm", u"7. Sin conversión por peso molecular",
        u"Para un estándar en la misma forma que el declarado (por ejemplo "
        u"una base contra una base): se quita F_PM del resultado.",
        model, variables, assay_rows, 102.316914, source=illustrative))

    model, variables = variant(
        result="cantidad / LC * 100 * F_PM * pureza/100",
        variables={"pureza": (99.5, STANDARD_LOT)})
    cases.append(case(
        "factor_extra", u"8. Insertar un factor nuevo (pureza 99.5 %)",
        u"Se agrega «* pureza/100» al resultado y se define de dónde sale "
        u"pureza. No requiere programar nada.",
        model, variables, assay_rows, 97.935031, source=illustrative))

    model, variables = variant(result="cantidad * F_PM / (W_mue / 1000)")
    cases.append(case(
        "mg_g", u"9. Resultado en mg/g",
        u"Usa la pesada de cada unidad (columna K) para expresar mg de "
        u"rosuvastatina base por g de contenido.",
        model, variables, assay_rows, 29.716728, source=illustrative))

    model, variables = variant(drop=["agua_st"])
    cases.append(case(
        "falta_agua", u"10. Falta el agua del estándar",
        u"Si el analista no carga el agua, el sistema no calcula y dice "
        u"qué falta, en lugar de asumir 0.",
        model, variables, assay_rows, None, source=illustrative,
        error=u"agua_st"))

    universal_title = u"Modelo universal"
    model, variables = universal({"usa_agua": 1, "usa_PM": 1, "por_porcion": 0})
    cases.append(case(
        "universal_rosuvastatina",
        u"11. Modelo universal: Rosuvastatina (agua y PM activos)",
        u"La misma Calculation sirve para todos los productos. Este producto "
        u"declara usa_agua = 1 y usa_PM = 1; da lo mismo que el caso 1.",
        model, variables, assay_rows, 98.427166, reference=u"Celda L64",
        source=universal_title))

    model, variables = universal({"usa_agua": 0, "usa_PM": 0, "por_porcion": 0},
                                 drop=["agua_st", "PM_st", "PM_decl", "n_PM"])
    cases.append(case(
        "universal_sin_factores",
        u"12. Modelo universal: producto sin agua ni PM",
        u"El producto declara usa_agua = 0 y usa_PM = 0: no hace falta "
        u"cargar agua ni pesos moleculares y esos factores valen 1.",
        model, variables, assay_rows, 106.859512, source=universal_title))

    model, variables = universal({"usa_agua": 1, "usa_PM": 1, "por_porcion": 0},
                                 drop=["agua_st"])
    cases.append(case(
        "universal_falta_agua",
        u"13. Modelo universal: el producto usa agua y falta el dato",
        u"Con usa_agua = 1 el agua pasa a ser obligatoria: si no se carga, "
        u"no calcula. Un factor activo nunca se reemplaza por su valor "
        u"neutro.",
        model, variables, assay_rows, None, source=universal_title,
        error=u"agua_st"))

    model, variables = universal(
        {"usa_agua": 1, "usa_PM": 1, "por_porcion": 1},
        variables={"peso_prom": (662.496, PRODUCT)})
    cases.append(case(
        "universal_porcion",
        u"14. Modelo universal: muestra por porción pesada",
        u"Con por_porcion = 1 la cantidad se lleva a la unidad con el peso "
        u"promedio (aquí 662.496 mg, el promedio de la columna K) y la "
        u"pesada de cada unidad.",
        model, variables, assay_rows, 98.436066, source=universal_title))

    source = u"Planilla FLAMADIN PLUS 82618"
    model = copy.deepcopy(UNIVERSAL_V2)
    variables = dict(ASSAY_VARIABLES)
    for name in ("D_st", "D_mue"):
        variables.pop(name)
    variables.update({
        "V_alicuota_st": (1, PRODUCT), "V_aforo_st": (25, PRODUCT),
        "V_alicuota_mue": (1, PRODUCT), "V_aforo_mue": (25, PRODUCT),
        "usa_agua": (1, PRODUCT), "usa_PM": (1, PRODUCT),
        "n_iny_st": (3, PRODUCT), "n_iny_mue": (2, PRODUCT)})
    cases.append(case(
        "v2_rosuvastatina", u"15. Universal v2: Rosuvastatina",
        u"Diluciones como alícuota y aforo, y 2 preparaciones de estándar "
        u"de 3 inyecciones, cada una con su pesada. Mismo resultado que el "
        u"caso 1.",
        model, variables, assay_rows, 98.427166, reference=u"Celda L64"))

    for key, title, test, active, aggregate, expected, ref in (
            ("flamadin_val_para", u"16. Flamadin: valoración Paracetamol",
             "assay", "PARACETAMOL", "mean", 97.271451, u"Celda J73"),
            ("flamadin_uc_para", u"17. Flamadin: uniformidad Paracetamol",
             "assay", "PARACETAMOL", "uniformity", 2.836051,
             u"E53 = 2.8 (escrito a mano)"),
            ("flamadin_val_diclo", u"18. Flamadin: valoración Diclofenaco",
             "assay", "DICLOFENACO SODICO", "mean", 103.288894, u"Celda L73"),
            ("flamadin_uc_diclo", u"19. Flamadin: uniformidad Diclofenaco",
             "assay", "DICLOFENACO SODICO", "uniformity", 8.382690,
             u"E55 = 8.4 (escrito a mano)"),
            ("flamadin_dis_para", u"20. Flamadin: disolución Paracetamol",
             "dissolution", "PARACETAMOL", "dissolution", 97.436344,
             u"Celda L161"),
            ("flamadin_dis_diclo", u"21. Flamadin: disolución Diclofenaco",
             "dissolution", "DICLOFENACO SODICO", "dissolution", 104.615467,
             u"La planilla informa 105.094109 con la concentración del "
             u"estándar escrita a mano y sin aplicar la potencia")):
        model, variables, rows = flamadin(test, active, aggregate)
        cases.append(case(key, title, u"Mismo modelo universal; cambian el "
                          u"agregado y los parámetros del servicio.",
                          model, variables, rows, expected, reference=ref,
                          source=source))

    model, variables, rows = flamadin("assay", "PARACETAMOL",
                                      drop=["W_st_2"])
    cases.append(case(
        "falta_pesada", u"22. Falta la pesada de la preparación 2",
        u"Con 2 preparaciones de estándar, cada una necesita su pesada: si "
        u"falta una, no calcula.",
        model, variables, rows, None, source=source, error=u"W_st_2"))

    return cases


def values_of(variables):
    return dict((name, value) for name, (value, source)
                in variables.items())
