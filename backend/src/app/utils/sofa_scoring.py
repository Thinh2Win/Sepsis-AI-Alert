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
from app.core.sofa_constants import (
    SofaDefaults, SofaThresholds, SofaParameterConfigs, SOFA_DEFAULTS
)
from app.utils.fhir_utils import extract_observations_by_loinc, get_most_recent_observation
from app.utils.calculations import calculate_mean_arterial_pressure

logger = logging.getLogger(__name__)

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
        # Assume room air if not specified
        ratio = pao2 / SofaDefaults.ROOM_AIR_FIO2
    else:
        ratio = SofaDefaults.PAO2_FIO2_RATIO
    
    # Apply SOFA scoring criteria using thresholds
    thresholds = SofaThresholds.RESPIRATORY
    if ratio >= thresholds["normal"]:
        score = 0
    elif ratio >= thresholds["mild"]:
        score = 1
    elif ratio >= thresholds["moderate"]:
        score = 2
    elif ratio >= thresholds["severe"] and on_ventilation:
        score = 3
    elif ratio < thresholds["severe"] and on_ventilation:
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
        platelets = SofaDefaults.PLATELETS
    
    # Apply SOFA scoring criteria using thresholds
    thresholds = SofaThresholds.COAGULATION
    if platelets >= thresholds["normal"]:
        score = 0
    elif platelets >= thresholds["mild"]:
        score = 1
    elif platelets >= thresholds["moderate"]:
        score = 2
    elif platelets >= thresholds["severe"]:
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
        bilirubin = SofaDefaults.BILIRUBIN
    
    # Apply SOFA scoring criteria using thresholds
    thresholds = SofaThresholds.LIVER
    if bilirubin < thresholds["normal"]:
        score = 0
    elif bilirubin < thresholds["mild"]:
        score = 1
    elif bilirubin < thresholds["moderate"]:
        score = 2
    elif bilirubin < thresholds["severe"]:
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
        map_value = SofaDefaults.MAP
    
    # Check vasopressor administration first using thresholds
    vasopressor_info = []
    thresholds = SofaThresholds.VASOPRESSOR
    
    # High-dose vasopressors (score 4)
    if (vasopressor_doses.dopamine and vasopressor_doses.dopamine > thresholds["high_dopamine"]) or \
       (vasopressor_doses.epinephrine and vasopressor_doses.epinephrine > thresholds["epi_norepi"]) or \
       (vasopressor_doses.norepinephrine and vasopressor_doses.norepinephrine > thresholds["epi_norepi"]):
        score = 4
        vasopressor_info.append("High-dose vasopressors")
    
    # Medium-dose dopamine (score 3)
    elif vasopressor_doses.dopamine and vasopressor_doses.dopamine > thresholds["low_dopamine"]:
        score = 3
        vasopressor_info.append(f"Dopamine {vasopressor_doses.dopamine:.1f} mcg/kg/min")
    
    # Low-dose dopamine (score 2)
    elif vasopressor_doses.dopamine and vasopressor_doses.dopamine <= thresholds["low_dopamine"]:
        score = 2
        vasopressor_info.append(f"Dopamine {vasopressor_doses.dopamine:.1f} mcg/kg/min")
    
    # No vasopressors - check MAP
    elif map_value < SofaThresholds.CARDIOVASCULAR["normal_map"]:
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
        gcs = SofaDefaults.GCS
    
    # Apply SOFA scoring criteria using thresholds
    thresholds = SofaThresholds.CNS
    if gcs >= thresholds["normal"]:
        score = 0
    elif gcs >= thresholds["mild"]:
        score = 1
    elif gcs >= thresholds["moderate"]:
        score = 2
    elif gcs >= thresholds["severe"]:
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
        creatinine = SofaDefaults.CREATININE
    if urine_output_24h is None:
        urine_output_24h = SofaDefaults.URINE_OUTPUT
    
    # Check creatinine levels using thresholds
    creat_thresholds = SofaThresholds.RENAL["creatinine"]
    if creatinine < creat_thresholds["normal"]:
        creatinine_score = 0
    elif creatinine < creat_thresholds["mild"]:
        creatinine_score = 1
    elif creatinine < creat_thresholds["moderate"]:
        creatinine_score = 2
    elif creatinine < creat_thresholds["severe"]:
        creatinine_score = 3
    else:
        creatinine_score = 4
    
    # Check urine output using thresholds
    urine_thresholds = SofaThresholds.RENAL["urine_output"]
    if urine_output_24h < urine_thresholds["oliguria"]:
        urine_score = 4
    elif urine_output_24h < urine_thresholds["normal"]:
        urine_score = 3
    else:
        urine_score = 0
    
    # Return the worse score
    score = max(creatinine_score, urine_score)
    
    interpretation_parts = [f"Creatinine: {creatinine:.1f} mg/dL"]
    if urine_output_24h < urine_thresholds["normal"]:
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

async def _collect_fhir_parameters(
    fhir_client: FHIRClient,
    patient_id: str,
    start_date: datetime,
    end_date: datetime,
    parameter_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generic FHIR parameter collector that eliminates code duplication
    
    Args:
        fhir_client: FHIR client instance
        patient_id: Patient FHIR ID
        start_date: Start date for data collection
        end_date: End date for data collection
        parameter_config: Configuration dict with:
            - codes: List of LOINC codes to search for
            - count: Number of results to return (default: 1)
            - parameter_mapping: Dict mapping LOINC codes to parameter names
            - extra_data: Dict of additional static data to return
    
    Returns:
        Dict with collected parameters as SofaParameter objects
    """
    codes = parameter_config.get("codes", [])
    count = parameter_config.get("count", 1)
    parameter_mapping = parameter_config.get("parameter_mapping", {})
    extra_data = parameter_config.get("extra_data", {})
    system_name = parameter_config.get("system_name", "unknown")
    
    try:
        bundle = await fhir_client._make_request(
            "GET", "Observation",
            params={
                "patient": patient_id,
                "code": ",".join(codes),
                "date": f"ge{start_date.isoformat()}&date=le{end_date.isoformat()}",
                "_sort": "-date",
                "_count": str(count)
            }
        )
        
        observations = extract_observations_by_loinc(bundle, codes)
        result = {}
        
        # Initialize all expected parameters
        for loinc_code, param_name in parameter_mapping.items():
            result[param_name] = SofaParameter()
        
        # Process observations
        for obs in observations:
            loinc_code = obs.get("loinc_code")
            param_name = parameter_mapping.get(loinc_code)
            
            if param_name and param_name in result:
                param = result[param_name]
                if param.value is None:  # Use most recent value only
                    param.value = obs.get("value")
                    param.unit = obs.get("unit")
                    param.timestamp = obs.get("timestamp")
                    param.source = "measured"
        
        # Add any extra static data
        result.update(extra_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Error collecting {system_name} parameters: {str(e)}")
        return {param_name: SofaParameter() for param_name in parameter_mapping.values()}

async def _collect_respiratory_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect respiratory system parameters"""
    config = SofaParameterConfigs.RESPIRATORY.copy()
    config["extra_data"] = {
        "mechanical_ventilation": False,  # TODO: Add detection from procedures
        "pao2": SofaParameter(),
        "fio2": SofaParameter()
    }
    
    return await _collect_fhir_parameters(fhir_client, patient_id, start_date, end_date, config)

async def _collect_coagulation_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect coagulation system parameters"""
    return await _collect_fhir_parameters(
        fhir_client, patient_id, start_date, end_date, SofaParameterConfigs.COAGULATION
    )

async def _collect_liver_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect liver system parameters"""
    return await _collect_fhir_parameters(
        fhir_client, patient_id, start_date, end_date, SofaParameterConfigs.LIVER
    )

async def _collect_cardiovascular_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect cardiovascular system parameters"""
    config = SofaParameterConfigs.CARDIOVASCULAR.copy()
    config["extra_data"] = {"map_value": SofaParameter()}
    
    result = await _collect_fhir_parameters(fhir_client, patient_id, start_date, end_date, config)
    
    # Calculate MAP if both BP values available
    systolic_bp = result.get("systolic_bp")
    diastolic_bp = result.get("diastolic_bp")
    
    if (systolic_bp and systolic_bp.value and 
        diastolic_bp and diastolic_bp.value):
        calculated_map = calculate_mean_arterial_pressure(systolic_bp.value, diastolic_bp.value)
        if calculated_map:
            map_value = result["map_value"]
            map_value.value = calculated_map
            map_value.unit = "mmHg"
            map_value.timestamp = max(
                systolic_bp.timestamp or datetime.min, 
                diastolic_bp.timestamp or datetime.min
            )
            map_value.source = "calculated"
    
    return result

async def _collect_cns_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect central nervous system parameters"""
    return await _collect_fhir_parameters(
        fhir_client, patient_id, start_date, end_date, SofaParameterConfigs.CNS
    )

async def _collect_renal_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect renal system parameters"""
    return await _collect_fhir_parameters(
        fhir_client, patient_id, start_date, end_date, SofaParameterConfigs.RENAL
    )

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
        
        # TODO: Extract actual dosing information from medication administrations
        # This would require parsing dosage instructions and administration records
        return {"vasopressor_doses": VasopressorDoses()}
        
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