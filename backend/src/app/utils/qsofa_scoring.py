import logging
from typing import Optional
from datetime import datetime, timedelta

from app.models.qsofa import (
    QsofaParameters, QsofaParameter, QsofaComponentScore, 
    QsofaScoreResult
)
from app.services.fhir_client import FHIRClient
from app.core.qsofa_constants import (
    QsofaDefaults, QsofaThresholds, QsofaParameterConfigs
)
from app.utils.scoring_utils import (
    collect_fhir_parameters, apply_parameter_defaults,
    calculate_data_reliability_score, validate_score_range,
    create_default_component_score
)

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
        # Collect all parameters using shared utility
        parameter_configs = {
            "respiratory": QsofaParameterConfigs.RESPIRATORY,
            "cardiovascular": QsofaParameterConfigs.CARDIOVASCULAR,
            "cns": QsofaParameterConfigs.CNS
        }
        
        collected_params = await collect_fhir_parameters(
            fhir_client, patient_id, start_date, end_date, 
            parameter_configs, QsofaParameter
        )
        
        # Map collected parameters to qSOFA object
        qsofa_params.respiratory_rate = collected_params.get("respiratory_rate", QsofaParameter())
        qsofa_params.systolic_bp = collected_params.get("systolic_bp", QsofaParameter())
        qsofa_params.gcs = collected_params.get("gcs", QsofaParameter())
        
        # Assess altered mental status (simplified)
        qsofa_params.altered_mental_status = _assess_mental_status_simple(qsofa_params.gcs)
        
        # Apply defaults using shared utility
        defaults = {
            "respiratory_rate": QsofaDefaults.RESPIRATORY_RATE,
            "systolic_bp": QsofaDefaults.SYSTOLIC_BP,
            "gcs": QsofaDefaults.GCS
        }
        units = {"respiratory_rate": "breaths/min", "systolic_bp": "mmHg", "gcs": "score"}
        
        param_dict = {
            "respiratory_rate": qsofa_params.respiratory_rate,
            "systolic_bp": qsofa_params.systolic_bp,
            "gcs": qsofa_params.gcs
        }
        
        apply_parameter_defaults(param_dict, defaults, units, QsofaParameter)
        
        logger.info(f"qSOFA parameters collected: {len(qsofa_params.missing_parameters)} parameters estimated/missing")
        return qsofa_params
        
    except Exception as e:
        logger.error(f"Error collecting qSOFA parameters: {str(e)}")
        # Return parameters with defaults applied
        return _create_default_qsofa_parameters(patient_id, timestamp)

def _assess_mental_status_simple(gcs_param: QsofaParameter) -> bool:
    """
    Simple mental status assessment based on GCS only (KISS principle)
    
    Args:
        gcs_param: Glasgow Coma Score parameter
    
    Returns:
        True if altered mental status detected (GCS < 15)
    """
    if gcs_param.value is not None and gcs_param.value < QsofaThresholds.GCS_THRESHOLD:
        logger.debug(f"Altered mental status detected: GCS {gcs_param.value}")
        return True
    return False

# Removed: Old complex parameter handling replaced by shared utilities

def calculate_respiratory_score(respiratory_rate: Optional[float]) -> QsofaComponentScore:
    """Calculate qSOFA respiratory score based on respiratory rate"""
    
    if respiratory_rate is None:
        respiratory_rate = QsofaDefaults.RESPIRATORY_RATE
    
    threshold_met = respiratory_rate >= QsofaThresholds.RESPIRATORY_RATE_THRESHOLD
    score = 1 if threshold_met else 0
    
    interpretation = f"Respiratory rate: {respiratory_rate:.0f} breaths/min"
    if threshold_met:
        interpretation += f" (≥{QsofaThresholds.RESPIRATORY_RATE_THRESHOLD})"
    
    return create_default_component_score(
        "Respiratory", score, threshold_met, interpretation, 
        ["respiratory_rate"], QsofaComponentScore
    )

def calculate_cardiovascular_score(systolic_bp: Optional[float]) -> QsofaComponentScore:
    """Calculate qSOFA cardiovascular score based on systolic blood pressure"""
    
    if systolic_bp is None:
        systolic_bp = QsofaDefaults.SYSTOLIC_BP
    
    threshold_met = systolic_bp <= QsofaThresholds.SYSTOLIC_BP_THRESHOLD
    score = 1 if threshold_met else 0
    
    interpretation = f"Systolic BP: {systolic_bp:.0f} mmHg"
    if threshold_met:
        interpretation += f" (≤{QsofaThresholds.SYSTOLIC_BP_THRESHOLD})"
    
    return create_default_component_score(
        "Cardiovascular", score, threshold_met, interpretation,
        ["systolic_bp"], QsofaComponentScore
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
    
    return create_default_component_score(
        "Central Nervous System", score, altered_mental_status, interpretation,
        ["gcs", "mental_status_assessment"], QsofaComponentScore
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
        
        # Calculate total score using shared utility
        total_score = validate_score_range(
            respiratory_score.score + cardiovascular_score.score + cns_score.score, 0, 3
        )
        
        # Determine high risk status
        high_risk = total_score >= QsofaThresholds.HIGH_RISK_THRESHOLD
        
        # Calculate data reliability score using shared utility
        estimated_count = parameters.estimated_parameters_count
        reliability_score = calculate_data_reliability_score(3, estimated_count)
        
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

# All helper functions moved to shared utilities (scoring_utils.py) for DRY compliance