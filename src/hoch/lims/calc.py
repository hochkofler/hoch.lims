# -*- coding: utf-8 -*-
from bika.lims import api
from bika.lims.api.analysis import is_reference_analysis
from hoch.lims import logger
from hoch.lims.utils import is_interim_editable, compute_variables_dict
from Products.statusmessages.interfaces import IStatusMessage
from zope.globalrequest import getRequest

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
        analysis_qcs = self.sample.getQCAnalyses() if self.sample else None
        if not analysis_qcs:
            raise LALCalculationError("No QCs found for analysis %s" % self.analysis.UID())
        
        sensitivity = next((qc.Sensitivity for qc in analysis_qcs if qc.Sensitivity), None)
        if not sensitivity:
            raise LALCalculationError("No sensitivity found for analysis %s" % self.analysis.UID())
        return sensitivity
    
    def get_concentration_and_dilution(self):
        """Obtener concentración y dilución de la matriz de muestra"""
        samplematrix = self.sample.getSampleType().getSampleMatrix() if self.sample else None
        if not samplematrix:
            raise LALCalculationError("Sample matrix not found")
        
        dict_variables = compute_variables_dict(samplematrix)
        concentration = dict_variables.get('LAL', {}).get('concentration')
        dilution = dict_variables.get('LAL', {}).get('dilution', 1)
        
        if not concentration:
            raise LALCalculationError("Concentration not found in sample matrix variables")
        
        return concentration, dilution
    
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
        
        raise LALCalculationError("Reference Sample not valid interim (d1)")
    
    def calculate_regular_analysis(self, sensitivity):
        """Calcular para análisis regular"""
        result_range = api.safe_getattr(self.analysis, "getResultsRange", None)
        if not result_range:
            return 0
        
        # Obtener límites de especificación
        specs_lim = max(
            api.to_float(getattr(result_range, 'max', 0), 0),
            api.to_float(getattr(result_range, 'min', 0), 0)
        )
        
        # Obtener concentración y dilución
        conc, dilution = self.get_concentration_and_dilution()

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

def calc_lal(analysis_brain_uid, default_return='0'):
    """Función principal para cálculo de LAL (versión mejorada)"""
    logger.info("Calculating LAL for analysis: %s", analysis_brain_uid)
    
    calculator = LALCalculator(analysis_brain_uid)
    result = calculator.calculate()
    
    return result if result is not None else default_return

class MicrobialAssaysCalculator:
    """Clase dedicada al cálculo de Ensayos Microbianos con responsabilidades separadas"""
    DEPENDENCIES_SERVICES_KEYS =['val_micro_1', 'val_micro_2', 'val_micro_3']
    DIAMETER_KEYS = ['diameter1', 'diameter2']
    INTERIM_KEYS = ['st_diameter1', 'st_diameter2', 'st_diameter3', 'st_diameter4', 'st_diameter5', 'st_diameter6']
    ALLOWED_EDITABLE_STATUS = ["to_be_verified", "verified", "published"]
    def __init__(self, analysis_brain_uid, *args):
        self.analysis = api.get_object(analysis_brain_uid)
        self.dependencies = self.analysis.getDependencies()
        self.sample = api.safe_getattr(self.analysis, "getRequest", None)
        self.qc_analyses = self.sample.getQCAnalyses() if self.sample else []
        self.interim_fields = api.safe_getattr(self.analysis, "getInterimFields", [])
        
    def get_diameters(self):
        """Get diameter from QC analyses"""
        "Check if there are all necesary QC analyses keywords"
        qc_keywords = [a.getKeyword() for a in self.qc_analyses]
        dependencies_keys = [a.getKeyword() for a in self.dependencies]
        
        if not all(key in qc_keywords for key in self.DEPENDENCIES_SERVICES_KEYS):
            raise MicrobialAssaysCalculationError("Missing value dependencies in qc analysis %s" % self.analysis.UID())
        
        if not all(key in dependencies_keys for key in self.DEPENDENCIES_SERVICES_KEYS):
            raise MicrobialAssaysCalculationError("Missing value dependencies in analysis %s" % self.analysis.UID())
        
        self.valid_qc_analyses = [qc for qc in self.qc_analyses if qc.getKeyword() in self.DEPENDENCIES_SERVICES_KEYS]
        self.valid_dependencies = [dep for dep in self.dependencies if dep.getKeyword() in self.DEPENDENCIES_SERVICES_KEYS]
        
        self.qc_diameters = []
        self.qc_diameters_editable = []
        for qc in self.valid_qc_analyses:
            #logger.info("Interim fields of QC %s: %s", qc.UID(), qc.getInterimFields())
            for interim in qc.getInterimFields():
                if interim.get("keyword") in self.DIAMETER_KEYS:
                    diameter_value = api.to_float(interim.get("value", 0), 0)
                    if diameter_value > 0:
                        self.qc_diameters.append(diameter_value)

        self.dependencies_diameters = []
        for dep in self.valid_dependencies:
            #logger.info("Interim fields of dep %s: %s", dep.UID(), dep.getInterimFields())
            for interim in dep.getInterimFields():
                if interim.get("keyword") in self.DIAMETER_KEYS:
                   if interim.get("keyword") in self.DIAMETER_KEYS:
                    diameter_value = api.to_float(interim.get("value", 0), 0)
                    if diameter_value > 0:
                        self.dependencies_diameters.append(diameter_value)
        
    def get_reference_concentration(self):
        """Get reference concentration from qc analysis"""
        if not self.qc_analyses:
            raise MicrobialAssaysCalculationError("No QC analyses found for analysis %s" % self.analysis.UID())
        
        reference_sample = self.qc_analyses[0].getSample()
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
        "check if all interim fields in qc analysis are editable"
        
        is_qc_analyses_editable = [
            api.get_workflow_status_of(qc) not in self.ALLOWED_EDITABLE_STATUS
            for qc in self.valid_qc_analyses
        ]
        
        if any(is_qc_analyses_editable):
            logger.info("Some interim fields in QC analyses are editable, skipping setting interim fields")
            return
                    
        valid_interim_fields = [
            interim
            for qc in self.valid_qc_analyses
            for interim in qc.getInterimFields()
            if interim.get("keyword") in self.DIAMETER_KEYS
            ]
        
        logger.info("valid interim fields '%s'", valid_interim_fields)
        
        valid_interim_fields_values = [api.to_float(interim.get("value"), 0) for interim in valid_interim_fields]
        for interim in self.interim_fields:
            if not is_interim_editable(interim):
                continue
            
            if interim.get("keyword", "") in self.INTERIM_KEYS:
                logger.info("Setting interim field %s with value 0 of list %s", interim.get("keyword", ""), valid_interim_fields_values)
                interim["value"] = str(valid_interim_fields_values.pop(0))
            
            if interim.get("keyword", "") == "st_concentration":
                interim["value"] = str(self.reference_concentration)
                
        self.analysis.setInterimFields(self.interim_fields)
        
    def calculate(self):
        """Método principal para realizar el cálculo de Ensayos Microbianos"""
        self.get_diameters()
        sum_dependencies_diameters = sum(self.dependencies_diameters)
        sum_qc_diameters = sum(self.qc_diameters)
        if not sum_qc_diameters:
            raise MicrobialAssaysCalculationError("Sum of QC diameters is zero for analysis %s" % self.analysis.UID())
        
        if not sum_dependencies_diameters:
            raise MicrobialAssaysCalculationError("Sum of dependency diameters is zero for analysis %s" % self.analysis.UID())
        
        concentration = self.get_reference_concentration()
        unit = self.analysis.getUnit()
        unit_factor = 100 if unit == "%" else 1
        water_content = self.get_water_content_factor()
        result = sum_dependencies_diameters / sum_qc_diameters * unit_factor * concentration * (1 - water_content / 100)
        return result
    
def calc_val_micro(analysis_brain_uid, *args):
    """Función principal para cálculo de Ensayos Microbianos"""
    
    calculator = MicrobialAssaysCalculator(analysis_brain_uid, *args)
    result = calculator.calculate()
    calculator.set_interim_fields()
    return result

def calc_std(self, *args, **kwargs):
    """Función de cálculo estándar que devuelve 0"""
    return 0