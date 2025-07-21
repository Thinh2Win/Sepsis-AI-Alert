"""
NEWS2 (National Early Warning Score 2) Scoring Implementation

Optimized for data reuse from existing SOFA and qSOFA parameters to minimize
FHIR API calls while maintaining accurate NEWS2 calculations.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from app.models.news2 import (
    News2Parameters, News2Parameter, News2ComponentScore, 
    News2ScoreResult, News2ScoreSummary, News2RiskAssessment
)
from app.core.news2_constants import (
    NEWS2Thresholds, NEWS2RiskThresholds, NEWS2Defaults, 
    NEWS2ClinicalMappings, NEWS2FHIRConfig
)
from app.services.fhir_client import FHIRClient
from app.utils.scoring_utils import (
    collect_fhir_parameters, apply_parameter_defaults,
    calculate_data_reliability_score, validate_score_range
)

logger = logging.getLogger(__name__)


async def calculate_total_news2(
    patient_id: str,
    fhir_client: FHIRClient,
    timestamp: Optional[datetime] = None,
    sofa_params: Optional[Any] = None,
    qsofa_params: Optional[Any] = None
) -> News2ScoreResult:
    """
    Calculate complete NEWS2 score with data reuse optimization
    
    Args:
        patient_id: Patient FHIR ID
        fhir_client: FHIR client instance
        timestamp: Target timestamp for calculation
        sofa_params: Existing SOFA parameters (for reuse)
        qsofa_params: Existing qSOFA parameters (for reuse)
    
    Returns:
        Complete NEWS2 score result
    """
    logger.debug(f"Calculating NEWS2 score for patient [REDACTED]")
    
    if timestamp is None:
        timestamp = datetime.now()
    
    # Collect NEWS2 parameters with data reuse optimization
    parameters = await collect_news2_parameters(
        patient_id=patient_id,
        fhir_client=fhir_client,
        timestamp=timestamp,
        sofa_params=sofa_params,
        qsofa_params=qsofa_params
    )
    
    # Calculate individual component scores
    respiratory_score = calculate_respiratory_rate_score(parameters.respiratory_rate)
    oxygen_sat_score = calculate_oxygen_saturation_score(
        parameters.oxygen_saturation, 
        parameters.hypercapnic_respiratory_failure
    )
    supplemental_o2_score = calculate_supplemental_oxygen_score(parameters.supplemental_oxygen)
    temperature_score = calculate_temperature_score(parameters.temperature)
    systolic_bp_score = calculate_systolic_bp_score(parameters.systolic_bp)
    heart_rate_score = calculate_heart_rate_score(parameters.heart_rate)
    consciousness_score = calculate_consciousness_score(parameters.consciousness_level)
    
    # Calculate total score
    component_scores = [
        respiratory_score.score, oxygen_sat_score.score, supplemental_o2_score.score,
        temperature_score.score, systolic_bp_score.score, heart_rate_score.score,
        consciousness_score.score
    ]
    total_score = sum(component_scores)
    
    # Validate total score range
    total_score = validate_score_range(total_score, 0, 20)
    
    # Determine risk level and clinical response
    any_parameter_score_3 = any(score >= 3 for score in component_scores)
    risk_level, clinical_response = determine_news2_risk_level(total_score, any_parameter_score_3)
    
    # Calculate data quality metrics
    reliability_score = calculate_data_reliability_score(
        total_parameters=7,
        estimated_count=parameters.estimated_parameters_count
    )
    
    # Create result
    result = News2ScoreResult(
        patient_id=patient_id,
        timestamp=timestamp,
        respiratory_rate_score=respiratory_score,
        oxygen_saturation_score=oxygen_sat_score,
        supplemental_oxygen_score=supplemental_o2_score,
        temperature_score=temperature_score,
        systolic_bp_score=systolic_bp_score,
        heart_rate_score=heart_rate_score,
        consciousness_score=consciousness_score,
        total_score=total_score,
        risk_level=risk_level,
        clinical_response=clinical_response,
        estimated_parameters_count=parameters.estimated_parameters_count,
        missing_parameters=parameters.missing_parameters,
        data_reliability_score=reliability_score,
        any_parameter_score_3=any_parameter_score_3
    )
    
    logger.debug(f"NEWS2 calculation complete: Score {total_score}/20, Risk {risk_level}")
    return result


async def collect_news2_parameters(
    patient_id: str,
    fhir_client: FHIRClient,
    timestamp: Optional[datetime] = None,
    sofa_params: Optional[Any] = None,
    qsofa_params: Optional[Any] = None
) -> News2Parameters:
    """
    Collect NEWS2 parameters with optimized data reuse from SOFA and qSOFA
    
    Args:
        patient_id: Patient FHIR ID
        fhir_client: FHIR client instance
        timestamp: Target timestamp
        sofa_params: Existing SOFA parameters (for reuse)
        qsofa_params: Existing qSOFA parameters (for reuse)
    
    Returns:
        Complete NEWS2 parameters with reused data where possible
    """
    logger.debug(f"Collecting NEWS2 parameters with data reuse optimization")
    
    if timestamp is None:
        timestamp = datetime.now()
    
    # Step 1: Reuse existing parameters from SOFA and qSOFA
    parameters = News2Parameters.from_existing_parameters(
        patient_id=patient_id,
        sofa_params=sofa_params,
        qsofa_params=qsofa_params,
        timestamp=timestamp
    )
    
    # Step 2: Only fetch supplemental oxygen data from FHIR (the one parameter not in SOFA/qSOFA)
    supplemental_oxygen = await collect_supplemental_oxygen_data(
        fhir_client=fhir_client,
        patient_id=patient_id,
        timestamp=timestamp
    )
    parameters.supplemental_oxygen = supplemental_oxygen
    
    # Step 3: Collect any missing parameters directly from FHIR if needed
    await fill_missing_parameters(
        parameters=parameters,
        fhir_client=fhir_client,
        timestamp=timestamp
    )
    
    # Step 4: Apply defaults for any still-missing parameters
    parameters = apply_news2_defaults(parameters)
    
    logger.debug(f"NEWS2 parameters collected: {len(parameters.missing_parameters)} missing/estimated")
    return parameters


async def collect_supplemental_oxygen_data(
    fhir_client: FHIRClient,
    patient_id: str,
    timestamp: datetime
) -> bool:
    """
    Collect supplemental oxygen data (the one parameter not available in SOFA/qSOFA)
    
    Args:
        fhir_client: FHIR client instance
        patient_id: Patient FHIR ID
        timestamp: Target timestamp
    
    Returns:
        True if patient is on supplemental oxygen, False otherwise
    """
    logger.debug(f"Checking supplemental oxygen status")
    
    # Calculate time window (4 hours for NEWS2)
    start_date = timestamp - timedelta(hours=NEWS2Defaults.LOOKBACK_HOURS)
    end_date = timestamp
    
    try:
        # Check for oxygen-related medications
        medication_bundle = await fhir_client._make_request(
            "GET", "MedicationRequest",
            params={
                "patient": patient_id,
                "status": "active",
                "effective-time": f"ge{start_date.isoformat()}&effective-time=le{end_date.isoformat()}",
                "_count": "10"
            }
        )
        
        # Check for oxygen in medication names
        config = NEWS2FHIRConfig.SUPPLEMENTAL_OXYGEN_PARAMETERS["supplemental_oxygen"]
        oxygen_keywords = config["medication_codes"]
        
        if medication_bundle and "entry" in medication_bundle:
            for entry in medication_bundle["entry"]:
                medication = entry.get("resource", {})
                # Check medication code and display names
                medication_display = medication.get("medicationCodeableConcept", {}).get("text", "").lower()
                
                if any(keyword.lower() in medication_display for keyword in oxygen_keywords):
                    logger.debug("Found supplemental oxygen in medications")
                    return True
        
        # Check for oxygen-related procedures/devices
        procedure_bundle = await fhir_client._make_request(
            "GET", "Procedure",
            params={
                "patient": patient_id,
                "status": "in-progress,completed",
                "date": f"ge{start_date.isoformat()}&date=le{end_date.isoformat()}",
                "_count": "10"
            }
        )
        
        if procedure_bundle and "entry" in procedure_bundle:
            for entry in procedure_bundle["entry"]:
                procedure = entry.get("resource", {})
                procedure_code = procedure.get("code", {}).get("coding", [])
                
                # Check for oxygen-related SNOMED codes
                device_codes = config["device_codes"]
                for coding in procedure_code:
                    if coding.get("code") in device_codes:
                        logger.debug("Found supplemental oxygen in procedures")
                        return True
        
        # Default assumption: room air
        logger.debug("No supplemental oxygen found, assuming room air")
        return False
        
    except Exception as e:
        logger.warning(f"Error checking supplemental oxygen status: {str(e)}")
        # Default to room air if unable to determine
        return False


async def fill_missing_parameters(
    parameters: News2Parameters,
    fhir_client: FHIRClient,
    timestamp: datetime
) -> None:
    """
    Fill any parameters still missing after reuse from SOFA/qSOFA
    
    Args:
        parameters: NEWS2Parameters object to fill
        fhir_client: FHIR client instance
        timestamp: Target timestamp
    """
    logger.debug("Filling missing NEWS2 parameters from FHIR")
    
    # Calculate time window
    start_date = timestamp - timedelta(hours=NEWS2Defaults.LOOKBACK_HOURS)
    end_date = timestamp
    
    # Only collect parameters that are still missing
    missing_vital_signs = {}
    
    # Check each vital sign parameter
    if not parameters.respiratory_rate.is_available:
        missing_vital_signs["respiratory_rate"] = NEWS2FHIRConfig.VITAL_SIGNS_PARAMETERS["respiratory_rate"]
    if not parameters.oxygen_saturation.is_available:
        missing_vital_signs["oxygen_saturation"] = NEWS2FHIRConfig.VITAL_SIGNS_PARAMETERS["oxygen_saturation"]
    if not parameters.temperature.is_available:
        missing_vital_signs["temperature"] = NEWS2FHIRConfig.VITAL_SIGNS_PARAMETERS["temperature"]
    if not parameters.systolic_bp.is_available:
        missing_vital_signs["systolic_bp"] = NEWS2FHIRConfig.VITAL_SIGNS_PARAMETERS["systolic_bp"]
    if not parameters.heart_rate.is_available:
        missing_vital_signs["heart_rate"] = NEWS2FHIRConfig.VITAL_SIGNS_PARAMETERS["heart_rate"]
    
    # Collect missing vital signs
    if missing_vital_signs:
        vital_results = await collect_fhir_parameters(
            fhir_client=fhir_client,
            patient_id=parameters.patient_id,
            start_date=start_date,
            end_date=end_date,
            parameter_configs=missing_vital_signs,
            parameter_class=News2Parameter
        )
        
        # Update parameters with collected data
        for param_name, param_obj in vital_results.items():
            if hasattr(parameters, param_name) and param_obj.is_available:
                setattr(parameters, param_name, param_obj)
    
    # Check GCS separately if still missing
    if not parameters.consciousness_level.is_available:
        gcs_results = await collect_fhir_parameters(
            fhir_client=fhir_client,
            patient_id=parameters.patient_id,
            start_date=start_date,
            end_date=end_date,
            parameter_configs=NEWS2FHIRConfig.NEUROLOGICAL_PARAMETERS,
            parameter_class=News2Parameter
        )
        
        if "gcs" in gcs_results and gcs_results["gcs"].is_available:
            parameters.consciousness_level = gcs_results["gcs"]


def apply_news2_defaults(parameters: News2Parameters) -> News2Parameters:
    """
    Apply default values to missing NEWS2 parameters
    
    Args:
        parameters: NEWS2Parameters object
    
    Returns:
        Updated parameters with defaults applied
    """
    logger.debug("Applying NEWS2 default values for missing parameters")
    
    defaults = NEWS2Defaults.PARAMETER_DEFAULTS
    units = NEWS2Defaults.PARAMETER_UNITS
    
    # Create a dict for apply_parameter_defaults function
    params_dict = {
        "respiratory_rate": parameters.respiratory_rate,
        "oxygen_saturation": parameters.oxygen_saturation,
        "temperature": parameters.temperature,
        "systolic_bp": parameters.systolic_bp,
        "heart_rate": parameters.heart_rate,
        "consciousness_level": parameters.consciousness_level
    }
    
    # Apply defaults using shared utility
    updated_params = apply_parameter_defaults(
        parameters=params_dict,
        defaults=defaults,
        units=units,
        parameter_class=News2Parameter
    )
    
    # Update parameters object
    parameters.respiratory_rate = updated_params["respiratory_rate"]
    parameters.oxygen_saturation = updated_params["oxygen_saturation"]
    parameters.temperature = updated_params["temperature"]
    parameters.systolic_bp = updated_params["systolic_bp"]
    parameters.heart_rate = updated_params["heart_rate"]
    parameters.consciousness_level = updated_params["consciousness_level"]
    
    return parameters


# =============================================================================
# INDIVIDUAL COMPONENT SCORING FUNCTIONS
# =============================================================================

def calculate_respiratory_rate_score(respiratory_rate: News2Parameter) -> News2ComponentScore:
    """Calculate NEWS2 respiratory rate component score"""
    if not respiratory_rate.is_available:
        rr_value = NEWS2Defaults.PARAMETER_DEFAULTS["respiratory_rate"]
    else:
        rr_value = respiratory_rate.value
    
    thresholds = NEWS2Thresholds.RESPIRATORY_RATE
    
    if rr_value <= 8 or rr_value >= 25:
        score = 3
        interpretation = f"Severely abnormal respiratory rate ({rr_value} breaths/min)"
    elif 9 <= rr_value <= 11:
        score = 2
        interpretation = f"Low respiratory rate ({rr_value} breaths/min)"
    elif 21 <= rr_value <= 24:
        score = 1
        interpretation = f"Elevated respiratory rate ({rr_value} breaths/min)"
    else:  # 12-20
        score = 0
        interpretation = f"Normal respiratory rate ({rr_value} breaths/min)"
    
    return News2ComponentScore(
        component="Respiratory Rate",
        score=score,
        threshold_met=score > 0,
        interpretation=interpretation,
        parameters_used=["respiratory_rate"]
    )


def calculate_oxygen_saturation_score(
    oxygen_saturation: News2Parameter, 
    hypercapnic_failure: bool = False
) -> News2ComponentScore:
    """Calculate NEWS2 oxygen saturation component score"""
    if not oxygen_saturation.is_available:
        spo2_value = NEWS2Defaults.PARAMETER_DEFAULTS["oxygen_saturation"]
    else:
        spo2_value = oxygen_saturation.value
    
    # Choose appropriate scale based on patient type
    if hypercapnic_failure:
        thresholds = NEWS2Thresholds.OXYGEN_SATURATION_SCALE2
        scale_type = "Scale 2 (COPD)"
        
        if spo2_value <= 83 or spo2_value >= 93:
            score = 3
            interpretation = f"Critically abnormal SpO2 for COPD patient ({spo2_value}%)"
        elif 84 <= spo2_value <= 85:
            score = 2
            interpretation = f"Low SpO2 for COPD patient ({spo2_value}%)"
        elif 86 <= spo2_value <= 87:
            score = 1
            interpretation = f"Below target SpO2 for COPD patient ({spo2_value}%)"
        else:  # 88-92
            score = 0
            interpretation = f"Target SpO2 for COPD patient ({spo2_value}%)"
    else:
        thresholds = NEWS2Thresholds.OXYGEN_SATURATION_SCALE1
        scale_type = "Scale 1 (Standard)"
        
        if spo2_value <= 91:
            score = 3
            interpretation = f"Critically low oxygen saturation ({spo2_value}%)"
        elif 92 <= spo2_value <= 93:
            score = 2
            interpretation = f"Low oxygen saturation ({spo2_value}%)"
        elif 94 <= spo2_value <= 95:
            score = 1
            interpretation = f"Mildly low oxygen saturation ({spo2_value}%)"
        else:  # ≥96
            score = 0
            interpretation = f"Normal oxygen saturation ({spo2_value}%)"
    
    return News2ComponentScore(
        component=f"Oxygen Saturation ({scale_type})",
        score=score,
        threshold_met=score > 0,
        interpretation=interpretation,
        parameters_used=["oxygen_saturation"]
    )


def calculate_supplemental_oxygen_score(supplemental_oxygen: bool) -> News2ComponentScore:
    """Calculate NEWS2 supplemental oxygen component score"""
    if supplemental_oxygen:
        score = 2
        interpretation = "Patient on supplemental oxygen therapy"
    else:
        score = 0
        interpretation = "Patient breathing room air"
    
    return News2ComponentScore(
        component="Supplemental Oxygen",
        score=score,
        threshold_met=score > 0,
        interpretation=interpretation,
        parameters_used=["supplemental_oxygen"]
    )


def calculate_temperature_score(temperature: News2Parameter) -> News2ComponentScore:
    """Calculate NEWS2 temperature component score"""
    if not temperature.is_available:
        temp_value = NEWS2Defaults.PARAMETER_DEFAULTS["temperature"]
    else:
        temp_value = temperature.value
    
    if temp_value <= 35.0:
        score = 3
        interpretation = f"Severe hypothermia ({temp_value}°C)"
    elif temp_value >= 39.1:
        score = 2
        interpretation = f"High fever ({temp_value}°C)"
    elif (35.1 <= temp_value <= 36.0) or (38.1 <= temp_value <= 39.0):
        score = 1
        interpretation = f"Abnormal temperature ({temp_value}°C)"
    else:  # 36.1-38.0
        score = 0
        interpretation = f"Normal temperature ({temp_value}°C)"
    
    return News2ComponentScore(
        component="Temperature",
        score=score,
        threshold_met=score > 0,
        interpretation=interpretation,
        parameters_used=["temperature"]
    )


def calculate_systolic_bp_score(systolic_bp: News2Parameter) -> News2ComponentScore:
    """Calculate NEWS2 systolic blood pressure component score"""
    if not systolic_bp.is_available:
        sbp_value = NEWS2Defaults.PARAMETER_DEFAULTS["systolic_bp"]
    else:
        sbp_value = systolic_bp.value
    
    if sbp_value <= 90 or sbp_value >= 220:
        score = 3
        interpretation = f"Critically abnormal blood pressure ({sbp_value} mmHg)"
    elif 91 <= sbp_value <= 100:
        score = 2
        interpretation = f"Low blood pressure ({sbp_value} mmHg)"
    elif 101 <= sbp_value <= 110:
        score = 1
        interpretation = f"Mildly low blood pressure ({sbp_value} mmHg)"
    else:  # 111-219
        score = 0
        interpretation = f"Normal blood pressure ({sbp_value} mmHg)"
    
    return News2ComponentScore(
        component="Systolic Blood Pressure",
        score=score,
        threshold_met=score > 0,
        interpretation=interpretation,
        parameters_used=["systolic_bp"]
    )


def calculate_heart_rate_score(heart_rate: News2Parameter) -> News2ComponentScore:
    """Calculate NEWS2 heart rate component score"""
    if not heart_rate.is_available:
        hr_value = NEWS2Defaults.PARAMETER_DEFAULTS["heart_rate"]
    else:
        hr_value = heart_rate.value
    
    if hr_value <= 40 or hr_value >= 131:
        score = 3
        interpretation = f"Critically abnormal heart rate ({hr_value} bpm)"
    elif 111 <= hr_value <= 130:
        score = 2
        interpretation = f"High heart rate ({hr_value} bpm)"
    elif (41 <= hr_value <= 50) or (91 <= hr_value <= 110):
        score = 1
        interpretation = f"Abnormal heart rate ({hr_value} bpm)"
    else:  # 51-90
        score = 0
        interpretation = f"Normal heart rate ({hr_value} bpm)"
    
    return News2ComponentScore(
        component="Heart Rate",
        score=score,
        threshold_met=score > 0,
        interpretation=interpretation,
        parameters_used=["heart_rate"]
    )


def calculate_consciousness_score(consciousness_level: News2Parameter) -> News2ComponentScore:
    """Calculate NEWS2 consciousness level component score"""
    if not consciousness_level.is_available:
        gcs_value = NEWS2Defaults.PARAMETER_DEFAULTS["consciousness_level"]
    else:
        gcs_value = consciousness_level.value
    
    if gcs_value >= 15:
        score = 0
        interpretation = f"Alert (GCS {int(gcs_value)})"
    else:
        score = 3
        # Convert GCS to AVPU-style interpretation
        if gcs_value >= 14:
            status = "New confusion"
        elif gcs_value >= 10:
            status = "Responds to voice"
        elif gcs_value >= 8:
            status = "Responds to pain"
        else:
            status = "Unresponsive"
        
        interpretation = f"Altered consciousness - {status} (GCS {int(gcs_value)})"
    
    return News2ComponentScore(
        component="Level of Consciousness",
        score=score,
        threshold_met=score > 0,
        interpretation=interpretation,
        parameters_used=["consciousness_level"]
    )


def determine_news2_risk_level(total_score: int, any_parameter_score_3: bool) -> Tuple[str, str]:
    """
    Determine NEWS2 risk level and clinical response
    
    Args:
        total_score: Total NEWS2 score
        any_parameter_score_3: Whether any single parameter scored 3 points
    
    Returns:
        Tuple of (risk_level, clinical_response)
    """
    # High risk: Score ≥7
    if total_score >= NEWS2RiskThresholds.HIGH_RISK_MIN:
        return "HIGH", "Emergency assessment"
    
    # Medium risk: Score 5-6 OR any single parameter = 3
    elif (total_score >= NEWS2RiskThresholds.MEDIUM_RISK_MIN or any_parameter_score_3):
        return "MEDIUM", "Urgent review within 1 hour"
    
    # Low risk: Score 0-4 (and no single parameter = 3)
    else:
        return "LOW", "Routine monitoring"