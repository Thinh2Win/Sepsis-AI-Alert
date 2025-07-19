import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.models.sofa import (
    SofaParameters, SofaParameter, VasopressorDoses, SofaComponentScore, 
    SofaScoreResult, SofaScoreResponse
)
from app.services.fhir_client import FHIRClient
from app.core.loinc_codes import LOINCCodes
from app.utils.fhir_utils import extract_observations_by_loinc, get_most_recent_observation
from app.utils.calculations import calculate_mean_arterial_pressure

logger = logging.getLogger(__name__)

# SOFA default values for missing parameters
SOFA_DEFAULTS = {
    "pao2_fio2_ratio": 400.0,  # Normal ratio
    "platelets": 150.0,        # Normal platelet count (10^3/μL)
    "bilirubin": 1.0,          # Normal bilirubin (mg/dL)
    "map": 70.0,               # Normal MAP (mmHg)
    "gcs": 15.0,               # Normal GCS
    "creatinine": 1.0,         # Normal creatinine (mg/dL)
    "urine_output": 1000.0     # Normal urine output (mL/24h)
}

async def collect_sofa_parameters(
    patient_id: str, 
    fhir_client: FHIRClient, 
    timestamp: Optional[datetime] = None
) -> SofaParameters:
    """
    Collect SOFA parameters from FHIR resources
    
    Args:
        patient_id: Patient FHIR ID
        fhir_client: FHIR client instance
        timestamp: Target timestamp for data collection
    
    Returns:
        SofaParameters object with collected data
    """
    logger.info(f"Collecting SOFA parameters for patient [REDACTED]")
    
    if timestamp is None:
        timestamp = datetime.now()
    
    # Define time window for data collection (last 24 hours)
    end_date = timestamp
    start_date = timestamp - timedelta(hours=24)
    
    # Initialize parameters object
    sofa_params = SofaParameters(patient_id=patient_id, timestamp=timestamp)
    
    try:
        # Collect all required observations concurrently
        tasks = [
            _collect_respiratory_parameters(fhir_client, patient_id, start_date, end_date),
            _collect_coagulation_parameters(fhir_client, patient_id, start_date, end_date),
            _collect_liver_parameters(fhir_client, patient_id, start_date, end_date),
            _collect_cardiovascular_parameters(fhir_client, patient_id, start_date, end_date),
            _collect_cns_parameters(fhir_client, patient_id, start_date, end_date),
            _collect_renal_parameters(fhir_client, patient_id, start_date, end_date),
            _collect_vasopressor_data(fhir_client, patient_id, start_date, end_date)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error collecting SOFA parameter group {i}: {str(result)}")
                continue
            
            if i == 0:  # Respiratory
                sofa_params.pao2 = result.get("pao2", SofaParameter())
                sofa_params.fio2 = result.get("fio2", SofaParameter())
                sofa_params.pao2_fio2_ratio = result.get("pao2_fio2_ratio", SofaParameter())
                sofa_params.mechanical_ventilation = result.get("mechanical_ventilation", False)
            elif i == 1:  # Coagulation
                sofa_params.platelets = result.get("platelets", SofaParameter())
            elif i == 2:  # Liver
                sofa_params.bilirubin = result.get("bilirubin", SofaParameter())
            elif i == 3:  # Cardiovascular
                sofa_params.map_value = result.get("map_value", SofaParameter())
                sofa_params.systolic_bp = result.get("systolic_bp", SofaParameter())
                sofa_params.diastolic_bp = result.get("diastolic_bp", SofaParameter())
            elif i == 4:  # CNS
                sofa_params.gcs = result.get("gcs", SofaParameter())
            elif i == 5:  # Renal
                sofa_params.creatinine = result.get("creatinine", SofaParameter())
                sofa_params.urine_output_24h = result.get("urine_output_24h", SofaParameter())
            elif i == 6:  # Vasopressors
                sofa_params.vasopressor_doses = result.get("vasopressor_doses", VasopressorDoses())
        
        # Handle missing data
        sofa_params = await handle_missing_sofa_data(sofa_params, fhir_client)
        
        logger.info(f"SOFA parameters collected: {len(sofa_params.missing_parameters)} parameters estimated/missing")
        return sofa_params
        
    except Exception as e:
        logger.error(f"Error collecting SOFA parameters: {str(e)}")
        raise

async def handle_missing_sofa_data(
    parameters: SofaParameters, 
    fhir_client: FHIRClient
) -> SofaParameters:
    """
    Handle missing SOFA data by using defaults and last known values
    
    Args:
        parameters: SofaParameters object
        fhir_client: FHIR client for retrieving historical data
    
    Returns:
        Updated SofaParameters with missing data handled
    """
    logger.debug("Handling missing SOFA data")
    
    # Parameter mapping for easier processing
    parameter_mapping = {
        "pao2_fio2_ratio": parameters.pao2_fio2_ratio,
        "platelets": parameters.platelets,
        "bilirubin": parameters.bilirubin,
        "map_value": parameters.map_value,
        "gcs": parameters.gcs,
        "creatinine": parameters.creatinine,
        "urine_output_24h": parameters.urine_output_24h
    }
    
    for param_name, param_obj in parameter_mapping.items():
        if param_obj.value is None:
            logger.info(f"Missing SOFA parameter: {param_name}")
            
            # Try to get last known value within 24 hours
            last_value = await _get_last_known_value(
                fhir_client, 
                parameters.patient_id, 
                param_name, 
                max_hours_back=24
            )
            
            if last_value is not None:
                param_obj.value = last_value
                param_obj.source = "last_known"
                param_obj.last_known_value = last_value
                logger.debug(f"Used last known value for {param_name}: {last_value}")
            else:
                # Use default value
                default_value = SOFA_DEFAULTS.get(param_name)
                if default_value is not None:
                    param_obj.value = default_value
                    param_obj.is_estimated = True
                    param_obj.source = "default"
                    logger.debug(f"Used default value for {param_name}: {default_value}")
    
    # Special handling for MAP calculation
    if parameters.map_value.value is None and parameters.systolic_bp.value and parameters.diastolic_bp.value:
        calculated_map = calculate_mean_arterial_pressure(
            parameters.systolic_bp.value, 
            parameters.diastolic_bp.value
        )
        if calculated_map:
            parameters.map_value.value = calculated_map
            parameters.map_value.source = "calculated"
            logger.debug(f"Calculated MAP from BP: {calculated_map}")
    
    # Calculate PaO2/FiO2 ratio if missing but components available
    if (parameters.pao2_fio2_ratio.value is None and 
        parameters.pao2.value and parameters.fio2.value and parameters.fio2.value > 0):
        ratio = parameters.pao2.value / parameters.fio2.value
        parameters.pao2_fio2_ratio.value = ratio
        parameters.pao2_fio2_ratio.source = "calculated"
        logger.debug(f"Calculated PaO2/FiO2 ratio: {ratio}")
    
    return parameters

def calculate_respiratory_score(pao2: Optional[float], fio2: Optional[float], on_ventilation: bool) -> SofaComponentScore:
    """Calculate SOFA respiratory score based on PaO2/FiO2 ratio and ventilation status"""
    
    # Calculate ratio
    if pao2 and fio2 and fio2 > 0:
        ratio = pao2 / fio2
    elif pao2 and fio2 is None:
        # Assume room air (FiO2 = 0.21) if not specified
        ratio = pao2 / 0.21
    else:
        ratio = SOFA_DEFAULTS["pao2_fio2_ratio"]
    
    # Apply SOFA scoring criteria
    if ratio >= 400:
        score = 0
    elif ratio >= 300:
        score = 1
    elif ratio >= 200:
        score = 2
    elif ratio >= 100 and on_ventilation:
        score = 3
    elif ratio < 100 and on_ventilation:
        score = 4
    else:
        score = 0  # Default if not on ventilation and low ratio
    
    interpretation = f"PaO2/FiO2 ratio: {ratio:.1f}"
    if on_ventilation:
        interpretation += " (on mechanical ventilation)"
    
    return SofaComponentScore(
        organ_system="Respiratory",
        score=score,
        parameters_used=["pao2_fio2_ratio", "mechanical_ventilation"],
        interpretation=interpretation
    )

def calculate_coagulation_score(platelets: Optional[float]) -> SofaComponentScore:
    """Calculate SOFA coagulation score based on platelet count"""
    
    if platelets is None:
        platelets = SOFA_DEFAULTS["platelets"]
    
    # Apply SOFA scoring criteria (platelets in 10^3/μL)
    if platelets >= 150:
        score = 0
    elif platelets >= 100:
        score = 1
    elif platelets >= 50:
        score = 2
    elif platelets >= 20:
        score = 3
    else:
        score = 4
    
    return SofaComponentScore(
        organ_system="Coagulation",
        score=score,
        parameters_used=["platelets"],
        interpretation=f"Platelets: {platelets:.0f} x 10^3/uL"
    )

def calculate_liver_score(bilirubin: Optional[float]) -> SofaComponentScore:
    """Calculate SOFA liver score based on bilirubin level"""
    
    if bilirubin is None:
        bilirubin = SOFA_DEFAULTS["bilirubin"]
    
    # Apply SOFA scoring criteria (bilirubin in mg/dL)
    if bilirubin < 1.2:
        score = 0
    elif bilirubin < 2.0:
        score = 1
    elif bilirubin < 6.0:
        score = 2
    elif bilirubin < 12.0:
        score = 3
    else:
        score = 4
    
    return SofaComponentScore(
        organ_system="Liver",
        score=score,
        parameters_used=["bilirubin"],
        interpretation=f"Total bilirubin: {bilirubin:.1f} mg/dL"
    )

def calculate_cardiovascular_score(map_value: Optional[float], vasopressor_doses: VasopressorDoses) -> SofaComponentScore:
    """Calculate SOFA cardiovascular score based on MAP and vasopressor use"""
    
    if map_value is None:
        map_value = SOFA_DEFAULTS["map"]
    
    # Check vasopressor administration first (doses in mcg/kg/min)
    vasopressor_info = []
    
    # High-dose vasopressors (score 4)
    if (vasopressor_doses.dopamine and vasopressor_doses.dopamine > 15) or \
       (vasopressor_doses.epinephrine and vasopressor_doses.epinephrine > 0.1) or \
       (vasopressor_doses.norepinephrine and vasopressor_doses.norepinephrine > 0.1):
        score = 4
        vasopressor_info.append("High-dose vasopressors")
    
    # Medium-dose dopamine (score 3)
    elif vasopressor_doses.dopamine and vasopressor_doses.dopamine > 5:
        score = 3
        vasopressor_info.append(f"Dopamine {vasopressor_doses.dopamine:.1f} mcg/kg/min")
    
    # Low-dose dopamine (score 2)
    elif vasopressor_doses.dopamine and vasopressor_doses.dopamine <= 5:
        score = 2
        vasopressor_info.append(f"Dopamine {vasopressor_doses.dopamine:.1f} mcg/kg/min")
    
    # No vasopressors - check MAP
    elif map_value < 70:
        score = 1
    else:
        score = 0
    
    interpretation = f"MAP: {map_value:.0f} mmHg"
    if vasopressor_info:
        interpretation += f", {', '.join(vasopressor_info)}"
    
    return SofaComponentScore(
        organ_system="Cardiovascular",
        score=score,
        parameters_used=["map", "vasopressors"],
        interpretation=interpretation
    )

def calculate_cns_score(gcs: Optional[float]) -> SofaComponentScore:
    """Calculate SOFA central nervous system score based on Glasgow Coma Scale"""
    
    if gcs is None:
        gcs = SOFA_DEFAULTS["gcs"]
    
    # Apply SOFA scoring criteria
    if gcs >= 15:
        score = 0
    elif gcs >= 13:
        score = 1
    elif gcs >= 10:
        score = 2
    elif gcs >= 6:
        score = 3
    else:
        score = 4
    
    return SofaComponentScore(
        organ_system="Central Nervous System",
        score=score,
        parameters_used=["gcs"],
        interpretation=f"Glasgow Coma Scale: {gcs:.0f}"
    )

def calculate_renal_score(creatinine: Optional[float], urine_output_24h: Optional[float]) -> SofaComponentScore:
    """Calculate SOFA renal score based on creatinine and urine output"""
    
    if creatinine is None:
        creatinine = SOFA_DEFAULTS["creatinine"]
    if urine_output_24h is None:
        urine_output_24h = SOFA_DEFAULTS["urine_output"]
    
    # Check creatinine levels (mg/dL)
    if creatinine < 1.2:
        creatinine_score = 0
    elif creatinine < 2.0:
        creatinine_score = 1
    elif creatinine < 3.5:
        creatinine_score = 2
    elif creatinine < 5.0:
        creatinine_score = 3
    else:
        creatinine_score = 4
    
    # Check urine output (mL/day)
    if urine_output_24h < 200:
        urine_score = 4
    elif urine_output_24h < 500:
        urine_score = 3
    else:
        urine_score = 0
    
    # Return the worse score
    score = max(creatinine_score, urine_score)
    
    interpretation_parts = [f"Creatinine: {creatinine:.1f} mg/dL"]
    if urine_output_24h < 500:
        interpretation_parts.append(f"Urine output: {urine_output_24h:.0f} mL/24h")
    
    return SofaComponentScore(
        organ_system="Renal",
        score=score,
        parameters_used=["creatinine", "urine_output_24h"],
        interpretation=", ".join(interpretation_parts)
    )

async def calculate_total_sofa(
    patient_id: str, 
    fhir_client: FHIRClient, 
    timestamp: Optional[datetime] = None
) -> SofaScoreResult:
    """
    Calculate complete SOFA score for a patient
    
    Args:
        patient_id: Patient FHIR ID
        fhir_client: FHIR client instance
        timestamp: Target timestamp for calculation
    
    Returns:
        Complete SOFA score result
    """
    logger.info(f"Calculating SOFA score for patient [REDACTED]")
    
    if timestamp is None:
        timestamp = datetime.now()
    
    # Collect parameters
    parameters = await collect_sofa_parameters(patient_id, fhir_client, timestamp)
    
    # Calculate individual organ scores
    respiratory_score = calculate_respiratory_score(
        parameters.pao2.value,
        parameters.fio2.value,
        parameters.mechanical_ventilation
    )
    
    coagulation_score = calculate_coagulation_score(parameters.platelets.value)
    liver_score = calculate_liver_score(parameters.bilirubin.value)
    cardiovascular_score = calculate_cardiovascular_score(
        parameters.map_value.value,
        parameters.vasopressor_doses
    )
    cns_score = calculate_cns_score(parameters.gcs.value)
    renal_score = calculate_renal_score(
        parameters.creatinine.value,
        parameters.urine_output_24h.value
    )
    
    # Calculate total score
    total_score = (
        respiratory_score.score + coagulation_score.score + liver_score.score +
        cardiovascular_score.score + cns_score.score + renal_score.score
    )
    
    # Calculate data reliability score
    total_params = 7  # Number of key parameters
    estimated_count = parameters.estimated_parameters_count
    reliability_score = max(0.0, (total_params - estimated_count) / total_params)
    
    # Create result
    result = SofaScoreResult(
        patient_id=patient_id,
        timestamp=timestamp,
        respiratory_score=respiratory_score,
        coagulation_score=coagulation_score,
        liver_score=liver_score,
        cardiovascular_score=cardiovascular_score,
        cns_score=cns_score,
        renal_score=renal_score,
        total_score=total_score,
        estimated_parameters_count=estimated_count,
        missing_parameters=parameters.missing_parameters,
        data_reliability_score=reliability_score
    )
    
    logger.info(f"SOFA score calculated: {total_score}/24, reliability: {reliability_score:.2f}")
    return result

# Helper functions for data collection

async def _collect_respiratory_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect respiratory system parameters"""
    
    # Get PaO2/FiO2 ratio directly
    ratio_codes = ["50984-4"]  # PaO2/FiO2 ratio
    
    try:
        ratio_bundle = await fhir_client._make_request(
            "GET", "Observation",
            params={
                "patient": patient_id,
                "code": ",".join(ratio_codes),
                "date": f"ge{start_date.isoformat()}&date=le{end_date.isoformat()}",
                "_sort": "-date",
                "_count": "1"
            }
        )
        
        ratio_obs = extract_observations_by_loinc(ratio_bundle, ratio_codes)
        pao2_fio2_ratio = SofaParameter()
        
        if ratio_obs:
            recent_ratio = get_most_recent_observation(ratio_obs)
            if recent_ratio:
                pao2_fio2_ratio.value = recent_ratio.get("value")
                pao2_fio2_ratio.unit = recent_ratio.get("unit")
                pao2_fio2_ratio.timestamp = recent_ratio.get("timestamp")
                pao2_fio2_ratio.source = "measured"
        
        # TODO: Add mechanical ventilation detection from procedures
        mechanical_ventilation = False
        
        return {
            "pao2_fio2_ratio": pao2_fio2_ratio,
            "mechanical_ventilation": mechanical_ventilation,
            "pao2": SofaParameter(),  # Individual PaO2 if needed
            "fio2": SofaParameter()   # Individual FiO2 if needed
        }
        
    except Exception as e:
        logger.error(f"Error collecting respiratory parameters: {str(e)}")
        return {}

async def _collect_coagulation_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect coagulation system parameters"""
    
    platelet_codes = [LOINCCodes.CBC["platelet_count"]]  # 777-3
    
    try:
        platelet_bundle = await fhir_client._make_request(
            "GET", "Observation",
            params={
                "patient": patient_id,
                "code": ",".join(platelet_codes),
                "date": f"ge{start_date.isoformat()}&date=le{end_date.isoformat()}",
                "_sort": "-date",
                "_count": "1"
            }
        )
        
        platelet_obs = extract_observations_by_loinc(platelet_bundle, platelet_codes)
        platelets = SofaParameter()
        
        if platelet_obs:
            recent_platelet = get_most_recent_observation(platelet_obs)
            if recent_platelet:
                platelets.value = recent_platelet.get("value")
                platelets.unit = recent_platelet.get("unit")
                platelets.timestamp = recent_platelet.get("timestamp")
                platelets.source = "measured"
        
        return {"platelets": platelets}
        
    except Exception as e:
        logger.error(f"Error collecting coagulation parameters: {str(e)}")
        return {}

async def _collect_liver_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect liver system parameters"""
    
    bilirubin_codes = [LOINCCodes.LIVER["bilirubin_total"]]  # 1975-2
    
    try:
        bilirubin_bundle = await fhir_client._make_request(
            "GET", "Observation",
            params={
                "patient": patient_id,
                "code": ",".join(bilirubin_codes),
                "date": f"ge{start_date.isoformat()}&date=le{end_date.isoformat()}",
                "_sort": "-date",
                "_count": "1"
            }
        )
        
        bilirubin_obs = extract_observations_by_loinc(bilirubin_bundle, bilirubin_codes)
        bilirubin = SofaParameter()
        
        if bilirubin_obs:
            recent_bilirubin = get_most_recent_observation(bilirubin_obs)
            if recent_bilirubin:
                bilirubin.value = recent_bilirubin.get("value")
                bilirubin.unit = recent_bilirubin.get("unit")
                bilirubin.timestamp = recent_bilirubin.get("timestamp")
                bilirubin.source = "measured"
        
        return {"bilirubin": bilirubin}
        
    except Exception as e:
        logger.error(f"Error collecting liver parameters: {str(e)}")
        return {}

async def _collect_cardiovascular_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect cardiovascular system parameters"""
    
    bp_codes = [LOINCCodes.VITAL_SIGNS["systolic_bp"], LOINCCodes.VITAL_SIGNS["diastolic_bp"]]
    
    try:
        bp_bundle = await fhir_client._make_request(
            "GET", "Observation",
            params={
                "patient": patient_id,
                "code": ",".join(bp_codes),
                "date": f"ge{start_date.isoformat()}&date=le{end_date.isoformat()}",
                "_sort": "-date",
                "_count": "2"
            }
        )
        
        bp_obs = extract_observations_by_loinc(bp_bundle, bp_codes)
        
        systolic_bp = SofaParameter()
        diastolic_bp = SofaParameter()
        map_value = SofaParameter()
        
        # Process blood pressure observations
        for obs in bp_obs:
            if obs.get("loinc_code") == LOINCCodes.VITAL_SIGNS["systolic_bp"]:
                systolic_bp.value = obs.get("value")
                systolic_bp.unit = obs.get("unit")
                systolic_bp.timestamp = obs.get("timestamp")
                systolic_bp.source = "measured"
            elif obs.get("loinc_code") == LOINCCodes.VITAL_SIGNS["diastolic_bp"]:
                diastolic_bp.value = obs.get("value")
                diastolic_bp.unit = obs.get("unit")
                diastolic_bp.timestamp = obs.get("timestamp")
                diastolic_bp.source = "measured"
        
        # Calculate MAP if both values available
        if systolic_bp.value and diastolic_bp.value:
            calculated_map = calculate_mean_arterial_pressure(systolic_bp.value, diastolic_bp.value)
            if calculated_map:
                map_value.value = calculated_map
                map_value.unit = "mmHg"
                map_value.timestamp = max(systolic_bp.timestamp or datetime.min, diastolic_bp.timestamp or datetime.min)
                map_value.source = "calculated"
        
        return {
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "map_value": map_value
        }
        
    except Exception as e:
        logger.error(f"Error collecting cardiovascular parameters: {str(e)}")
        return {}

async def _collect_cns_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect central nervous system parameters"""
    
    gcs_codes = [LOINCCodes.VITAL_SIGNS["glasgow_coma_score"]]  # 9269-2
    
    try:
        gcs_bundle = await fhir_client._make_request(
            "GET", "Observation",
            params={
                "patient": patient_id,
                "code": ",".join(gcs_codes),
                "date": f"ge{start_date.isoformat()}&date=le{end_date.isoformat()}",
                "_sort": "-date",
                "_count": "1"
            }
        )
        
        gcs_obs = extract_observations_by_loinc(gcs_bundle, gcs_codes)
        gcs = SofaParameter()
        
        if gcs_obs:
            recent_gcs = get_most_recent_observation(gcs_obs)
            if recent_gcs:
                gcs.value = recent_gcs.get("value")
                gcs.unit = recent_gcs.get("unit")
                gcs.timestamp = recent_gcs.get("timestamp")
                gcs.source = "measured"
        
        return {"gcs": gcs}
        
    except Exception as e:
        logger.error(f"Error collecting CNS parameters: {str(e)}")
        return {}

async def _collect_renal_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect renal system parameters"""
    
    renal_codes = [
        LOINCCodes.METABOLIC["creatinine"],  # 2160-0
        LOINCCodes.FLUID_BALANCE["urine_output_24hr"]  # 9188-4
    ]
    
    try:
        renal_bundle = await fhir_client._make_request(
            "GET", "Observation",
            params={
                "patient": patient_id,
                "code": ",".join(renal_codes),
                "date": f"ge{start_date.isoformat()}&date=le{end_date.isoformat()}",
                "_sort": "-date",
                "_count": "2"
            }
        )
        
        renal_obs = extract_observations_by_loinc(renal_bundle, renal_codes)
        
        creatinine = SofaParameter()
        urine_output_24h = SofaParameter()
        
        for obs in renal_obs:
            if obs.get("loinc_code") == LOINCCodes.METABOLIC["creatinine"]:
                creatinine.value = obs.get("value")
                creatinine.unit = obs.get("unit")
                creatinine.timestamp = obs.get("timestamp")
                creatinine.source = "measured"
            elif obs.get("loinc_code") == LOINCCodes.FLUID_BALANCE["urine_output_24hr"]:
                urine_output_24h.value = obs.get("value")
                urine_output_24h.unit = obs.get("unit")
                urine_output_24h.timestamp = obs.get("timestamp")
                urine_output_24h.source = "measured"
        
        return {
            "creatinine": creatinine,
            "urine_output_24h": urine_output_24h
        }
        
    except Exception as e:
        logger.error(f"Error collecting renal parameters: {str(e)}")
        return {}

async def _collect_vasopressor_data(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect vasopressor medication data"""
    
    try:
        # Query for active vasopressor medications
        med_bundle = await fhir_client._make_request(
            "GET", "MedicationRequest",
            params={
                "patient": patient_id,
                "status": "active",
                "medication.code:text": "norepinephrine,epinephrine,dopamine,dobutamine,phenylephrine"
            }
        )
        
        vasopressor_doses = VasopressorDoses()
        
        # TODO: Extract actual dosing information from medication administrations
        # This would require parsing dosage instructions and administration records
        # For now, return empty vasopressor data
        
        return {"vasopressor_doses": vasopressor_doses}
        
    except Exception as e:
        logger.error(f"Error collecting vasopressor data: {str(e)}")
        return {"vasopressor_doses": VasopressorDoses()}

async def _get_last_known_value(
    fhir_client: FHIRClient,
    patient_id: str,
    parameter_name: str,
    max_hours_back: int = 24
) -> Optional[float]:
    """Get last known value for a parameter within specified time window"""
    
    # Map parameter names to LOINC codes
    loinc_mapping = {
        "pao2_fio2_ratio": ["50984-4"],
        "platelets": [LOINCCodes.CBC["platelet_count"]],
        "bilirubin": [LOINCCodes.LIVER["bilirubin_total"]],
        "gcs": [LOINCCodes.VITAL_SIGNS["glasgow_coma_score"]],
        "creatinine": [LOINCCodes.METABOLIC["creatinine"]],
        "urine_output_24h": [LOINCCodes.FLUID_BALANCE["urine_output_24hr"]]
    }
    
    codes = loinc_mapping.get(parameter_name)
    if not codes:
        return None
    
    try:
        cutoff_time = datetime.now() - timedelta(hours=max_hours_back)
        
        bundle = await fhir_client._make_request(
            "GET", "Observation",
            params={
                "patient": patient_id,
                "code": ",".join(codes),
                "date": f"ge{cutoff_time.isoformat()}",
                "_sort": "-date",
                "_count": "1"
            }
        )
        
        observations = extract_observations_by_loinc(bundle, codes)
        if observations:
            recent_obs = get_most_recent_observation(observations)
            return recent_obs.get("value") if recent_obs else None
        
        return None
        
    except Exception as e:
        logger.warning(f"Error getting last known value for {parameter_name}: {str(e)}")
        return None