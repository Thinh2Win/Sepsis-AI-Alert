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
    scoring_systems: str = Query("SOFA,qSOFA,NEWS2", description="Scoring systems to calculate (SOFA, qSOFA, NEWS2, or any combination). All three calculated by default."),
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """
    Calculate sepsis assessment scores for a patient.
    
    **Current Implementation:**
    - SOFA (Sequential Organ Failure Assessment) score
    - qSOFA (Quick SOFA) score
    - NEWS2 (National Early Warning Score 2)
    - Overall sepsis risk assessment with combined scores
    - Clinical recommendations with data reuse optimization
    
    **Future Extensions:**
    - SIRS (Systemic Inflammatory Response Syndrome) criteria
    - Aggregated sepsis likelihood assessment
    - Trend analysis and historical scoring
    
    **Use Cases:**
    - Real-time patient monitoring
    - Clinical decision support
    - Risk stratification
    - Interval monitoring for inpatient populations
    
    **Query Parameters:**
    - `timestamp`: Calculate score for specific time (defaults to current time)
    - `include_parameters`: Include detailed FHIR parameter data
    - `scoring_systems`: Specify which systems to calculate (default: "SOFA,qSOFA,NEWS2" for all three)
    
    **Response includes:**
    - SOFA total score (0-24) with mortality risk assessment (calculated by default)
    - qSOFA total score (0-3) with high-risk threshold assessment (calculated by default) 
    - NEWS2 total score (0-20) with clinical deterioration risk assessment (calculated by default)
    - Individual component scores for all calculated systems
    - Overall sepsis risk level (MINIMAL/LOW/MODERATE/HIGH/CRITICAL) based on combined assessment
    - Clinical alerts and recommendations based on all calculated scores
    - Data quality indicators and missing parameter information
    - Data reuse optimization to minimize FHIR API calls
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


