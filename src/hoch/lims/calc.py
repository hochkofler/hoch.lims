# -*- coding: utf-8 -*-
from bika.lims import api
from bika.lims.api.analysis import is_reference_analysis
from hoch.lims import logger
from hoch.lims.utils import is_interim_editable
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
        
        dict_variables = getattr(samplematrix, 'variables_dict', {})
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

def calc_lal(analysis_brain_uid, default_return='0'):
    """Función principal para cálculo de LAL (versión mejorada)"""
    logger.info("Calculating LAL for analysis: %s", analysis_brain_uid)
    
    calculator = LALCalculator(analysis_brain_uid)
    result = calculator.calculate()
    
    return result if result is not None else default_return