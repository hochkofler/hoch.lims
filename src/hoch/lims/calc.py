# -*- coding: utf-8 -*-
from bika.lims import api
from bika.lims.api.analysis import is_reference_analysis
from hoch.lims import logger
from hoch.lims.utils import is_interim_editable
from Products.statusmessages.interfaces import IStatusMessage
from zope.globalrequest import getRequest
from hoch.lims.utils import compute_variables_dict
import math
from zope import event
from Products.Archetypes.event import ObjectEditedEvent
from hoch.lims import messageFactory as _


def show_message(msg, msg_type="error"):
    """Muestra un mensaje en la UI"""
    request = getRequest()
    if request:
        IStatusMessage(request).addStatusMessage(msg, type=msg_type)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class CalculationError(Exception):
    """Base exception for all hoch.lims calculation errors"""


class LALCalculationError(CalculationError):
    """Excepción personalizada para errores en el cálculo de LAL"""


class MicrobialAssaysCalculationError(CalculationError):
    """Excepción personalizada para errores en el cálculo de Microbial Assays"""


class MicrobialAssaysPrepCalculationError(CalculationError):
    """Excepción personalizada para errores en el cálculo de preparación microbiológica"""


class DensityCalculationError(CalculationError):
    """Excepción personalizada para errores en el cálculo de densidad"""


# ---------------------------------------------------------------------------
# BaseCalculator
# ---------------------------------------------------------------------------

class BaseCalculator(object):
    """Infrastructure base for all HOCH.LIMS analysis calculators.

    Provides:
    - Resolving analysis from UID/brain
    - Lazy-loaded interim fields with cache invalidation
    - Getting / setting individual interim values by keyword
    - Fetching dependencies by keyword
    - Standardised error reporting (UI message + exception)
    """

    #: Subclasses override this to use a more specific exception type
    error_class = CalculationError

    def __init__(self, analysis_brain_uid):
        self.analysis = api.get_object(analysis_brain_uid)
        self._interim_fields = None

    # ------------------------------------------------------------------
    # Interim field access
    # ------------------------------------------------------------------

    @property
    def interim_fields(self):
        """Return the list of interim field dicts, loading once per instance."""
        if self._interim_fields is None:
            self._interim_fields = api.safe_getattr(
                self.analysis, "getInterimFields", []
            )
        return self._interim_fields

    def reload_interims(self):
        """Force a fresh fetch of interim fields from the analysis object."""
        self._interim_fields = None

    def get_interim(self, keyword):
        """Return the interim dict whose 'keyword' matches, or None."""
        return next(
            (i for i in self.interim_fields if i.get("keyword") == keyword),
            None
        )

    def get_interim_value(self, keyword, default=None, as_float=False):
        """Return the value of an interim field by keyword.

        :param keyword: interim keyword
        :param default: value returned when interim not found or empty
        :param as_float: coerce to float via api.to_float when True
        """
        interim = self.get_interim(keyword)
        if interim is None:
            return default
        raw = interim.get("value", default)
        if as_float:
            if raw in (None, "", "None"):
                return default
            return api.to_float(raw, default)
        return raw

    @staticmethod
    def parse_time_to_seconds(value):
        """Convert duration strings to total seconds.

        Accepts "MM:SS" or "HH:MM:SS" and returns float seconds.
        """
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        parts = text.split(":")
        if len(parts) not in (2, 3):
            raise ValueError("Invalid time format, expected MM:SS or HH:MM:SS")

        try:
            parts = [float(p) for p in parts]
        except ValueError:
            raise ValueError("Time parts must be numeric")

        if len(parts) == 2:
            minutes, seconds = parts
            return minutes * 60.0 + seconds
        hours, minutes, seconds = parts
        return hours * 3600.0 + minutes * 60.0 + seconds

    def get_interim_time_seconds(self, keyword, default=None):
        """Read a time interim in MM:SS/HH:MM:SS and return total seconds."""
        raw = self.get_interim_value(keyword, default=None)
        if raw in (None, "", "None"):
            return default
        try:
            return self.parse_time_to_seconds(raw)
        except ValueError:
            self._raise("Interval '{}' value '{}' is not valid time".format(keyword, raw))
            return default

    def set_interim_value(self, keyword, value, overwrite=True):
        """Set the value of one interim field by keyword and persist.

        Only writes if the interim is editable (analysis not verified/locked).
        If overwrite=False, skips fields that already have a non-empty value.

        Returns True if the field was found and written, False otherwise.
        """
        for interim in self.interim_fields:
            if interim.get("keyword") != keyword:
                continue
            if not is_interim_editable(interim):
                return False
            if not overwrite and interim.get("value") not in (None, "", "0", 0):
                return False
            interim["value"] = str(value)
            self.analysis.setInterimFields(self.interim_fields)
            return True
        return False

    def set_interim_values(self, mapping, overwrite=True):
        """Set multiple interim values in a single pass, persisting once.

        Only writes interims that are editable (analysis not verified/locked).
        If overwrite=False, skips fields that already have a non-empty value.

        :param mapping: dict of {keyword: value}
        :param overwrite: if False, skip fields that already have a value
        """
        written = False
        for interim in self.interim_fields:
            kw = interim.get("keyword")
            if kw not in mapping:
                continue
            if not is_interim_editable(interim):
                continue
            if not overwrite and interim.get("value") not in (None, "", "0", 0):
                continue
            interim["value"] = str(mapping[kw])
            written = True
        if written:
            self.analysis.setInterimFields(self.interim_fields)

    # ------------------------------------------------------------------
    # Dependency access
    # ------------------------------------------------------------------

    def get_dependencies(self):
        """Return list of dependency analysis objects."""
        return self.analysis.getDependencies()

    def get_dependency_by_keyword(self, keyword):
        """Return the first dependency whose getKeyword() matches, or None."""
        return next(
            (dep for dep in self.get_dependencies()
             if dep.getKeyword() == keyword),
            None
        )

    # ------------------------------------------------------------------
    # Validation / error reporting
    # ------------------------------------------------------------------

    def _raise(self, message):
        """Show message in UI and raise self.error_class."""
        show_message(str(message))
        raise self.error_class(str(message))

    def require(self, value, message):
        """Raise CalculationError if value is falsy.

        Returns value so it can be used inline:
            x = self.require(some_call(), "msg")
        """
        if not value:
            self._raise(message)
        return value

    def validate(self, condition, message):
        """Raise CalculationError if condition is False."""
        if not condition:
            self._raise(message)


# ---------------------------------------------------------------------------
# LALCalculator
# ---------------------------------------------------------------------------

class LALCalculator(BaseCalculator):
    """Clase dedicada al cálculo de LAL con responsabilidades separadas"""

    error_class = LALCalculationError

    def __init__(self, analysis_brain_uid):
        super(LALCalculator, self).__init__(analysis_brain_uid)
        self.sample = api.safe_getattr(self.analysis, "getRequest", None)

    def get_sensitivity(self):
        """Obtener sensibilidad de los análisis QC"""
        LAL_KEYWORD_QC = "Reactivo LAL"
        analysis_qcs = self.sample.getQCAnalyses() if self.sample else None
        self.require(analysis_qcs, _("No QCs found for analysis %s" % self.analysis.UID()))

        valid_qc = None
        for qc in analysis_qcs:
            rd = qc.getReferenceDefinition()
            if not rd:
                continue
            if rd.Title() == LAL_KEYWORD_QC:
                valid_qc = qc
                break

        self.require(
            valid_qc,
            _("Not valid qcs with reference definition '%s'" % LAL_KEYWORD_QC)
        )

        variables = getattr(valid_qc, 'VariablesSettings', [])
        self.require(
            variables,
            _("Variables for qc analysis not set for qc '%s'" % analysis_qcs)
        )

        sensitivity = next(
            (var["value"] for var in variables if var["keyword"] == "sensitivity"),
            None
        )
        self.require(
            sensitivity,
            _("No sensitivity found for analysis %s" % self.analysis.UID())
        )
        return api.to_float(sensitivity, 0)

    def get_concentration_and_dilution(self):
        """Obtener concentración y dilución de la matriz de muestra"""
        samplematrix = self.sample.getSampleType().getSampleMatrix() if self.sample else None
        self.require(samplematrix, _("Sample matrix not found"))

        dict_variables = compute_variables_dict(samplematrix)
        concentration_raw = dict_variables.get('LAL', {}).get('concentration')
        dilution_raw = dict_variables.get('LAL', {}).get('dilution', (1, 'mL'))

        self.require(
            concentration_raw,
            _("Concentration not found in sample matrix variables, actual sample matrices "
              "for samplematrix '%s' are: '%s'" % (samplematrix, dict_variables))
        )

        logger.info("Este es concentracion '%s' y dilution '%s'", concentration_raw, dilution_raw)
        return concentration_raw[0], dilution_raw[0], concentration_raw[1], dilution_raw[1]

    def calculate_reference_analysis(self):
        """Calcular para análisis de referencia"""
        for interim in self.interim_fields:
            if not is_interim_editable(interim):
                continue
            if interim.get("keyword", "") == "d1":
                result = api.to_float(interim.get("value"), -1)
                if result == -1:
                    return None
                return 1 if result > 0 else 0

        self._raise(_("Reference Sample not valid interim (d1)"))

    def calculate_regular_analysis(self, sensitivity):
        """Calcular para análisis regular"""
        logger.info("Calculating regular analysis of LAL calc")
        result_range = api.safe_getattr(self.analysis, "getResultsRange", None)
        if not result_range:
            return 0

        specs_lim = max(
            api.to_float(getattr(result_range, 'max', 0), 0),
            api.to_float(getattr(result_range, 'min', 0), 0)
        )

        conc, dilution, conc_unit, dilution_unit = self.get_concentration_and_dilution()
        logger.info(
            "Data for LAL Calc--->conc:='%s'---dilution:='%s'---sensitivity:='%s'",
            conc, dilution, sensitivity
        )

        mdv = (specs_lim * conc) / (sensitivity * dilution) if sensitivity and dilution else 0

        # Update simple interim values in a single pass first
        simple_updates = {
            "mdv": str(mdv),
            "sensitivity": str(sensitivity),
        }

        max_dilution = 0
        for interim in self.interim_fields:
            if not is_interim_editable(interim):
                continue

            keyword = interim.get("keyword", "")
            value = interim.get("value", "")

            if keyword in simple_updates:
                interim["value"] = simple_updates[keyword]

            elif keyword == "concentration":
                interim["value"] = str(conc)
                interim["unit"] = conc_unit

            elif keyword == "dilution":
                interim["value"] = str(dilution)
                interim["unit"] = dilution_unit

            elif keyword == "dmdv" and value not in [None, "", 0, "0"]:
                interim["value"] = str(mdv)

            elif keyword.startswith("d") and len(keyword) > 1:
                try:
                    dilution_key_number = api.to_float(keyword[1:], 1)
                    current_value = api.to_float(value, 1)
                    max_dilution = max(max_dilution, current_value)
                    interim["allow_empty"] = "on" if dilution_key_number > mdv else "off"
                except ValueError:
                    logger.error("Invalid interim field value: %s", value)

        self.analysis.setInterimFields(self.interim_fields)

        logger.info(
            "Data for LAL Calc--->mdv:='%s'---max dilution:='%s'", mdv, max_dilution
        )
        result_ue_ml = max_dilution * sensitivity
        result_ue_mg = result_ue_ml * dilution / conc if conc else 0
        return result_ue_mg

    def calculate(self):
        """Método principal para realizar el cálculo"""
        sensitivity = self.get_sensitivity()
        if is_reference_analysis(self.analysis):
            return self.calculate_reference_analysis()
        return self.calculate_regular_analysis(sensitivity)


# ---------------------------------------------------------------------------
# MicrobialAssaysCalculator
# ---------------------------------------------------------------------------

class MicrobialAssaysCalculator(BaseCalculator):
    """Clase dedicada al cálculo de Ensayos Microbianos con responsabilidades separadas"""

    error_class = MicrobialAssaysCalculationError

    DEPENDENCIES_SERVICES_KEY_M = ('DIAMETRO_HALO_M1', 'DIAMETRO_HALO_M2', 'DIAMETRO_HALO_M3')
    DEPENDENCIES_SERVICES_KEY_ST = ('DIAMETRO_HALO_ST1', 'DIAMETRO_HALO_ST2', 'DIAMETRO_HALO_ST3')
    DEPENDENCIES_SERVICES_KEYS = DEPENDENCIES_SERVICES_KEY_ST + DEPENDENCIES_SERVICES_KEY_M
    DIAMETER_KEYS = ['diameter_plate1', 'diameter_plate2']
    CONCENTRATION_ANALYSIS = ['ST']
    REQUIRED_QC_KEYS = ('ST', 'ORGANISM')
    ALLOWED_EDITABLE_STATUS = ["to_be_verified", "verified", "published"]

    def __init__(self, analysis_brain_uid):
        super(MicrobialAssaysCalculator, self).__init__(analysis_brain_uid)
        self.sample = api.safe_getattr(self.analysis, "getRequest", None)
        self.qc_analyses = self.sample.getQCAnalyses() if self.sample else []

    def get_diameters(self):
        """Get diameter from QC analyses"""
        dependencies = self.get_dependencies()
        dependencies_keys = [a.getKeyword() for a in dependencies]

        self.validate(
            all(key in dependencies_keys for key in self.DEPENDENCIES_SERVICES_KEYS),
            _("Missing value dependencies in analysis %s" % self.analysis.UID())
        )

        self.valid_qc_analyses = [
            qc for qc in self.qc_analyses if qc.getKeyword() in self.REQUIRED_QC_KEYS
        ]
        valid_dependencies = [
            dep for dep in dependencies if dep.getKeyword() in self.DEPENDENCIES_SERVICES_KEYS
        ]

        self.dependencies_diameters_m = []
        self.dependencies_diameters_st = []
        for dep in valid_dependencies:
            for interim in dep.getInterimFields():
                if interim.get("keyword") in self.DIAMETER_KEYS:
                    diameter_value = api.to_float(interim.get("value", 0), 0)
                    if diameter_value > 0:
                        if dep.getKeyword() in self.DEPENDENCIES_SERVICES_KEY_M:
                            self.dependencies_diameters_m.append(diameter_value)
                        elif dep.getKeyword() in self.DEPENDENCIES_SERVICES_KEY_ST:
                            self.dependencies_diameters_st.append(diameter_value)

    def get_reference_concentration(self):
        """Get reference concentration from qc analysis"""
        self.require(
            self.qc_analyses,
            _("No QC analyses found for analysis %s" % self.analysis.UID())
        )

        reference_sample = next(
            (qc.getSample() for qc in self.qc_analyses
             if qc.getKeyword() in self.CONCENTRATION_ANALYSIS),
            None
        )
        self.require(
            reference_sample,
            _("No QC analyses found to get concentration for analysis %s" % self.analysis.UID())
        )

        self.reference_concentration = api.to_float(
            api.safe_getattr(reference_sample, "getConcentration", lambda: 1)(), 1
        )
        return self.reference_concentration

    def get_water_content_factor(self):
        """Get water content factor"""
        self.water_factor = self.get_interim_value("humedad", default=0, as_float=True)
        return self.water_factor

    def set_interim_fields(self):
        """Set interim fields with calculated values"""
        is_qc_analyses_editable = [
            api.get_workflow_status_of(qc) not in self.ALLOWED_EDITABLE_STATUS
            for qc in self.valid_qc_analyses
        ]

        if any(is_qc_analyses_editable):
            logger.info(
                "Some interim fields in QC analyses are editable, skipping setting interim fields"
            )
            return

        self.set_interim_value("st_concentration", self.reference_concentration)

    def calculate(self):
        """Método principal para realizar el cálculo de Ensayos Microbianos"""
        self.get_diameters()
        sum_dependencies_diameters_st = sum(self.dependencies_diameters_st)
        sum_dependencies_diameters_m = sum(self.dependencies_diameters_m)

        self.validate(
            sum_dependencies_diameters_st and sum_dependencies_diameters_m,
            _("Sum of dependency diameters is zero for analysis %s" % self.analysis.UID())
        )

        concentration = self.get_reference_concentration()
        unit = self.analysis.getUnit()
        unit_factor = 100 if unit == "%" else 1
        water_content = self.get_water_content_factor()
        result = (
            sum_dependencies_diameters_m / sum_dependencies_diameters_st
            * unit_factor * concentration * (1 - water_content / 100)
        )
        return result


# ---------------------------------------------------------------------------
# MicrobialAssaysPrepCalculator  (NEW)
# ---------------------------------------------------------------------------

class MicrobialAssaysPrepCalculator(BaseCalculator):
    """Calculator for microbial assay preparation (standard dilution and
    real concentration validation).

    Business logic:
    - potencia_ref: potency of the reference standard (auto-filled from
      consumable). Raises an error if missing.
    - volumen_aforo: predefined dilution/volumetric factor.
    - conc_obj: obtained from the first consumable assigned to the analysis
      via getConsumablesFields()[0].getConcentration().
    - peso_objetivo: computed as conc_obj * volumen_aforo / potencia_ref
      and written to the 'peso_objetivo' interim field.
    - conc_real: computed as (rep_01+rep_02+rep_03)/3 * potencia_ref / volumen_aforo.
      Validated to be within `tolerance` of conc_obj.
    - Final result: average of halo_p1_1..halo_p2_3 passed as **kwargs.
    """

    error_class = MicrobialAssaysPrepCalculationError

    HALO_KEYS = [
        "halo_p1_1", "halo_p1_2", "halo_p1_3",
        "halo_p2_1", "halo_p2_2", "halo_p2_3",
    ]

    def get_reference_concentration(self):
        """Resolve the reference concentration from the consumable's reference sample.

        Path: analysis.getConsumablesFields()[0]["value"] (UID)
              → api.get_object_by_uid(uid)
              → obj.VariablesSettings
              → entry with keyword="concentration"

        Sets the 'potencia_ref' interim field (value + unit) as a side effect.
        Returns the float concentration value, or None if not yet assigned.
        """
        consumables = api.safe_getattr(self.analysis, "getConsumablesFields", [])
        logger.info("[MicroPrep] consumables raw='%s'", consumables)

        if not consumables:
            logger.info("[MicroPrep] get_reference_concentration SKIP — sin consumibles")
            return None

        reference_sample_uid = consumables[0].get("value", "") if consumables[0] else ""
        if not reference_sample_uid:
            logger.info("[MicroPrep] get_reference_concentration SKIP — consumable sin muestra asignada")
            return None

        reference_sample = api.get_object_by_uid(reference_sample_uid, None)
        if not reference_sample:
            logger.info("[MicroPrep] get_reference_concentration SKIP — UID '%s' no resuelve objeto",
                        reference_sample_uid)
            return None

        variables = getattr(reference_sample, "VariablesSettings", [])
        logger.info("[MicroPrep] reference_sample='%s' VariablesSettings=%s",
                    reference_sample_uid, variables)

        conc_entry = next(
            (v for v in variables if v.get("keyword") == "concentration"), None
        )
        if not conc_entry:
            logger.info("[MicroPrep] get_reference_concentration SKIP — 'concentration' no encontrada en VariablesSettings")
            return None

        value_raw = conc_entry.get("value", "")
        unit = conc_entry.get("unit", "")

        if value_raw in (None, "", "None"):
            logger.info("[MicroPrep] get_reference_concentration SKIP — concentration value vacio")
            return None

        conc = api.to_float(value_raw, 0)
        logger.info("[MicroPrep] concentration='%s' unit='%s'", conc, unit)

        # Write potencia_ref interim (value + unit) — auto-populated, skip editability check
        for interim in self.interim_fields:
            if interim.get("keyword") == "potencia_ref":
                interim["value"] = str(conc)
                interim["unit"] = unit
                logger.info("[MicroPrep] potencia_ref interim actualizado: value='%s' unit='%s'", conc, unit)
                break
        self.analysis.setInterimFields(self.interim_fields)

        return conc, unit

    def calculate_peso_objetivo(self, conc_obj, volumen_aforo, potencia_ref, conversion_factor=1):
        """Compute target weight and write it to the 'peso_objetivo' interim."""
        peso = conc_obj * volumen_aforo / potencia_ref * conversion_factor
        logger.info("[MicroPrep] calculate_peso_objetivo conc_obj='%s' volumen_aforo='%s' potencia_ref='%s' conversion_factor='%s' => peso_objetivo='%s'",
                    conc_obj, volumen_aforo, potencia_ref, conversion_factor, peso)
        self.set_interim_value("peso_objetivo", peso)
        return peso

    def calculate_conc_real(self, rep_01, rep_02, rep_03, potencia_ref, volumen_aforo, conversion_factor=1, peso_objetivo=None):
        """Compute real concentration from three replicates."""
        avg_rep = (rep_01 + rep_02 + rep_03) / 3.0
        
        return avg_rep * potencia_ref / volumen_aforo / conversion_factor

    def validate_conc_real(self, conc_real, conc_obj, tolerance):
        """Validate that conc_real is within tolerance fraction of conc_obj."""
        self.validate(conc_obj != 0, _("Objective concentration cannot be zero"))
        deviation = abs(conc_real - conc_obj) / conc_obj
        self.validate(
            deviation <= tolerance,
            _("Real concentration %.4f deviates %.2f%% from objective %.4f "
              "(max allowed: %.0f%%)" % (
                  conc_real,
                  deviation * 100,
                  conc_obj,
                  tolerance * 100,
              ))
        )

    def calculate_halo_average(self, kwargs):
        """Compute the average of the six halo measurement kwargs.

        Returns None if any halo value is missing or zero.
        """
        values = []
        for key in self.HALO_KEYS:
            raw = kwargs.get(key)
            if raw in (None, "", "None"):
                continue
            val = api.to_float(raw, 0)
            if val > 0:
                values.append(val)

        if len(values) != len(self.HALO_KEYS):
            logger.info(
                "[MicroPrep] Halos incompletos: se esperan %d, hay %d validos. "
                "Resultado final no calculado aun.",
                len(self.HALO_KEYS), len(values)
            )
            return None
        return sum(values) / len(values)
    
    def get_conc_obj_from_dependant_condition(self, analysis=None, keyword="concentracion_s3"):
        """Attempt to get conc_obj from the first consumable assigned to the analysis.
        """
        dependants = analysis.getDependents()
        if not dependants:
            logger.info("[MicroPrep] get_conc_obj_from_dependant_condition SKIP — analysis sin dependientes")
            return None
        dependant = dependants[0]
        conditions = api.safe_getattr(dependant, "getConditions", [])
        if not conditions:
            logger.info("[MicroPrep] get_conc_obj_from_dependant_condition SKIP — analysis sin condiciones")
            logger.info("[MicroPrep] dependientes disponibles: %s", [d.UID() for d in dependants])
            return None
        condition = next((c for c in conditions if c.get("title") == keyword), None)
        if not condition:
            logger.info("[MicroPrep] get_conc_obj_from_dependant_condition SKIP — no se encuentra condition con keyword '%s'", keyword)
            logger.info("[MicroPrep] conditions disponibles: %s", conditions)
        return condition.get("value", None) if condition else None

    def standardize_unit(self, unit_raw):
        """Standardize unit strings to a common format for conversion.

        For example, "mg/mL", "MG/ML", "mg/ml" would all be standardized to "MG/ML".
        """
        if not unit_raw:
            return u""
        if isinstance(unit_raw, bytes):
            unit_raw = unit_raw.decode("utf-8")
        unit = unit_raw.replace(u"µ", u"U")  # replace micro symbol with 'U' for easier matching
        unit = unit.replace(u" ", u"")
        unit = unit.strip().upper()
        replacements = {
            u"MG/ML": [u"MG/ML"],
            u"UG/ML": [u"UG/ML", u"UG/ML"],
            u"NG/ML": [u"NG/ML", u"NG/ML"],
            u"G/MG": [u"G/MG"],
            u"MG/G": [u"MG/G"],
            u"UG/MG": [u"UG/MG"],
            u"%": [u"%"],
        }
        
        for standard, variants in replacements.items():
            if unit in variants:
                logger.info("[MicroPrep] Unidad '%s' estandarizada a '%s'", unit_raw, standard)
                return standard
        logger.info("[MicroPrep] Unidad '%s' no reconocida en standardize_unit, se devuelve sin cambios, '%s' -> '%s'", unit_raw, unit_raw, unit)
        return unit
    
    def run(self, tolerance=0.02, type="standard", **kwargs):
        """Orchestrate the full preparation calculation.

        All input values are read directly from the analysis interim fields.
        Runs in stages — each stage is skipped (not errored) if its inputs
        are not yet filled:
        
        Stage 1 — peso_objetivo: requires potencia_ref + volumen_aforo + consumable conc_obj
        Stage 2 — conc_real validation: requires rep_01, rep_02, rep_03
        Stage 3 — final result: requires all six halo measurements
        """
        
        # Stage 1: get potencia_ref from consumable + calculate peso_objetivo
        # get_reference_concentration also writes potencia_ref interim (value + unit)
        if type == "standard":
            potencia_ref, potencia_ref_unit = self.get_reference_concentration()
        else:
            potencia_ref_intrim = self.get_interim("potencia_ref")
            if potencia_ref_intrim is not None:
                potencia_ref = potencia_ref_intrim.get("value", None)
                potencia_ref_unit = potencia_ref_intrim.get("unit", "")
            else:
                potencia_ref = None
                potencia_ref_unit = ""
        
        volumen_aforo = self.get_interim_value("volumen_aforo", default=None, as_float=True)

        logger.info(
            "[MicroPrep] Stage 1 — potencia_ref='%s' volumen_aforo='%s' | halos=%s",
            potencia_ref, volumen_aforo,
            {k: self.get_interim_value(k) for k in self.HALO_KEYS}
        )

        if not potencia_ref:
            logger.info("[MicroPrep] Stage 1 SKIP — potencia_ref no disponible (consumable sin asignar o sin concentracion)")
            return None

        potencia_ref = api.to_float(potencia_ref, None)
        
        if not volumen_aforo:
            logger.info("[MicroPrep] Stage 1 SKIP — volumen_aforo vacio")
            return None

        # conc_obj == analysis_condition_from analysis condiion from father analysis (dependant)
        conc_obj_raw = self.get_conc_obj_from_dependant_condition(analysis=self.analysis)
        
        logger.info("[MicroPrep] conc_obj_raw ='%s'", conc_obj_raw)
        
        # extract number from conc_obj if it's in the format "X mg/mL" or similar
        if isinstance(conc_obj_raw, str):
            try:
                conc_obj = api.to_float(conc_obj_raw.split()[0], None)
                conc_obj_unit = conc_obj_raw.split()[1] if len(conc_obj_raw.split()) > 1 else ""
                logger.info("[MicroPrep] conc_obj extraido de string='%s'", conc_obj)
            except (ValueError, IndexError):
                logger.info("[MicroPrep] conc_obj no pudo ser convertido a float desde string='%s'", conc_obj)
                conc_obj = None
        
        self.require(conc_obj, _("Objective concentration (conc_obj) is required for preparation calculation"))
        
        # the conversion between conc_obj unit and potencia should be handled by the user filling the conc_obj value in the correct unit that matches potencia_ref, or by extending this method to also parse units and convert accordingly. For now we assume they are compatible.
        # the format of conversion_factors should be aplied in conc_obj and potencia_ref, the search shorld be in upper_case and converted to mg/mL or similar units, but since we are assuming they are compatible for now, we will not implement the conversion logic until we have a clear requirement for it.:
        conversion_factors = {
            "MG/ML": 1,
            "MG/G": 1,
            "UG/ML": 0.001,
            "µG/MG": 0.001,
            "UG/MG": 0.001,
            "G/MG": 1000,
            "NG/ML": 0.000001,
            "%": 1,
        }
        potencia_ref_unit = self.standardize_unit(potencia_ref_unit)
        conc_obj_unit = self.standardize_unit(conc_obj_unit)
        
        potencia_ref_factor = conversion_factors.get(potencia_ref_unit, None)
        conc_obj_factor = conversion_factors.get(conc_obj_unit, None)
        if potencia_ref_factor is None:
            logger.info("[MicroPrep] Unidad de potencia_ref '%s' no reconocida en conversion_factors", potencia_ref_unit)
            potencia_ref_factor = 1  # assume compatible
        if conc_obj_factor is None:
            logger.info("[MicroPrep] Unidad de conc_obj '%s' no reconocida en conversion_factors", conc_obj_unit)
            conc_obj_factor = 1  # assume compatible
        
        peso = self.calculate_peso_objetivo(conc_obj, volumen_aforo, potencia_ref, conversion_factor=conc_obj_factor / potencia_ref_factor)
        logger.info("[MicroPrep] Stage 1 OK — conc_obj='%s' peso_objetivo='%s'", conc_obj, peso)

        # Stage 2: validate conc_real if all reps are available
        rep_01 = self.get_interim_value("rep_01", default=None, as_float=True)
        rep_02 = self.get_interim_value("rep_02", default=None, as_float=True)
        rep_03 = self.get_interim_value("rep_03", default=None, as_float=True)

        if rep_01 and rep_02 and rep_03:
            conc_real = self.calculate_conc_real(
                rep_01, rep_02, rep_03, potencia_ref, volumen_aforo, conversion_factor=conc_obj_factor / potencia_ref_factor
            )
            logger.info("[MicroPrep] Stage 2 OK — conc_real='%s'", conc_real)
            self.validate_conc_real(conc_real, conc_obj, tolerance)
            self.set_interim_value("conc_real", conc_real)
        else:
            logger.info("[MicroPrep] Stage 2 SKIP — replicas incompletas rep_01=%s rep_02=%s rep_03=%s",
                        rep_01, rep_02, rep_03)
        
        # Stage 3: final result from halo measurements (read from interims)
        halo_kwargs = {k: self.get_interim_value(k) for k in self.HALO_KEYS}
        result = self.calculate_halo_average(halo_kwargs)
        if result is not None:
            logger.info("[MicroPrep] Stage 3 OK — resultado final='%s'", result)
            
        return result


# ---------------------------------------------------------------------------
# VariationCoeficientCalculator
# ---------------------------------------------------------------------------

class VariationCoeficientCalculator(BaseCalculator):
    """Calculate Variation Coeficient from interim fields"""

    def calculate(self):
        """Calculate Variation Coeficient"""
        data = []
        for dependency in self.get_dependencies():
            interim_fields = api.safe_getattr(dependency, "getInterimFields", [])
            for interim in interim_fields:
                if api.to_float(interim.get("value"), 0) > 0:
                    data.append(api.to_float(interim.get("value"), 0))

        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / (len(data) - 1)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean * 100 if mean != 0 else 0
        return cv


# ---------------------------------------------------------------------------
# DensityCalculator
# ---------------------------------------------------------------------------

class DensityCalculator(BaseCalculator):

    error_class = DensityCalculationError

    def __init__(self, analysis_brain_uid):
        logger.info("[Density] START uid='%s'", analysis_brain_uid)
        super(DensityCalculator, self).__init__(analysis_brain_uid)
        self.instrument = self.analysis.getInstrument()

        logger.info("[Density] instrument='%s'", self.instrument)

        self.require(self.instrument, _("Not instrument selected"))

        logger.info("[Density] interim_fields count=%d | raw=%s",
                    len(self.interim_fields),
                    [(i.get("keyword"), i.get("value")) for i in self.interim_fields])

        self.require(self.interim_fields, _("Interim fields not defined"))

        self.weight_sample = self.get_interim_value(
            "pycnometer_sample_weight", default=None, as_float=True
        )
        logger.info("[Density] pycnometer_sample_weight='%s'", self.weight_sample)

        if not self.weight_sample:
            logger.info("[Density] STOP — pycnometer_sample_weight is empty, skipping calculation")
            return

        self.pycnometer_data()
        self.calculate()
        self.setInterimFieldsWithValues()

    def pycnometer_data(self):
        self.variables = getattr(self.instrument, 'VariablesSettings', [])
        logger.info("[Density] instrument variables=%s", self.variables)
        self.require(self.variables, _("Not variables defined"))

        self.weight = next(
            (api.to_float(var["value"]) for var in self.variables
             if var["keyword"] == 'weight'),
            None
        )
        self.water_filled_weight = next(
            (api.to_float(var["value"], None) for var in self.variables
             if var["keyword"] == 'water_filled_weight'),
            None
        )
        logger.info("[Density] pycnometer empty weight='%s' | water_filled_weight='%s'",
                    self.weight, self.water_filled_weight)

        self.require(self.weight, _("weight variable not defined"))
        self.require(self.water_filled_weight, _("water filled weight variable not defined"))

    def calculate(self):
        logger.info("[Density] CALCULATE weight_sample='%s' | weight='%s' | water_filled_weight='%s'",
                    self.weight_sample, self.weight, self.water_filled_weight)
        self.validate(
            self.weight_sample > self.weight,
            _("The weight of the pycnometer with the sample cannot be less than "
              "the weight of the empty pycnometer.")
        )
        self.validate(
            self.water_filled_weight > self.weight,
            _("The weight of the pycnometer with the water cannot be less than "
              "the weight of the empty pycnometer.")
        )

        self.water_weight = self.water_filled_weight - self.weight
        self.result = (self.weight_sample - self.weight) / self.water_weight
        logger.info("[Density] water_weight='%s' | result='%s'", self.water_weight, self.result)

    def setInterimFieldsWithValues(self):
        mapping = {
            "pycnometer_void_weight": str(self.weight) if self.result else "",
            "pycnometer_water_filled_weight": str(self.water_filled_weight) if self.result else "",
        }
        logger.info("[Density] setInterimFieldsWithValues mapping=%s", mapping)

        for interim in self.interim_fields:
            kw = interim.get("keyword")
            if kw in mapping:
                logger.info("[Density]   field='%s' current_value='%s' is_editable=%s",
                            kw, interim.get("value"), is_interim_editable(interim))

        self.set_interim_values(mapping, overwrite=True)
        logger.info("[Density] setInterimFields DONE")


# ---------------------------------------------------------------------------
# Public calc_* functions
# ---------------------------------------------------------------------------

def calc_lal(analysis_brain_uid, default_return='0'):
    """Función principal para cálculo de LAL"""
    logger.info("Calculating LAL for analysis: %s", analysis_brain_uid)
    calculator = LALCalculator(analysis_brain_uid)
    result = calculator.calculate()
    return result if result is not None else default_return


def calc_val_micro(analysis_brain_uid, *args):
    """Función principal para cálculo de Ensayos Microbianos"""
    try:
        calculator = MicrobialAssaysCalculator(analysis_brain_uid)
        result = calculator.calculate()
        calculator.set_interim_fields()
        return result
    except MicrobialAssaysCalculationError as e:
        logger.error("MicrobialAssaysError Calculation error: %s", str(e))
        raise


def calc_val_micro_prep(context, type=None, tolerance=0.02, **kwargs):
    """Función para cálculo de preparación de ensayo microbiológico.

    Todos los valores se leen directamente de los interim fields del análisis.
    La fórmula solo necesita pasar context:
        calc_val_micro_prep(context=%(context_uid)s)

    - tolerance: máxima desviación relativa entre conc_real y conc_obj (default 2%)
    """
    logger.info("[MicroPrep] START context='%s' tolerance='%s'", context, tolerance)
    try:
        calculator = MicrobialAssaysPrepCalculator(context)
        return calculator.run(tolerance=tolerance, type=type, **kwargs)
    except MicrobialAssaysPrepCalculationError as e:
        logger.error("MicrobialAssaysPrep calculation error: %s", str(e))
        raise


def calc_val_micro_cv(analysis_brain_uid, *args):
    """Función de cálculo estándar que devuelve el coeficiente de variación"""
    calculator = VariationCoeficientCalculator(analysis_brain_uid)
    return calculator.calculate()


def calc_densidad(analysis_brain_uid, *args):
    logger.info("Calculating density for analysis: %s", analysis_brain_uid)
    try:
        calculator = DensityCalculator(analysis_brain_uid)
        return calculator.result
    except DensityCalculationError as e:
        logger.error("Density Calculation error: %s", str(e))
        raise


def calc_valoracion(**kwargs):
    """Función de cálculo estándar que devuelve 0"""
    unknown_concentration = [k for k in kwargs.keys() if 'CONC_UNK_' in k]
    return calc_average(*[kwargs[k] for k in unknown_concentration])


def calc_average(*args):
    """Function that calculates the average of the input values"""
    values = [api.to_float(arg, 0) for arg in args if arg is not None]
    if not values:
        return 0
    return sum(values) / len(values)


def calc_uniformidad_contenido(context=None, T=100, k=2.4, SUBGROUPS=2, POTENCIA_DECLARADA=1, **kwargs):
    """Función para calcular la uniformidad de contenido"""
    unknown_concentration = [kwargs[key] for key in sorted(kwargs) if 'CONC_UNK_' in key]
    logger.info("Unknown concentrations: '%s'", unknown_concentration)

    unknown_concentrations_gruped = []
    for i in range(0, len(unknown_concentration), SUBGROUPS):
        logger.info("Index i: '%s'", i)
        val1 = api.to_float(unknown_concentration[i], 0)
        val2 = api.to_float(unknown_concentration[i + 1], 0)
        logger.info("Values to group: '%s' and '%s'", val1, val2)
        if val1 > 0 and val2 > 0:
            unknown_concentrations_gruped.append(
                (val1 + val2) / SUBGROUPS / POTENCIA_DECLARADA * 100
            )
    logger.info("Unknown concentrations gruped: '%s'", unknown_concentrations_gruped)
    if len(unknown_concentrations_gruped) < len(unknown_concentration) / SUBGROUPS:
        return

    mean = sum(unknown_concentrations_gruped) / len(unknown_concentrations_gruped)
    logger.info("Mean of unknown concentrations gruped: '%s'", mean)
    variance = sum((x - mean) ** 2 for x in unknown_concentrations_gruped) / (len(unknown_concentrations_gruped) - 1)
    logger.info("Variance of unknown concentrations gruped: '%s'", variance)
    std = variance ** 0.5
    M = 0
    if T <= 101:
        if mean < 98.5:
            M = 98.5
        elif mean <= 101.5:
            M = mean
        else:
            M = 101.5
    else:
        if mean < 98.5:
            M = 98.5
        elif mean <= T:
            M = mean
        else:
            M = T
    logger.info("M:'%s' | k: '%s' | mean: '%s' | std: '%s'", M, k, mean, std)
    logger.info("result value: '%s'", abs(M - mean) + float(k) * std)

    result = abs(M - mean) + k * std

    interims_to_modify = {'mean': mean, 'std': std, 'm': M}
    if context:
        analysis = api.get_object(context)
        if analysis:
            interim_fields = api.safe_getattr(analysis, "getInterimFields", [])
            for interim in interim_fields:
                if not is_interim_editable(interim):
                    continue
                if interim.get("keyword") in interims_to_modify:
                    logger.info(
                        "Setting interim field '%s' with value '%s'",
                        interim.get("keyword"), interims_to_modify[interim.get("keyword")]
                    )
                    interim["value"] = interims_to_modify[interim.get("keyword")]
            analysis.setInterimFields(interim_fields)
    return result


def calc_net_average(gross, tare, context=None):
    """Función para calcular el promedio neto"""
    if not gross or not tare:
        return

    gross_value = api.to_float(gross, 0)
    tare_value = api.to_float(tare, 0)
    net_value = gross_value - tare_value

    if not context:
        return net_value

    analysis = api.get_object(context)
    if not analysis:
        return net_value

    interim_fields = api.safe_getattr(analysis, "getInterimFields", [])
    dependencies = analysis.getDependencies()

    gross_analysis = next(
        (dep for dep in dependencies if str(dep.getResult()) == str(gross)), None
    )
    tare_analysis = next(
        (dep for dep in dependencies if str(dep.getResult()) == str(tare)), None
    )

    gross_interims_dict = {}
    tare_interims_dict = {}

    for item in api.safe_getattr(gross_analysis, "getInterimFields", []):
        gross_interims_dict[item["keyword"]] = item["value"]

    for item in api.safe_getattr(tare_analysis, "getInterimFields", []):
        tare_interims_dict[item["keyword"]] = item["value"]

    for interim in interim_fields:
        if not is_interim_editable(interim):
            continue
        keyword = interim["keyword"]
        gross_interim_value = api.to_float(gross_interims_dict.get(keyword, 0))
        tare_interim_value = api.to_float(tare_interims_dict.get(keyword, 0))
        interim["value"] = str(gross_interim_value - tare_interim_value)

    analysis.setInterimFields(interim_fields)
    return net_value


def calc_units_in_range(context, base_spec, potency_declared, dependency_keyword=None, percentage_difference=0, constant_difference=0, max_out_of_range=0, **kwargs):
    """Función para calcular unidades en rango
    args:
        context: análisis
        base_spec: the base spec to compare any unit
        percentage_difference: percentage difference from base spec
        max_out_of_range: maximum units out of range
        dependency_keyword: keyword to check in dependencies
    """
    if not context:
        return

    analysis = api.get_object(context)
    if not analysis:
        return

    spec_value = api.to_float(base_spec, None)
    if base_spec is None or spec_value is None:
        return

    dependencies = analysis.getDependencies()
    if not dependencies:
        return

    valid_dependencies = []
    for dep in dependencies:
        keyword = dep.getKeyword()
        result = dep.getResult()
        if dependency_keyword in keyword:
            valid_dependencies.append({
                "keyword": keyword,
                "result": api.to_float(result, None)
            })
            continue
        for interim in dep.getInterimFields():
            if dependency_keyword in interim["keyword"]:
                valid_dependencies.append({
                    "keyword": interim["keyword"],
                    "result": api.to_float(interim["value"], None)
                })

    if not valid_dependencies or any([dep["result"] is None for dep in valid_dependencies]):
        logger.info("No valid dependencies or None result")
        logger.info("Valid dependencies: '%s'", valid_dependencies)
        return

    out_of_ranges = []
    percentage_difference = api.to_float(percentage_difference, 0)
    spec_value = api.to_float(spec_value, 0)
    min_value = spec_value * (1 - percentage_difference / 100)
    max_value = spec_value * (1 + percentage_difference / 100)
    for dep in valid_dependencies:
        result = dep["result"]
        if result < min_value or result > max_value:
            out_of_ranges.append(dep)

    logger.info("Out of ranges: '%s'", out_of_ranges)
    logger.info(
        "spec range are: mean='%s' | percentage_difference='%s' | max_value='%s' | min_value='%s'",
        spec_value, percentage_difference,
        spec_value * (1 + percentage_difference / 100),
        spec_value * (1 - percentage_difference / 100)
    )
    if len(out_of_ranges) > max_out_of_range:
        message = ""
        for dep in out_of_ranges:
            message += "{}: {}\n".format(dep["keyword"], dep["result"])
        logger.info("Message: '%s'", message)
        analysis.setRemarks(message)
        return 0
    analysis.setRemarks("")
    return 1


def calc_disolution(context=None, stage="S1", Q=75, overwrite_remarks=True, potency_declared=None, **kwargs):
    """Función para calcular la disolución

    args:
        stage: stage of the disolution
        Q: Q value in % (15% = 15)
        context: analysis
        overwrite_remarks: overwrite remarks

        return 1 if all conditions are met, 0 otherwise
    """
    """Criterios de aceptación según usp<711>
    S1: 6 unidades, ninguna < Q + 5%
    S2: 12 unidades (6 de S1 + 6 de S2), promedio >= Q & ninguna < Q - 15%
    S3: 24 unidades (6 de S1 + 6 de S2 + 12 de S3), promedio >= Q & no más de 2 unidades < Q - 15% & ninguna < Q - 25%

    Muestras combinadas
    S1': 6 unidades, ninguna < Q + 10%
    S2': 12 unidades (6 de S1 + 6 de S2), promedio >= Q + 5%
    S3': 24 unidades (6 de S1 + 6 de S2 + 12 de S3), promedio >= Q

    Liberación prolongada (L)
    L1: 6 unidades, ninguna < spec
    L2: 12 unidades (6 de L1 + 6 de L2), promedio >= spec & ninguna < spec - 10% & ninguna > spec + 10%
    L3: 24 unidades (6 de L1 + 6 de L2 + 12 de L3), promedio >= spec & no mas de 2 unidades < spec - 10% & no mas de 2 unidades > spec + 10% & ninguna > spec + 20% & ninguna < spec - 20%

    Liberación retardada (A+B)
    A1: 6 unidades, ninguna > 10%
    A2: 12 unidades (6 de A1 + 6 de A2), promedio <= 10% & ninguna > 25%
    A3: 24 unidades (6 de A1 + 6 de A2 + 12 de A3),promedio <= 10% & ninguna > 25%

    B1: 6 unidades, ninguna > Q + 5%
    B2: 12 unidades (6 de B1 + 6 de B2), promedio >= Q & ninguna < Q - 15%
    B3: 24 unidades (6 de B1 + 6 de B2 + 12 de B3), promedio >= Q & no mas de 2 unidades < Q - 15% & ninguna < Q - 25%
    """
    if not context:
        return

    analysis = api.get_object(context)
    if not analysis:
        return
    spec_min_t1 = 10
    spec_max_t1 = 15
    spec_min_t2 = 35
    spec_max_t2 = 50
    spec_min_t3 = 75
    spec_max_t3 = 200
    Q = api.to_float(Q, None)

    if Q is None:
        logger.info("Q is not number")
        return

    logger.info("Q: '%s'", Q)
    stage_conditions = {
        "S1": {
            "n_units": 6,
            "conditions": [
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": Q - 5,
                    "max": None,
                }
            ]
        },
        "S2": {
            "n_units": 12,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": Q,
                    "max": None,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": Q - 15,
                    "max": None,
                }
            ]
        },
        "S3": {
            "n_units": 24,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": Q,
                    "max": None,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 2,
                    "min": Q - 15,
                    "max": None,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": Q - 25,
                    "max": None,
                }
            ]
        },
        "SS1": {
            "n_units": 6,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": Q + 10,
                    "max": None,
                    "message": "Promedio de disolución mayor a Q + 10%"
                }
            ]
        },
        "SS2": {
            "n_units": 12,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": Q + 5,
                    "max": None,
                    "message": "Promedio de disolución mayor a Q + 5%"
                }
            ]
        },
        "SS3": {
            "n_units": 24,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": Q,
                    "max": None,
                    "message": "Promedio de disolución mayor a Q"
                },
            ]
        },
        "L1": {
            "n_units": 6,
            "conditions": [
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": spec_min_t1,
                    "max": spec_max_t1,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": spec_min_t2,
                    "max": spec_max_t2,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": spec_min_t3,
                    "max": spec_max_t3,
                }
            ]
        },
        "L2": {
            "n_units": 12,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": spec_min_t1,
                    "max": spec_max_t1,
                },
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": spec_min_t2,
                    "max": spec_max_t2,
                },
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": spec_min_t3,
                    "max": spec_max_t3,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": spec_min_t1 - 10,
                    "max": spec_max_t1 + 10,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": spec_min_t2 - 10,
                    "max": spec_max_t2 + 10,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": spec_min_t3 - 10,
                    "max": spec_max_t3 + 10,
                }
            ]
        },
        "L3": {
            "n_units": 24,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": spec_min_t1,
                    "max": spec_max_t1,
                },
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": spec_min_t2,
                    "max": spec_max_t2,
                },
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": spec_min_t3,
                    "max": spec_max_t3,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 2,
                    "min": spec_min_t1 - 10,
                    "max": spec_max_t1 + 10,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 2,
                    "min": spec_min_t2 - 10,
                    "max": spec_max_t2 + 10,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 2,
                    "min": spec_min_t3 - 10,
                    "max": spec_max_t3 + 10,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": spec_min_t1 - 20,
                    "max": spec_max_t1 + 20,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": spec_min_t2 - 20,
                    "max": spec_max_t2 + 20,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": spec_min_t3 - 20,
                    "max": spec_max_t3 + 20,
                }
            ]
        },
        "A1": {
            "n_units": 6,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": None,
                    "max": 10,
                },
            ]
        },
        "A2": {
            "n_units": 12,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": None,
                    "max": 10,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": None,
                    "max": 25,
                },
            ]
        },
        "A3": {
            "n_units": 24,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": None,
                    "max": 10,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": None,
                    "max": 25,
                },
            ]
        },
        "B1": {
            "n_units": 6,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": Q + 5,
                    "max": None,
                },
            ]
        },
        "B2": {
            "n_units": 12,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": Q + 5,
                    "max": None,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": Q - 15,
                    "max": None,
                },
            ]
        },
        "B3": {
            "n_units": 24,
            "conditions": [
                {
                    "type": "average",
                    "max_units_out_of_range": None,
                    "min": Q,
                    "max": None,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 2,
                    "min": Q - 15,
                    "max": None,
                },
                {
                    "type": "individual",
                    "max_units_out_of_range": 0,
                    "min": Q - 25,
                    "max": None,
                },
            ]
        },
    }

    if stage not in stage_conditions:
        logger.error("Stage not valid: '%s'", stage)
        raise ValueError("Stage not valid: '%s'" % stage)

    stage_data = stage_conditions[stage]
    n_units = stage_data["n_units"]
    conditions = stage_data["conditions"]

    values = [v for k, v in kwargs.items() if k.startswith("CONC_UNK_")]
    logger.info("values '%s'", values)
    logger.info("type of values '%s'", [type(v) for v in values])
    values = [api.to_float(v, None) for v in values if v is not None]

    if any([v is None for v in values]):
        logger.error("All values must be numbers")
        raise ValueError("All values must be numbers")
    values.sort()

    if len(values) != n_units:
        logger.error(
            "Number of values does not match number of units: %d != %d",
            len(values), n_units
        )
        raise ValueError(
            "Number of values does not match number of units: %d != %d" % (len(values), n_units)
        )

    if potency_declared is not None:
        potency_declared = api.to_float(potency_declared, None)
        if potency_declared is None:
            logger.error("Potency declared must be a number")
            raise ValueError("Potency declared must be a number")
        values = [v / potency_declared * 100 for v in values]

    logger.info("values after potency_declared '%s'", values)
    for condition in conditions:
        if condition["type"] == "average":
            avg = sum(values) / len(values)
            if condition["min"] is not None and avg < condition["min"]:
                condition["pass"] = False
                continue
            if condition["max"] is not None and avg > condition["max"]:
                condition["pass"] = False
                continue
            condition["pass"] = True

        elif condition["type"] == "individual":
            out_of_range = 0
            for v in values:
                if condition["min"] is not None and v < condition["min"]:
                    out_of_range += 1
                    continue
                if condition["max"] is not None and v > condition["max"]:
                    out_of_range += 1
                    continue
            if out_of_range > condition["max_units_out_of_range"]:
                condition["pass"] = False
            else:
                condition["pass"] = True
            condition["num_out_of_range"] = out_of_range

    all_pass = all(condition["pass"] for condition in conditions)

    for condition in conditions:
        if condition["min"] is not None and condition["max"] is not None:
            condition_spect_formatted = "{min} - {max}".format(
                min=condition["min"], max=condition["max"]
            )
        elif condition["min"] is not None:
            condition_spect_formatted = "No menor a {min}".format(min=condition["min"])
        elif condition["max"] is not None:
            condition_spect_formatted = "No mayor a {max}".format(max=condition["max"])

        if condition["type"] == "average":
            condition["message"] = (
                "El promedio Q debe estar en el rango de {condition_spect_formatted}".format(
                    condition_spect_formatted=condition_spect_formatted
                )
            )
        else:
            if condition["max_units_out_of_range"] == 0:
                condition["message"] = (
                    "Ninguna de las unidades debe ser {condition_spect_formatted}".format(
                        condition_spect_formatted=condition_spect_formatted
                    )
                )
            else:
                condition["message"] = (
                    "No más de {max_units_out_of_range} unidades deben ser "
                    "{condition_spect_formatted}".format(
                        max_units_out_of_range=condition["max_units_out_of_range"],
                        condition_spect_formatted=condition_spect_formatted
                    )
                )

    message = "Requisitos: " + "; ".join([condition["message"] for condition in conditions])

    logger.info("message: '%s'", message)
    if overwrite_remarks:
        logger.info("Overwriting remarks")
        logger.info("analysis %s", analysis)
        logger.info("analysis uid %s", analysis.UID())
        logger.info("analysis remarks %s", analysis.getRemarks())
        analysis.setRemarks(api.safe_unicode(message))
        analysis.reindexObject()
        event.notify(ObjectEditedEvent(analysis))
        logger.info("analysis remarks after %s", analysis.getRemarks())
    return 1 if all_pass else 0
