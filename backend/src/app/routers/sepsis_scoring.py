from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime
import time
import logging

from app.models.sofa import (
    SepsisAssessmentResponse, SofaScoreSummary, SepsisRiskLevel, 
    CalculationMetadata, SepsisScoreRequest, BatchSepsisScoreRequest, 
    BatchSepsisScoreResponse
)
from app.services.fhir_client import FHIRClient
from app.core.dependencies import get_fhir_client
from app.core.exceptions import FHIRException
from app.utils.sofa_scoring import calculate_total_sofa, collect_sofa_parameters

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/patients/{patient_id}/sepsis-score", response_model=SepsisAssessmentResponse)
async def get_sepsis_score(
    patient_id: str,
    timestamp: Optional[datetime] = Query(None, description="Target timestamp for score calculation (ISO format)"),
    include_parameters: bool = Query(False, description="Include detailed parameter data in response"),
    scoring_systems: str = Query("SOFA", description="Scoring systems to calculate (currently only SOFA supported)"),
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """
    Calculate sepsis assessment scores for a patient.
    
    **Current Implementation:**
    - SOFA (Sequential Organ Failure Assessment) score
    - Overall sepsis risk assessment
    - Clinical recommendations
    
    **Future Extensions:**
    - qSOFA (Quick SOFA) score
    - NEWS2 (National Early Warning Score 2)
    - Aggregated sepsis likelihood assessment
    
    **Use Cases:**
    - Real-time patient monitoring
    - Clinical decision support
    - Risk stratification
    - Interval monitoring for inpatient populations
    
    **Query Parameters:**
    - `timestamp`: Calculate score for specific time (defaults to current time)
    - `include_parameters`: Include detailed FHIR parameter data
    - `scoring_systems`: Future support for "SOFA,qSOFA,NEWS2" (currently SOFA only)
    
    **Response includes:**
    - SOFA total score (0-24) with mortality risk assessment
    - Individual organ system scores
    - Overall sepsis risk level (MINIMAL/LOW/MODERATE/HIGH/CRITICAL)
    - Clinical alerts and recommendations
    - Data quality indicators
    """
    logger.info(f"Calculating sepsis score for patient [REDACTED]")
    
    start_time = time.time()
    
    try:
        # Validate patient ID format (basic validation)
        if not patient_id or not patient_id.strip():
            raise HTTPException(
                status_code=400, 
                detail="Patient ID is required and cannot be empty"
            )
        
        # Parse scoring systems request
        request_params = SepsisScoreRequest(
            timestamp=timestamp,
            include_parameters=include_parameters,
            scoring_systems=scoring_systems
        )
        
        # Validate scoring systems (currently only SOFA supported)
        supported_systems = ["SOFA"]
        unsupported = [sys for sys in request_params.requested_systems if sys not in supported_systems]
        if unsupported:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported scoring systems: {', '.join(unsupported)}. Currently supported: {', '.join(supported_systems)}"
            )
        
        # Calculate SOFA score
        sofa_result = await calculate_total_sofa(
            patient_id=patient_id,
            fhir_client=fhir_client,
            timestamp=timestamp
        )
        
        # Collect detailed parameters if requested
        detailed_parameters = None
        if include_parameters:
            detailed_parameters = await collect_sofa_parameters(
                patient_id=patient_id,
                fhir_client=fhir_client,
                timestamp=timestamp
            )
        
        # Create response models
        sofa_summary = SofaScoreSummary.from_sofa_result(sofa_result)
        sepsis_risk = SepsisRiskLevel.from_sofa_score(sofa_result)
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Determine last parameter update time
        last_update = None
        if detailed_parameters:
            timestamps = []
            for param_name in ["platelets", "bilirubin", "gcs", "creatinine"]:
                param = getattr(detailed_parameters, param_name, None)
                if param and param.timestamp:
                    timestamps.append(param.timestamp)
            if timestamps:
                last_update = max(timestamps)
        
        # Create calculation metadata
        metadata = CalculationMetadata(
            estimated_parameters=sofa_result.estimated_parameters_count,
            missing_parameters=sofa_result.missing_parameters,
            calculation_time_ms=processing_time,
            data_sources=["FHIR"],
            last_parameter_update=last_update
        )
        
        # Build response
        response = SepsisAssessmentResponse(
            patient_id=patient_id,
            timestamp=timestamp or datetime.now(),
            sofa_score=sofa_summary,
            sepsis_assessment=sepsis_risk,
            detailed_parameters=detailed_parameters if include_parameters else None,
            full_sofa_result=sofa_result if include_parameters else None,
            calculation_metadata=metadata
        )
        
        logger.info(f"Sepsis score calculated: SOFA {sofa_result.total_score}/24, Risk: {sepsis_risk.risk_level}, Time: {processing_time:.1f}ms")
        
        return response
        
    except FHIRException as e:
        logger.error(f"FHIR error calculating sepsis score for patient [REDACTED]: {e.detail}")
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to retrieve patient data: {e.detail}"
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request parameters: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error calculating sepsis score: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while calculating sepsis score"
        )

@router.post("/patients/batch-sepsis-scores", response_model=BatchSepsisScoreResponse)
async def get_batch_sepsis_scores(
    request: BatchSepsisScoreRequest,
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """
    Calculate sepsis assessment scores for multiple patients in a single request.
    
    **Designed for:**
    - Automated monitoring systems
    - Dashboard applications
    - Interval polling for hospital wards
    - Population health monitoring
    
    **Request Limits:**
    - Maximum 50 patients per request
    - Minimum 1 patient per request
    
    **Response includes:**
    - Individual sepsis assessments for each patient
    - Summary of high-risk patients
    - Error details for any failed calculations
    - Success/error counts
    
    **Error Handling:**
    - Partial results returned when some patients fail
    - Individual error messages for failed calculations
    - Overall request succeeds if any patients processed successfully
    """
    logger.info(f"Calculating batch sepsis scores for {len(request.patient_ids)} patients")
    
    start_time = time.time()
    
    try:
        # Validate request
        if len(request.patient_ids) > 50:
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 patients allowed per batch request"
            )
        
        if len(set(request.patient_ids)) != len(request.patient_ids):
            raise HTTPException(
                status_code=400,
                detail="Duplicate patient IDs are not allowed"
            )
        
        patient_scores = []
        errors = []
        
        # Process each patient
        for patient_id in request.patient_ids:
            try:
                # Calculate SOFA score for individual patient
                sofa_result = await calculate_total_sofa(
                    patient_id=patient_id,
                    fhir_client=fhir_client,
                    timestamp=request.timestamp
                )
                
                # Collect detailed parameters if requested
                detailed_parameters = None
                if request.include_parameters:
                    detailed_parameters = await collect_sofa_parameters(
                        patient_id=patient_id,
                        fhir_client=fhir_client,
                        timestamp=request.timestamp
                    )
                
                # Create response models
                sofa_summary = SofaScoreSummary.from_sofa_result(sofa_result)
                sepsis_risk = SepsisRiskLevel.from_sofa_score(sofa_result)
                
                metadata = CalculationMetadata(
                    estimated_parameters=sofa_result.estimated_parameters_count,
                    missing_parameters=sofa_result.missing_parameters,
                    data_sources=["FHIR"]
                )
                
                # Create individual response
                patient_response = SepsisAssessmentResponse(
                    patient_id=patient_id,
                    timestamp=request.timestamp or datetime.now(),
                    sofa_score=sofa_summary,
                    sepsis_assessment=sepsis_risk,
                    detailed_parameters=detailed_parameters if request.include_parameters else None,
                    full_sofa_result=sofa_result if request.include_parameters else None,
                    calculation_metadata=metadata
                )
                
                patient_scores.append(patient_response)
                
            except FHIRException as e:
                error_msg = f"FHIR error: {e.detail}"
                errors.append({"patient_id": patient_id, "error": error_msg})
                logger.warning(f"Failed to calculate sepsis score for patient [REDACTED]: {error_msg}")
            except Exception as e:
                error_msg = f"Calculation error: {str(e)}"
                errors.append({"patient_id": patient_id, "error": error_msg})
                logger.error(f"Unexpected error for patient [REDACTED]: {error_msg}")
        
        processing_time = (time.time() - start_time) * 1000
        
        # Create batch response
        batch_response = BatchSepsisScoreResponse(
            timestamp=datetime.now(),
            patient_scores=patient_scores,
            errors=errors
        )
        
        logger.info(f"Batch sepsis scores completed: {batch_response.success_count} successful, {batch_response.error_count} errors, {len(batch_response.high_risk_patients)} high-risk patients, {processing_time:.1f}ms")
        
        # Return partial results even if some patients failed
        return batch_response
        
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in batch sepsis score calculation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while calculating batch sepsis scores"
        )

@router.get("/scoring-systems", response_model=Dict[str, Any])
async def get_supported_scoring_systems():
    """
    Get information about supported sepsis scoring systems.
    
    **Returns:**
    - Currently supported scoring systems
    - Future planned scoring systems
    - System descriptions and references
    """
    return {
        "supported": {
            "SOFA": {
                "name": "Sequential Organ Failure Assessment",
                "description": "Assesses organ dysfunction severity in ICU patients",
                "score_range": "0-24",
                "mortality_correlation": "Higher scores indicate higher mortality risk",
                "reference": "Vincent JL, et al. Intensive Care Med. 1996;22(7):707-10"
            }
        },
        "planned": {
            "qSOFA": {
                "name": "Quick Sequential Organ Failure Assessment",
                "description": "Rapid sepsis screening tool for non-ICU settings",
                "score_range": "0-3",
                "status": "Development planned"
            },
            "NEWS2": {
                "name": "National Early Warning Score 2",
                "description": "Physiological track and trigger system",
                "score_range": "0-20+",
                "status": "Development planned"
            }
        },
        "api_info": {
            "current_version": "1.0",
            "endpoint": "/patients/{patient_id}/sepsis-score",
            "batch_endpoint": "/patients/batch-sepsis-scores",
            "max_batch_size": 50
        }
    }

@router.get("/patients/{patient_id}/sepsis-score/trend", response_model=Dict[str, Any])
async def get_sepsis_score_trend(
    patient_id: str,
    hours_back: int = Query(24, ge=1, le=168, description="Hours of history to analyze (1-168)"),
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """
    Get sepsis score trend analysis for a patient over time.
    
    **Future Implementation:**
    - Historical SOFA score progression
    - Trend analysis (improving/worsening/stable)
    - Rate of change calculations
    - Clinical deterioration alerts
    
    **Currently:**
    - Returns placeholder for trend analysis
    - Will be implemented with historical data storage
    """
    logger.info(f"Trend analysis requested for patient [REDACTED] over {hours_back} hours")
    
    # Placeholder implementation - future enhancement
    return {
        "patient_id": patient_id,
        "analysis_period_hours": hours_back,
        "status": "not_implemented",
        "message": "Trend analysis will be available in future version",
        "current_score_endpoint": f"/patients/{patient_id}/sepsis-score",
        "suggested_interval": "Every 4-8 hours for trend monitoring"
    }