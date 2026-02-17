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

class LALCalculator:
    """Clase dedicada al cálculo de LAL con responsabilidades separadas"""
    
    def __init__(self, analysis_brain_uid):
        self.analysis = api.get_object(analysis_brain_uid)
        self.sample = api.safe_getattr(self.analysis, "getRequest", None)
        self.interim_fields = api.safe_getattr(self.analysis, "getInterimFields", [])
    
    def get_sensitivity(self):
        """Obtener sensibilidad de los análisis QC"""
        LAL_KEYWORD_QC = "Reactivo LAL"
        analysis_qcs = self.sample.getQCAnalyses() if self.sample else None
        if not analysis_qcs:
            raise LALCalculationError(_("No QCs found for analysis %s" % self.analysis.UID()))
        
        valid_qc = None
        
        for qc in analysis_qcs:
            rd = qc.getReferenceDefinition()
            if not rd:
                continue
            if rd.Title() == LAL_KEYWORD_QC:
                valid_qc = qc
                break
        
        if not valid_qc:
            raise LALCalculationError(_("Not valid qcs with reference definition '%s'"%(LAL_KEYWORD_QC)))

        variables = getattr(valid_qc,'VariablesSettings', [])
        
        if not variables:
            raise LALCalculationError(_("Variables for qc analysis not set for qc '%s'"%(analysis_qcs)))
        
        sensitivity = next((var["value"] for var in variables if var["keyword"] == "sensitivity"), None)
        if not sensitivity:
            raise LALCalculationError(_("No sensitivity found for analysis %s" % self.analysis.UID()))
        
        return api.to_float(sensitivity,0)
    
    def get_concentration_and_dilution(self):
        """Obtener concentración y dilución de la matriz de muestra"""
        samplematrix = self.sample.getSampleType().getSampleMatrix() if self.sample else None
        if not samplematrix:
            raise LALCalculationError(_("Sample matrix not found"))
        
        dict_variables = compute_variables_dict(samplematrix)
        concentration_raw = dict_variables.get('LAL', {}).get('concentration')
        dilution_raw = dict_variables.get('LAL', {}).get('dilution', (1, 'mL'))
        
        if not concentration_raw:
            raise LALCalculationError(_("Concentration not found in sample matrix variables, actual sample matrices for samplematrix '%s' are: '%s'", samplematrix, dict_variables))
        
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
        
        raise LALCalculationError(_("Reference Sample not valid interim (d1)"))
    
    def calculate_regular_analysis(self, sensitivity):
        """Calcular para análisis regular"""
        logger.info("Calculating regular analysis of LAL calc")
        result_range = api.safe_getattr(self.analysis, "getResultsRange", None)
        if not result_range:
            return 0
        
        # Obtener límites de especificación
        specs_lim = max(
            api.to_float(getattr(result_range, 'max', 0), 0),
            api.to_float(getattr(result_range, 'min', 0), 0)
        )
        
        # Obtener concentración y dilución
        conc, dilution, conc_unit, dilution_unit = self.get_concentration_and_dilution()
        logger.info("Data for LAL Calc--->conc:='%s'---dilution:='%s'---sensitivity:='%s'", conc, dilution, sensitivity)

        # Calcular MDV
        mdv = (specs_lim * conc) / (sensitivity * dilution) if sensitivity and dilution else 0
        # Actualizar campos interinos
        max_dilution = 0
        for interim in self.interim_fields:
            if not is_interim_editable(interim):
                continue
                
            keyword = interim.get("keyword", "")
            value = interim.get("value", "")
            
            # Actualizar campo mdv
            if keyword == "mdv":
                interim["value"] = str(mdv)
                
            elif keyword == "concentration":
                interim["value"] = str(conc)
                interim["unit"] = conc_unit
            
            elif keyword == "dilution":
                interim["value"] = str(dilution)
                interim["unit"] = dilution_unit
            
            elif keyword == "sensitivity":
                interim["value"] = str(sensitivity) 
            
            # Actualizar campo dmdv si existe
            elif keyword == "dmdv" and value not in [None, "", 0, "0"]:
                interim["value"] = str(mdv)
            
            # Manejar campos de dilución
            elif keyword.startswith("d") and len(keyword) > 1:
                try:
                    dilution_key_number = api.to_float(keyword[1:], 1)
                    current_value = api.to_float(value, 1)
                    max_dilution = max(max_dilution, current_value)
                    
                    # Actualizar permitir vacío basado en MDV
                    interim["allow_empty"] = "on" if dilution_key_number > mdv else "off"
                except ValueError:
                    logger.error("Invalid interim field value: %s", value)
        
        # Guardar campos actualizados
        self.analysis.setInterimFields(self.interim_fields)
        
        # Calcular resultado final
        logger.info("Data for LAL Calc--->mdv:='%s'---max dilution:='%s'", mdv, max_dilution)
        result_ue_ml = max_dilution * sensitivity
        result_ue_mg = result_ue_ml * dilution / conc if conc else 0
        
        return result_ue_mg
    
    def calculate(self):
        """Método principal para realizar el cálculo"""
        try:
            sensitivity = self.get_sensitivity()
            
            if is_reference_analysis(self.analysis):
                return self.calculate_reference_analysis()
            else:
                return self.calculate_regular_analysis(sensitivity)
                
        except LALCalculationError as e:
            logger.error("LAL calculation error: %s", str(e))
            show_message(str(e))
            raise LALCalculationError(str(e))

class LALCalculationError(Exception):
    """Excepción personalizada para errores en el cálculo de LAL"""
    
class MicrobialAssaysCalculationError(Exception):
    """Excepción personalizada para errores en el cálculo de Microbial Assays"""

class DensityCalculationError(Exception):
    """Excepción personalizada para errores en el cálculo de densidad"""

class MicrobialAssaysCalculator:
    """Clase dedicada al cálculo de Ensayos Microbianos con responsabilidades separadas"""
    DEPENDENCIES_SERVICES_KEY_M =('DIAMETRO_HALO_M1', 'DIAMETRO_HALO_M2', 'DIAMETRO_HALO_M3')
    DEPENDENCIES_SERVICES_KEY_ST = ('DIAMETRO_HALO_ST1', 'DIAMETRO_HALO_ST2', 'DIAMETRO_HALO_ST3')
    DEPENDENCIES_SERVICES_KEYS = DEPENDENCIES_SERVICES_KEY_ST+DEPENDENCIES_SERVICES_KEY_M
    DIAMETER_KEYS = ['diameter_plate1', 'diameter_plate2']
    CONCENTRATION_ANALYSIS = ['ST']
    REQUIRED_QC_KEYS = ('ST', 'ORGANISM')
    ALLOWED_EDITABLE_STATUS = ["to_be_verified", "verified", "published"]
    
    def __init__(self, analysis_brain_uid):
        self.analysis = api.get_object(analysis_brain_uid)
        self.dependencies = self.analysis.getDependencies()
        self.sample = api.safe_getattr(self.analysis, "getRequest", None)
        self.qc_analyses = self.sample.getQCAnalyses() if self.sample else []
        self.interim_fields = api.safe_getattr(self.analysis, "getInterimFields", [])

        
    def get_diameters(self):
        """Get diameter from QC analyses"""

        dependencies_keys = [a.getKeyword() for a in self.dependencies]
        
        if not all(key in dependencies_keys for key in self.DEPENDENCIES_SERVICES_KEYS):
            raise MicrobialAssaysCalculationError(_("Missing value dependencies in analysis %s" % self.analysis.UID()))
        
        self.valid_qc_analyses = [qc for qc in self.qc_analyses if qc.getKeyword() in self.REQUIRED_QC_KEYS]
        valid_dependencies = [dep for dep in self.dependencies if dep.getKeyword() in self.DEPENDENCIES_SERVICES_KEYS]

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
        if not self.qc_analyses:
            raise MicrobialAssaysCalculationError(_("No QC analyses found for analysis %s" % self.analysis.UID()))
        
        reference_sample = next((qc.getSample() for qc in self.qc_analyses if qc.getKeyword() in self.CONCENTRATION_ANALYSIS), None)
        
        if not reference_sample:
            raise MicrobialAssaysCalculationError(_("No QC analyses found to get concentration for analysis %s" % self.analysis.UID()))    
        
        self.reference_concentration = api.to_float(api.safe_getattr(reference_sample, "getConcentration", lambda: 1)(), 1)
        return self.reference_concentration
    
    def get_water_content_factor(self):
        """Get water content factor"""
        self.analysis.getInterimFields()
        self.water_factor = 0
        self.water_factor = api.to_float(next((interim.get("value") for interim in self.interim_fields if interim.get("keyword") == "humedad"), 0), 0)
        return self.water_factor
    
    def set_interim_fields(self):
        """Set interim fields with calculated values"""

        
        is_qc_analyses_editable = [
            api.get_workflow_status_of(qc) not in self.ALLOWED_EDITABLE_STATUS
            for qc in self.valid_qc_analyses
        ]
        
        if any(is_qc_analyses_editable):
            logger.info("Some interim fields in QC analyses are editable, skipping setting interim fields")
            return
        
        for interim in self.interim_fields:
            if not is_interim_editable(interim):
                continue
            
            if interim.get("keyword", "") == "st_concentration":
                interim["value"] = str(self.reference_concentration)
                
        self.analysis.setInterimFields(self.interim_fields)
        
    def calculate(self):
        """Método principal para realizar el cálculo de Ensayos Microbianos"""
        self.get_diameters()
        sum_dependencies_diameters_st = sum(self.dependencies_diameters_st)
        sum_dependencies_diameters_m = sum(self.dependencies_diameters_m)
        
        if not sum_dependencies_diameters_st or not sum_dependencies_diameters_m:
            raise MicrobialAssaysCalculationError(_("Sum of dependency diameters is zero for analysis %s" % self.analysis.UID()))
        
        concentration = self.get_reference_concentration()
        unit = self.analysis.getUnit()
        unit_factor = 100 if unit == "%" else 1
        water_content = self.get_water_content_factor()
        result = sum_dependencies_diameters_m / sum_dependencies_diameters_st * unit_factor * concentration * (1 - water_content / 100)
        return result

class VariationCoeficientCalculator:
    """Calculate Variation Coeficient from interim fields"""
    
    def __init__(self, analysis_brain_uid):
        self.analysis = api.get_object(analysis_brain_uid)
        self.dependencies = self.analysis.getDependencies()

    
    def calculate(self):
        """Calculate Variation Coeficient"""
        self.data = []

        for dependency in self.dependencies:
            interim_fields = api.safe_getattr(dependency, "getInterimFields", [])
            for interim in interim_fields:
                if api.to_float(interim.get("value"), 0) > 0:
                    self.data.append(api.to_float(interim.get("value"), 0))
        
        mean = sum(self.data) / len(self.data)
        variance = sum((x - mean) ** 2 for x in self.data) / (len(self.data) - 1)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean * 100 if mean != 0 else 0
        return cv

class DensityCalculator:
    def __init__(self, analysis_brain_uid):
        logger.info(">>>> Calculating Density")
        self.analysis = api.get_object(analysis_brain_uid)
        self.instrument = self.analysis.getInstrument()
        self.interim_fields = api.safe_getattr(self.analysis, "getInterimFields", [])
        
        logger.info("the instrument is:'%s'", self.instrument)
        
        if not self.instrument:
            raise DensityCalculationError(_("Not instrument selected"))
        
        if not self.interim_fields:
            raise DensityCalculationError(_("Interim fields not defined"))
        
        self.weight_sample = next((intreim["value"] for intreim in self.interim_fields if intreim["keyword"] == 'pycnometer_sample_weight'), None)
        self.weight_sample = api.to_float(self.weight_sample, None)
        
        if not self.weight_sample:
            logger.info("not weigh sample assigned")
            return
            
        self.pycnometer_data()
        self.calculate()
        self.setInterimFieldsWithValues()
            
    
    def pycnometer_data(self):
        self.variables = getattr(self.instrument,'VariablesSettings', [])
        
        if not self.variables:
            raise DensityCalculationError(_("Not variables defined"))
        
        self.weight = next((api.to_float(var["value"]) for var in self.variables if var["keyword"] == 'weight'), None)
        self.water_filled_weight = next((api.to_float(var["value"], None) for var in self.variables if var["keyword"] == 'water_filled_weight'), None)

        if not self.weight:
            raise DensityCalculationError(_("weight variable not defined"))
        
        if not self.water_filled_weight:
            raise DensityCalculationError(_("water filled weight variable not defined"))
    
    def calculate(self):
        if self.weight_sample <= self.weight:
            raise DensityCalculationError(_("The weight of the pycnometer with the sample cannot be less than the weight of the empty pycnometer."))
        
        if self.water_filled_weight <= self.weight:
            raise DensityCalculationError(_("The weight of the pycnometer with the water cannot be less than the weight of the empty pycnometer."))
        
        self.water_weight = self.water_filled_weight - self.weight
        self.result = (self.weight_sample - self.weight)/self.water_weight
    
    def setInterimFieldsWithValues(self):
        for interim in self.interim_fields:
            if not is_interim_editable(interim):
                logger.info("Not editable field")
                continue
            
            if interim.get("keyword", "") == "pycnometer_void_weight":
                interim["value"] = str(self.weight) if self.result else ""
                continue
            
            if interim.get("keyword", "") == "pycnometer_water_filled_weight":
                interim["value"] = str(self.water_filled_weight) if self.result else ""
                continue
            
        self.analysis.setInterimFields(self.interim_fields)
        
def calc_lal(analysis_brain_uid, default_return='0'):
    """Función principal para cálculo de LAL (versión mejorada)"""
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
        show_message(str(e))
        raise MicrobialAssaysCalculationError(str(e))

def calc_val_micro_cv(analysis_brain_uid, *args):
    """Función de cálculo estándar que devuelve 0"""
    
    calculator = VariationCoeficientCalculator(analysis_brain_uid)
    result = calculator.calculate()
    return result

def calc_densidad(analysis_brain_uid, *args):
    try:
        calculator = DensityCalculator(analysis_brain_uid)
        return calculator.result
    except DensityCalculationError as e:
            logger.error("Density Calculation error: %s", str(e))
            show_message(str(e))
            raise DensityCalculationError(str(e))
        
def calc_valoracion(**kwargs):
    """Función de cálculo estándar que devuelve 0"""
    # filter kwargs that contain 'st_concentration'

    unknown_concentration = [k for k in kwargs.keys() if 'CONC_UNK_' in k]
    
    return calc_average(
        *[kwargs[k] for k in unknown_concentration]
    )

def calc_average(*args):
    """Function that calculates the average of the input values"""
    values = [api.to_float(arg, 0) for arg in args if arg is not None]
    if not values:
        return 0
    return sum(values) / len(values)

def calc_uniformidad_contenido(T=100,k=2.4, SUBGROUPS=2, POTENCIA_DECLARADA=1, **kwargs):
    """Función para calcular la uniformidad de contenido"""

    unknown_concentration = [kwargs[key] for key in sorted(kwargs) if 'CONC_UNK_' in key]
    logger.info("Unknown concentrations: '%s'", unknown_concentration)
    # average in pairs, only 10 samples
    unknown_concentrations_gruped = []
    for i in range(0, len(unknown_concentration), SUBGROUPS):
        logger.info("Index i: '%s'", i)
        val1 = api.to_float(unknown_concentration[i], 0)
        val2 = api.to_float(unknown_concentration[i+1], 0)
        logger.info("Values to group: '%s' and '%s'", val1, val2)
        if val1 > 0 and val2 > 0:
            unknown_concentrations_gruped.append((val1 + val2) / SUBGROUPS / POTENCIA_DECLARADA * 100)
    logger.info("Unknown concentrations gruped: '%s'", unknown_concentrations_gruped)
    if len(unknown_concentrations_gruped) < len(unknown_concentration)/SUBGROUPS:
        return
    
    mean = sum(unknown_concentrations_gruped) / len(unknown_concentrations_gruped)
    logger.info("Mean of unknown concentrations gruped: '%s'", mean)
    # calculate standard deviation of data10 of 10 samples
    variance = sum((x - mean) ** 2 for x in unknown_concentrations_gruped) / (len(unknown_concentrations_gruped) - 1)
    logger.info("Variance of unknown concentrations gruped: '%s'", variance)
    std = variance ** 0.5
    M = 0
    if T<=101:
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
    logger.info("result value: '%s'", abs(M-mean)+float(k)*std)
    result = abs(M-mean)+k*std
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
    
    # setting interim field 'net_value'
    interim_fields = api.safe_getattr(analysis, "getInterimFields", [])
    dependencies = analysis.getDependencies()
    
    gross_analysis = next((dep for dep in dependencies if str(dep.getResult()) == str(gross)), None)
    tare_analysis = next((dep for dep in dependencies if str(dep.getResult()) == str(tare)), None)
    
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

def calc_units_in_range(context, base_spec, potency_declared ,dependency_keyword=None, percentage_difference=0, constant_difference=0, max_out_of_range=0, **kwargs):
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

    # check dependencies that contains the keyword
    valid_dependencies = []
    for dep in dependencies:
        keyword = dep.getKeyword()
        result = dep.getResult()
        if dependency_keyword in keyword:
            valid_dependencies.append(
                {
                    "keyword": keyword,
                    "result": api.to_float(result, None)
                }
            )
            continue
        for interim in dep.getInterimFields():
            if dependency_keyword in interim["keyword"]:
                valid_dependencies.append(
                    {
                        "keyword": interim["keyword"],
                        "result": api.to_float(interim["value"], None)
                    }
                )

    if not valid_dependencies or any([dep["result"] is None for dep in valid_dependencies]):
        logger.info("No valid dependencies or None result")
        logger.info("Valid dependencies: '%s'", valid_dependencies)
        return  
    
    out_of_ranges = []
    percentage_difference = api.to_float(percentage_difference, 0)
    spec_value = api.to_float(spec_value, 0)
    min_value = spec_value * (1 - percentage_difference/100)
    max_value = spec_value * (1 + percentage_difference/100)
    for dep in valid_dependencies:
        result = dep["result"]
        if result < min_value or result > max_value:
            out_of_ranges.append(dep)
    
    logger.info("Out of ranges: '%s'", out_of_ranges)
    logger.info("spec range are: mean='%s' | percentage_difference='%s' | max_value='%s' | min_value='%s'", spec_value, percentage_difference, spec_value*(1+percentage_difference/100), spec_value*(1-percentage_difference/100))
    if len(out_of_ranges) > max_out_of_range:
        message = ""
        for dep in out_of_ranges:
            message += "{}: {}\n".format(dep["keyword"], dep["result"])

        logger.info("Message: '%s'", message)
        analysis.setRemarks(message)
        return 0
    analysis.setRemarks("")
    return 1

def calc_disolution(context=None,stage="S1",Q=75,overwrite_remarks=True,potency_declared=None, **kwargs):
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
    """
    Condition array format:
    <stage>: {
        "n_units": 24,
        "conditions": [
            {
                "type": "average",
                "max_units_out_of_range": None,
                "min": None,
                "max": Q + 5,
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
    }

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

    # get values from kwargs that key starts with "dep"
    values = [v for k, v in kwargs.items() if k.startswith("CONC_UNK_")]
    logger.info("values '%s'", values)
    logger.info("type of values '%s'", [type(v) for v in values])
    values = [api.to_float(v, None) for v in values if v is not None]
    
    if any([v is None for v in values]):
        logger.error("All values must be numbers")
        raise ValueError("All values must be numbers")
    values.sort()
    
    if len(values) != n_units:
        logger.error("Number of values does not match number of units: %d != %d", len(values), n_units)
        raise ValueError("Number of values does not match number of units: %d != %d" % (len(values), n_units))

    if potency_declared is not None:
        potency_declared = api.to_float(potency_declared, None)
        if potency_declared is None:
            logger.error("Potency declared must be a number")
            raise ValueError("Potency declared must be a number")
        values = [v/potency_declared*100 for v in values]
    
    logger.info("values after potency_declared '%s'", values)
    # check conditions
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
    
    # check if all conditions are met
    all_pass = all(condition["pass"] for condition in conditions)

    # automatically generate message for all conditions, according to it's each condition
    # if condition is average

    for condition in conditions:
        if condition["min"] is not None and condition["max"] is not None:
            condition_spect_formatted = "{min} - {max}".format(min=condition["min"], max=condition["max"])
        elif condition["min"] is not None:
            condition_spect_formatted = "No menor a {min}".format(min=condition["min"])
        elif condition["max"] is not None:
            condition_spect_formatted = "No mayor a {max}".format(max=condition["max"])
        
        if condition["type"] == "average":
            condition["message"] = "El promedio Q debe estar en el rango de {condition_spect_formatted}".format(condition_spect_formatted=condition_spect_formatted)

        else:
            if condition["max_units_out_of_range"] == 0:
                condition["message"] = "Ninguna de las unidades debe ser {condition_spect_formatted}".format(condition_spect_formatted=condition_spect_formatted)
            
            else:
                condition["message"] = "No más de {max_units_out_of_range} unidades deben ser {condition_spect_formatted}".format(max_units_out_of_range=condition["max_units_out_of_range"], condition_spect_formatted=condition_spect_formatted)
    
    # generate message for all conditions
    message = "Requisitos: " +"; ".join([condition["message"] for condition in conditions])
    
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