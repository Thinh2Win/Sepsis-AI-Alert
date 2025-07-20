"""
Sepsis Scoring Service

Business logic layer for sepsis scoring operations, extracted from routers
to improve separation of concerns and maintainability.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.models.sofa import (
    SepsisAssessmentResponse, SepsisScoreRequest, BatchSepsisScoreRequest,
    BatchSepsisScoreResponse
)
from app.services.fhir_client import FHIRClient
from app.services.sepsis_response_builder import SepsisResponseBuilder, ProcessingTimer
from app.utils.sofa_scoring import calculate_total_sofa, collect_sofa_parameters
from app.utils.error_handling import validate_patient_id, validate_scoring_systems

logger = logging.getLogger(__name__)


class SepsisScoringService:
    """Service class for sepsis scoring business logic"""
    
    def __init__(self, fhir_client: FHIRClient):
        self.fhir_client = fhir_client
    
    async def calculate_patient_sepsis_score(
        self,
        patient_id: str,
        timestamp: Optional[datetime] = None,
        include_parameters: bool = False,
        scoring_systems: str = "SOFA"
    ) -> SepsisAssessmentResponse:
        """
        Calculate sepsis assessment score for a single patient
        
        Args:
            patient_id: Patient FHIR ID
            timestamp: Target timestamp for calculation
            include_parameters: Whether to include detailed parameters
            scoring_systems: Comma-separated list of scoring systems
        
        Returns:
            Complete sepsis assessment response
        """
        logger.info(f"Calculating sepsis score for patient [REDACTED]")
        
        with ProcessingTimer() as timer:
            # Validate inputs and create request parameters
            request_params = self._validate_and_create_request(
                patient_id, timestamp, include_parameters, scoring_systems
            )
            
            # Calculate SOFA score
            sofa_result = await calculate_total_sofa(
                patient_id=patient_id,
                fhir_client=self.fhir_client,
                timestamp=timestamp
            )
            
            # Collect detailed parameters if requested
            detailed_parameters = None
            if include_parameters:
                detailed_parameters = await collect_sofa_parameters(
                    patient_id=patient_id,
                    fhir_client=self.fhir_client,
                    timestamp=timestamp
                )
            
            # Build response using centralized service
            response = SepsisResponseBuilder.build_assessment_response(
                patient_id=patient_id,
                sofa_result=sofa_result,
                detailed_parameters=detailed_parameters,
                timestamp=timestamp,
                processing_time_ms=timer.elapsed_ms,
                include_parameters=include_parameters
            )
            
            logger.info(f"Sepsis score calculated: SOFA {sofa_result.total_score}/24, Risk: {response.sepsis_assessment.risk_level}, Time: {timer.elapsed_ms:.1f}ms")
            
            return response
    
    async def calculate_batch_sepsis_scores(
        self,
        request: BatchSepsisScoreRequest
    ) -> BatchSepsisScoreResponse:
        """
        Calculate sepsis assessment scores for multiple patients
        
        Args:
            request: Batch request with patient IDs and parameters
        
        Returns:
            Batch response with individual patient scores and errors
        """
        logger.info(f"Calculating batch sepsis scores for {len(request.patient_ids)} patients")
        
        with ProcessingTimer() as timer:
            patient_scores = []
            errors = []
            
            # Process each patient with individual error handling
            for patient_id in request.patient_ids:
                try:
                    # Calculate score for individual patient
                    patient_response = await self.calculate_patient_sepsis_score(
                        patient_id=patient_id,
                        timestamp=request.timestamp,
                        include_parameters=request.include_parameters,
                        scoring_systems=request.scoring_systems
                    )
                    
                    patient_scores.append(patient_response)
                    
                except Exception as e:
                    error_msg = f"Calculation error: {str(e)}"
                    errors.append({"patient_id": patient_id, "error": error_msg})
                    logger.warning(f"Failed to calculate sepsis score for patient [REDACTED]: {error_msg}")
            
            # Create batch response with metadata
            batch_response = BatchSepsisScoreResponse(
                timestamp=datetime.now(),
                patient_scores=patient_scores,
                errors=errors
            )
            
            # Log batch results with metadata
            metadata = SepsisResponseBuilder.build_batch_metadata(
                patient_scores, errors, timer.elapsed_ms
            )
            
            logger.info(f"Batch sepsis scores completed: {metadata['success_count']} successful, {metadata['error_count']} errors, {metadata['high_risk_patient_count']} high-risk patients, {timer.elapsed_ms:.1f}ms")
            
            return batch_response
    
    def _validate_and_create_request(
        self,
        patient_id: str,
        timestamp: Optional[datetime],
        include_parameters: bool,
        scoring_systems: str
    ) -> SepsisScoreRequest:
        """Validate inputs and create SepsisScoreRequest object"""
        validate_patient_id(patient_id)
        
        request_params = SepsisScoreRequest(
            timestamp=timestamp,
            include_parameters=include_parameters,
            scoring_systems=scoring_systems
        )
        
        validate_scoring_systems(request_params.requested_systems)
        return request_params


class SepsisScoringServiceFactory:
    """Factory for creating SepsisScoringService instances"""
    
    @staticmethod
    def create_service(fhir_client: FHIRClient) -> SepsisScoringService:
        """
        Create a new SepsisScoringService instance
        
        Args:
            fhir_client: FHIR client instance
        
        Returns:
            Configured SepsisScoringService
        """
        return SepsisScoringService(fhir_client)