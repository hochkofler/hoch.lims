from bika.lims import api
from bika.lims.api.analysis import is_reference_analysis
from hoch.lims import logger
from hoch.lims.utils import is_interim_editable

def calc_lal(analysis_brain_uid, default_return='0'):
    analysis = api.get_object(analysis_brain_uid)
    interim_fields = api.safe_getattr(analysis, "getInterimFields", None)
    sample = api.safe_getattr(analysis, "getRequest", None)
    analysis_qcs = sample.getQCAnalyses()
    if not analysis_qcs:
        logger.info("No QCs found for analysis %s" % analysis_brain_uid)
        return
    sensitivity = next((qc.Sensitivity for qc in analysis_qcs if qc.Sensitivity), None)
    logger.info("No sensitivity found in QCs")
    if not sensitivity:
        return
    if not interim_fields:
        logger.info("No interim fields found for analysis %s" % analysis_brain_uid)
        return
    logger.info("Interim fields: %s" % interim_fields)
    if is_reference_analysis(analysis):
        logger.info("Reference analysis")
        logger.info("Interim fields: %s" % interim_fields)
        for interim in interim_fields:
            if not is_interim_editable(interim):
                continue
            if interim.get("keyword", "") == "d1":
                result = api.to_float(interim["value"], -1)
                logger.info("d1 value: %s" % result)
                if result == -1:
                    return
                if result > 0:
                    return 1
                else:
                    return 0
            return
                
    else :
        logger.info("Analysis not reference")
        result_range = api.safe_getattr(analysis, "getResultsRange", None)
        if not result_range:
            return 0
        specs_lim = max(api.to_float(result_range.max, 0), api.to_float(result_range.min, 0))
        conc, dilution = getConcentrationAndDilution(sample)
        
        if not conc or not dilution:
            logger.info("Concentration or dilution not found")
            return
        
        mdv = (specs_lim * conc) / (sensitivity * dilution)        
        for interim in interim_fields:
            if not is_interim_editable(interim):
                continue
            if interim.get("keyword", "") == "mdv":
                interim.update({"value": str(mdv)})
        max_dilution = 0
        for interim in interim_fields:
            if not is_interim_editable(interim):
                continue
            if interim.get("keyword", "") == "dmdv":
                dmdv = interim["value"]
                if dmdv not in [None, "", 0, "0"]:
                    interim.update({"value": str(mdv)})
            if interim.get("keyword", "")[0] == "d":
                try:
                    max_dilution = max(max_dilution, api.to_float(interim["value"], 1))
                except ValueError:
                    logger.error("Invalid interim field value: %s" % interim["value"])
                    
        analysis.setInterimFields(interim_fields)
        result_ue_ml = max_dilution * sensitivity
        #logger.info("LAL result in UE/ml: %s" % result_ue_ml)
        result_ue_mg = result_ue_ml * dilution / conc
        return result_ue_mg
    
def getConcentrationAndDilution(sample):
    samplematrix = sample.getSampleType().getSampleMatrix()
    if not samplematrix:
        return None
    logger.info("Sample matrix: %s" % samplematrix.__dict__)
    logger.info("Variables table: %s" % samplematrix.variables_dict)
    dict_variables = samplematrix.variables_dict
    if not dict_variables:
        return None
    concentration = dict_variables.get('LAL',{}).get('lal_concentration', None)
    dilution = dict_variables.get('LAL', {}).get('lal_dilution',1)
    
    logger.info("Concentration: %s, Dilution: %s" % (concentration, dilution))
    return concentration, dilution