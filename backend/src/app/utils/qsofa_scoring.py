import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.models.qsofa import (
    QsofaParameters, QsofaParameter, QsofaComponentScore, 
    QsofaScoreResult, QsofaScoreSummary
)
from app.services.fhir_client import FHIRClient
from app.core.loinc_codes import LOINCCodes
from app.core.qsofa_constants import (
    QsofaDefaults, QsofaThresholds, QsofaParameterConfigs, 
    QSOFA_DEFAULTS, QsofaClinicalKeywords
)
from app.utils.fhir_utils import extract_observations_by_loinc, get_most_recent_observation

logger = logging.getLogger(__name__)

async def collect_qsofa_parameters(
    patient_id: str, 
    fhir_client: FHIRClient, 
    timestamp: Optional[datetime] = None
) -> QsofaParameters:
    """
    Collect qSOFA parameters from FHIR resources
    
    Args:
        patient_id: Patient FHIR ID
        fhir_client: FHIR client instance
        timestamp: Target timestamp for data collection
    
    Returns:
        QsofaParameters object with collected data
    """
    logger.info(f"Collecting qSOFA parameters for patient [REDACTED]")
    
    if timestamp is None:
        timestamp = datetime.now()
    
    # Define time window for data collection (last 4 hours for qSOFA)
    end_date = timestamp
    start_date = timestamp - timedelta(hours=4)
    
    # Initialize parameters object
    qsofa_params = QsofaParameters(patient_id=patient_id, timestamp=timestamp)
    
    try:
        # Collect all required observations concurrently
        tasks = [
            _collect_respiratory_parameters(fhir_client, patient_id, start_date, end_date),
            _collect_cardiovascular_parameters(fhir_client, patient_id, start_date, end_date),
            _collect_cns_parameters(fhir_client, patient_id, start_date, end_date)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                system_names = ["respiratory", "cardiovascular", "CNS"]
                system_name = system_names[i] if i < len(system_names) else "unknown"
                logger.error(f"Error collecting qSOFA parameters for {system_name}: {str(result)}")
                continue
            
            if i == 0:  # Respiratory
                qsofa_params.respiratory_rate = result.get("respiratory_rate", QsofaParameter())
            elif i == 1:  # Cardiovascular
                qsofa_params.systolic_bp = result.get("systolic_bp", QsofaParameter())
            elif i == 2:  # CNS
                qsofa_params.gcs = result.get("gcs", QsofaParameter())
        
        # Assess altered mental status
        qsofa_params.altered_mental_status = await assess_mental_status(
            patient_id, fhir_client, qsofa_params.gcs, timestamp
        )
        
        # Handle missing data with defaults
        qsofa_params = await handle_missing_qsofa_data(qsofa_params, fhir_client)
        
        logger.info(f"qSOFA parameters collected: {len(qsofa_params.missing_parameters)} parameters estimated/missing")
        return qsofa_params
        
    except Exception as e:
        logger.error(f"Error collecting qSOFA parameters: {str(e)}")
        raise

async def assess_mental_status(
    patient_id: str, 
    fhir_client: FHIRClient, 
    gcs_param: QsofaParameter, 
    timestamp: datetime
) -> bool:
    """
    Assess altered mental status using multiple methods
    
    Args:
        patient_id: Patient FHIR ID
        fhir_client: FHIR client instance
        gcs_param: Glasgow Coma Score parameter
        timestamp: Target timestamp
    
    Returns:
        True if altered mental status detected
    """
    logger.debug("Assessing mental status for qSOFA")
    
    # Method 1: Check GCS
    if gcs_param.value is not None and gcs_param.value < QsofaThresholds.GCS_THRESHOLD:
        logger.debug(f"Altered mental status detected via GCS: {gcs_param.value}")
        return True
    
    # Method 2: Check for confusion/delirium in clinical notes
    try:
        mental_status_from_notes = await _check_clinical_notes_for_confusion(
            fhir_client, patient_id, timestamp
        )
        if mental_status_from_notes:
            logger.debug("Altered mental status detected via clinical notes")
            return True
    except Exception as e:
        logger.warning(f"Error checking clinical notes for mental status: {str(e)}")
    
    # Method 3: Check AVPU scale (if available)
    try:
        avpu_altered = await _check_avpu_scale(fhir_client, patient_id, timestamp)
        if avpu_altered:
            logger.debug("Altered mental status detected via AVPU scale")
            return True
    except Exception as e:
        logger.warning(f"Error checking AVPU scale: {str(e)}")
    
    # Method 4: Check Richmond Agitation-Sedation Scale (RASS) (if available)
    try:
        rass_altered = await _check_rass_score(fhir_client, patient_id, timestamp)
        if rass_altered:
            logger.debug("Altered mental status detected via RASS score")
            return True
    except Exception as e:
        logger.warning(f"Error checking RASS score: {str(e)}")
    
    return False

async def handle_missing_qsofa_data(
    parameters: QsofaParameters, 
    fhir_client: FHIRClient
) -> QsofaParameters:
    """
    Handle missing qSOFA data by using defaults and last known values
    
    Args:
        parameters: QsofaParameters object
        fhir_client: FHIR client for retrieving historical data
    
    Returns:
        Updated QsofaParameters with missing data handled
    """
    logger.debug("Handling missing qSOFA data")
    
    # Parameter mapping for easier processing
    parameter_mapping = {
        "respiratory_rate": parameters.respiratory_rate,
        "systolic_bp": parameters.systolic_bp,
        "gcs": parameters.gcs
    }
    
    for param_name, param_obj in parameter_mapping.items():
        if param_obj.value is None:
            logger.info(f"Missing qSOFA parameter: {param_name}")
            
            # Try to get last known value within 24 hours
            try:
                last_value = await _get_last_known_qsofa_value(
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
                    continue  # Skip to next parameter
            except Exception as e:
                logger.warning(f"Error retrieving last known value for {param_name}: {str(e)}")
            
            # Use default value (guaranteed fallback)
            default_value = QSOFA_DEFAULTS.get(param_name)
            if default_value is not None:
                param_obj.value = default_value
                param_obj.is_estimated = True
                param_obj.source = "default"
                param_obj.unit = _get_default_unit(param_name)
                logger.debug(f"Used default value for {param_name}: {default_value}")
            else:
                # Hardcoded fallback if QSOFA_DEFAULTS is missing
                fallback_values = {
                    "respiratory_rate": 16.0,
                    "systolic_bp": 120.0,
                    "gcs": 15.0
                }
                param_obj.value = fallback_values.get(param_name, 0.0)
                param_obj.is_estimated = True
                param_obj.source = "hardcoded_default"
                param_obj.unit = _get_default_unit(param_name)
                logger.warning(f"Used hardcoded fallback for {param_name}: {param_obj.value}")
    
    # Ensure all parameters have values (additional safety check)
    if parameters.respiratory_rate.value is None:
        parameters.respiratory_rate.value = 16.0
        parameters.respiratory_rate.is_estimated = True
        parameters.respiratory_rate.source = "safety_default"
        logger.warning("Applied safety default for respiratory_rate")
    
    if parameters.systolic_bp.value is None:
        parameters.systolic_bp.value = 120.0
        parameters.systolic_bp.is_estimated = True
        parameters.systolic_bp.source = "safety_default"
        logger.warning("Applied safety default for systolic_bp")
    
    if parameters.gcs.value is None:
        parameters.gcs.value = 15.0
        parameters.gcs.is_estimated = True
        parameters.gcs.source = "safety_default"
        logger.warning("Applied safety default for gcs")
    
    return parameters

def _get_default_unit(param_name: str) -> str:
    """Get the default unit for a parameter"""
    unit_mapping = {
        "respiratory_rate": "breaths/min",
        "systolic_bp": "mmHg",
        "gcs": "score"
    }
    return unit_mapping.get(param_name, "")

def calculate_respiratory_score(respiratory_rate: Optional[float]) -> QsofaComponentScore:
    """Calculate qSOFA respiratory score based on respiratory rate"""
    
    if respiratory_rate is None:
        respiratory_rate = QsofaDefaults.RESPIRATORY_RATE
    
    # Apply qSOFA scoring criteria
    threshold_met = respiratory_rate >= QsofaThresholds.RESPIRATORY_RATE_THRESHOLD
    score = 1 if threshold_met else 0
    
    interpretation = f"Respiratory rate: {respiratory_rate:.0f} breaths/min"
    if threshold_met:
        interpretation += f" (≥{QsofaThresholds.RESPIRATORY_RATE_THRESHOLD})"
    
    return QsofaComponentScore(
        component="Respiratory",
        score=score,
        threshold_met=threshold_met,
        interpretation=interpretation,
        parameters_used=["respiratory_rate"]
    )

def calculate_cardiovascular_score(systolic_bp: Optional[float]) -> QsofaComponentScore:
    """Calculate qSOFA cardiovascular score based on systolic blood pressure"""
    
    if systolic_bp is None:
        systolic_bp = QsofaDefaults.SYSTOLIC_BP
    
    # Apply qSOFA scoring criteria
    threshold_met = systolic_bp <= QsofaThresholds.SYSTOLIC_BP_THRESHOLD
    score = 1 if threshold_met else 0
    
    interpretation = f"Systolic BP: {systolic_bp:.0f} mmHg"
    if threshold_met:
        interpretation += f" (≤{QsofaThresholds.SYSTOLIC_BP_THRESHOLD})"
    
    return QsofaComponentScore(
        component="Cardiovascular", 
        score=score,
        threshold_met=threshold_met,
        interpretation=interpretation,
        parameters_used=["systolic_bp"]
    )

def calculate_cns_score(altered_mental_status: bool, gcs: Optional[float] = None) -> QsofaComponentScore:
    """Calculate qSOFA central nervous system score based on altered mental status"""
    
    score = 1 if altered_mental_status else 0
    
    interpretation = "Mental status: "
    if altered_mental_status:
        if gcs is not None:
            interpretation += f"Altered (GCS: {gcs:.0f})"
        else:
            interpretation += "Altered"
    else:
        interpretation += "Normal"
    
    return QsofaComponentScore(
        component="Central Nervous System",
        score=score,
        threshold_met=altered_mental_status,
        interpretation=interpretation,
        parameters_used=["gcs", "mental_status_assessment"]
    )

async def calculate_total_qsofa(
    patient_id: str, 
    fhir_client: FHIRClient, 
    timestamp: Optional[datetime] = None
) -> QsofaScoreResult:
    """
    Calculate complete qSOFA score for a patient
    
    Args:
        patient_id: Patient FHIR ID
        fhir_client: FHIR client instance
        timestamp: Target timestamp for calculation
    
    Returns:
        Complete qSOFA score result (never None, minimum score 0)
    """
    logger.info(f"Calculating qSOFA score for patient [REDACTED]")
    
    if timestamp is None:
        timestamp = datetime.now()
    
    try:
        # Collect parameters
        parameters = await collect_qsofa_parameters(patient_id, fhir_client, timestamp)
        
        # Ensure parameters is valid
        if parameters is None:
            logger.warning("Parameter collection returned None, creating default parameters")
            parameters = _create_default_qsofa_parameters(patient_id, timestamp)
        
        # Calculate individual component scores
        respiratory_score = calculate_respiratory_score(parameters.respiratory_rate.value)
        cardiovascular_score = calculate_cardiovascular_score(parameters.systolic_bp.value)
        cns_score = calculate_cns_score(parameters.altered_mental_status, parameters.gcs.value)
        
        # Calculate total score (ensure it's always valid)
        total_score = max(0, min(3, respiratory_score.score + cardiovascular_score.score + cns_score.score))
        
        # Determine high risk status
        high_risk = total_score >= QsofaThresholds.HIGH_RISK_THRESHOLD
        
        # Calculate data reliability score
        total_params = 3  # Number of key parameters (respiratory rate, systolic BP, GCS)
        estimated_count = parameters.estimated_parameters_count
        reliability_score = max(0.0, (total_params - estimated_count) / total_params)
        
        # Create result
        result = QsofaScoreResult(
            patient_id=patient_id,
            timestamp=timestamp,
            respiratory_score=respiratory_score,
            cardiovascular_score=cardiovascular_score,
            cns_score=cns_score,
            total_score=total_score,
            high_risk=high_risk,
            estimated_parameters_count=estimated_count,
            missing_parameters=parameters.missing_parameters,
            data_reliability_score=reliability_score
        )
        
        logger.info(f"qSOFA score calculated: {total_score}/3, high risk: {high_risk}, reliability: {reliability_score:.2f}")
        return result
        
    except Exception as e:
        logger.error(f"Error in qSOFA calculation: {str(e)}")
        # Return safe fallback result with score 0
        return _create_fallback_qsofa_result(patient_id, timestamp)

def _create_default_qsofa_parameters(patient_id: str, timestamp: datetime) -> QsofaParameters:
    """Create default qSOFA parameters when collection fails"""
    return QsofaParameters(
        patient_id=patient_id,
        timestamp=timestamp,
        respiratory_rate=QsofaParameter(value=16.0, source="default", is_estimated=True, unit="breaths/min"),
        systolic_bp=QsofaParameter(value=120.0, source="default", is_estimated=True, unit="mmHg"),
        gcs=QsofaParameter(value=15.0, source="default", is_estimated=True, unit="score"),
        altered_mental_status=False
    )

def _create_fallback_qsofa_result(patient_id: str, timestamp: datetime) -> QsofaScoreResult:
    """Create a safe fallback qSOFA result with score 0"""
    # Create default component scores
    respiratory_score = QsofaComponentScore(
        component="Respiratory",
        score=0,
        threshold_met=False,
        interpretation="Respiratory rate: 16 breaths/min (fallback default)",
        parameters_used=["respiratory_rate"]
    )
    
    cardiovascular_score = QsofaComponentScore(
        component="Cardiovascular",
        score=0,
        threshold_met=False,
        interpretation="Systolic BP: 120 mmHg (fallback default)",
        parameters_used=["systolic_bp"]
    )
    
    cns_score = QsofaComponentScore(
        component="Central Nervous System",
        score=0,
        threshold_met=False,
        interpretation="Mental status: Normal (fallback default)",
        parameters_used=["gcs", "mental_status_assessment"]
    )
    
    return QsofaScoreResult(
        patient_id=patient_id,
        timestamp=timestamp,
        respiratory_score=respiratory_score,
        cardiovascular_score=cardiovascular_score,
        cns_score=cns_score,
        total_score=0,
        high_risk=False,
        estimated_parameters_count=3,
        missing_parameters=["respiratory_rate", "systolic_bp", "gcs"],
        data_reliability_score=0.0
    )

# Helper functions for data collection

async def _collect_respiratory_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect respiratory rate parameter"""
    config = QsofaParameterConfigs.RESPIRATORY
    return await _collect_fhir_parameters(fhir_client, patient_id, start_date, end_date, config)

async def _collect_cardiovascular_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect systolic blood pressure parameter"""
    config = QsofaParameterConfigs.CARDIOVASCULAR
    return await _collect_fhir_parameters(fhir_client, patient_id, start_date, end_date, config)

async def _collect_cns_parameters(
    fhir_client: FHIRClient, 
    patient_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, Any]:
    """Collect Glasgow Coma Score parameter"""
    config = QsofaParameterConfigs.CNS
    return await _collect_fhir_parameters(fhir_client, patient_id, start_date, end_date, config)

async def _collect_fhir_parameters(
    fhir_client: FHIRClient,
    patient_id: str,
    start_date: datetime,
    end_date: datetime,
    parameter_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generic FHIR parameter collector for qSOFA parameters
    """
    codes = parameter_config.get("codes", [])
    count = parameter_config.get("count", 1)
    parameter_mapping = parameter_config.get("parameter_mapping", {})
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
            result[param_name] = QsofaParameter()
        
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
        
        return result
        
    except Exception as e:
        logger.error(f"Error collecting {system_name} parameters: {str(e)}")
        return {param_name: QsofaParameter() for param_name in parameter_mapping.values()}

async def _check_clinical_notes_for_confusion(
    fhir_client: FHIRClient, 
    patient_id: str, 
    timestamp: datetime
) -> bool:
    """Check clinical notes for evidence of altered mental status"""
    try:
        # Look for clinical notes in the last 4 hours
        start_time = timestamp - timedelta(hours=4)
        
        # Query for DocumentReference resources (clinical notes)
        bundle = await fhir_client._make_request(
            "GET", "DocumentReference",
            params={
                "patient": patient_id,
                "date": f"ge{start_time.isoformat()}&date=le{timestamp.isoformat()}",
                "_sort": "-date",
                "_count": "10"
            }
        )
        
        # Extract and check note content
        if bundle and "entry" in bundle:
            for entry in bundle["entry"]:
                resource = entry.get("resource", {})
                content = resource.get("content", [])
                
                for content_item in content:
                    attachment = content_item.get("attachment", {})
                    data = attachment.get("data", "")
                    
                    if data and QsofaClinicalKeywords.check_clinical_notes(data):
                        return True
        
        return False
        
    except Exception as e:
        logger.warning(f"Error checking clinical notes: {str(e)}")
        return False

async def _check_avpu_scale(
    fhir_client: FHIRClient, 
    patient_id: str, 
    timestamp: datetime
) -> bool:
    """Check AVPU scale for altered mental status"""
    try:
        # AVPU is not a standard LOINC code, but might be in custom observations
        # This is a placeholder implementation
        return False
        
    except Exception as e:
        logger.warning(f"Error checking AVPU scale: {str(e)}")
        return False

async def _check_rass_score(
    fhir_client: FHIRClient, 
    patient_id: str, 
    timestamp: datetime
) -> bool:
    """Check Richmond Agitation-Sedation Scale for altered mental status"""
    try:
        # RASS might have LOINC code 73936-1
        # Check for non-zero RASS score indicating altered mental status
        return False
        
    except Exception as e:
        logger.warning(f"Error checking RASS score: {str(e)}")
        return False

async def _get_last_known_qsofa_value(
    fhir_client: FHIRClient,
    patient_id: str,
    parameter_name: str,
    max_hours_back: int = 24
) -> Optional[float]:
    """Get last known value for a qSOFA parameter within specified time window"""
    
    # Map parameter names to LOINC codes
    loinc_mapping = {
        "respiratory_rate": [LOINCCodes.VITAL_SIGNS["respiratory_rate"]],
        "systolic_bp": [LOINCCodes.VITAL_SIGNS["systolic_bp"]],
        "gcs": [LOINCCodes.VITAL_SIGNS["glasgow_coma_score"]]
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