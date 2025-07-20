from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.models.sofa import (
    SepsisAssessmentResponse, BatchSepsisScoreRequest, 
    BatchSepsisScoreResponse
)
from app.services.fhir_client import FHIRClient
from app.services.sepsis_scoring_service import SepsisScoringServiceFactory
from app.core.dependencies import get_fhir_client
from app.utils.error_handling import (
    handle_sepsis_errors, validate_batch_request
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/patients/{patient_id}/sepsis-score", response_model=SepsisAssessmentResponse)
@handle_sepsis_errors(operation_name="sepsis score calculation")
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
    # Delegate to service layer
    service = SepsisScoringServiceFactory.create_service(fhir_client)
    return await service.calculate_patient_sepsis_score(
        patient_id=patient_id,
        timestamp=timestamp,
        include_parameters=include_parameters,
        scoring_systems=scoring_systems
    )

@router.post("/patients/batch-sepsis-scores", response_model=BatchSepsisScoreResponse)
@handle_sepsis_errors(operation_name="batch sepsis score calculation", include_patient_in_log=False)
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
    # Validate batch request
    validate_batch_request(request.patient_ids, max_patients=50, allow_duplicates=False)
    
    # Delegate to service layer
    service = SepsisScoringServiceFactory.create_service(fhir_client)
    return await service.calculate_batch_sepsis_scores(request)


