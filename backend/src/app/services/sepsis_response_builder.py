"""
Response Builder Service for Sepsis Scoring Endpoints

Centralizes response building logic to eliminate duplication between
individual and batch sepsis scoring endpoints.
"""

import time
import logging
from datetime import datetime
from typing import Optional, List

from app.models.sofa import (
    SepsisAssessmentResponse, SofaScoreSummary, SepsisRiskLevel, 
    CalculationMetadata, SofaScoreResult, SofaParameters
)

logger = logging.getLogger(__name__)


class SepsisResponseBuilder:
    """Service for building standardized sepsis assessment responses"""
    
    @staticmethod
    def build_assessment_response(
        patient_id: str,
        sofa_result: SofaScoreResult,
        detailed_parameters: Optional[SofaParameters] = None,
        timestamp: Optional[datetime] = None,
        processing_time_ms: Optional[float] = None,
        include_parameters: bool = False
    ) -> SepsisAssessmentResponse:
        """
        Build a standardized sepsis assessment response
        
        Args:
            patient_id: Patient FHIR ID
            sofa_result: Calculated SOFA score result
            detailed_parameters: Optional detailed parameter data
            timestamp: Target timestamp for assessment
            processing_time_ms: Processing time in milliseconds
            include_parameters: Whether to include detailed parameters
        
        Returns:
            Complete sepsis assessment response
        """
        # Create response models
        sofa_summary = SofaScoreSummary.from_sofa_result(sofa_result)
        sepsis_risk = SepsisRiskLevel.from_sofa_score(sofa_result)
        
        # Determine last parameter update time
        last_update = SepsisResponseBuilder._get_last_parameter_update(detailed_parameters)
        
        # Create calculation metadata
        metadata = CalculationMetadata(
            estimated_parameters=sofa_result.estimated_parameters_count,
            missing_parameters=sofa_result.missing_parameters,
            calculation_time_ms=processing_time_ms,
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
        
        logger.debug(f"Built assessment response: SOFA {sofa_result.total_score}/24, Risk: {sepsis_risk.risk_level}")
        return response
    
    @staticmethod
    def build_batch_metadata(
        patient_scores: List[SepsisAssessmentResponse],
        errors: List[dict],
        processing_time_ms: Optional[float] = None
    ) -> dict:
        """
        Build metadata for batch processing results
        
        Args:
            patient_scores: List of successful patient assessments
            errors: List of error dictionaries
            processing_time_ms: Total processing time
        
        Returns:
            Metadata dictionary with summary statistics
        """
        success_count = len(patient_scores)
        error_count = len(errors)
        
        # Find high-risk patients
        high_risk_patients = []
        for score in patient_scores:
            if score.sepsis_assessment.risk_level in ["HIGH", "CRITICAL"]:
                high_risk_patients.append(score.patient_id)
        
        return {
            "success_count": success_count,
            "error_count": error_count,
            "total_processed": success_count + error_count,
            "high_risk_patient_count": len(high_risk_patients),
            "high_risk_patients": high_risk_patients,
            "processing_time_ms": processing_time_ms
        }
    
    @staticmethod
    def _get_last_parameter_update(detailed_parameters: Optional[SofaParameters]) -> Optional[datetime]:
        """
        Determine the last parameter update time from detailed parameters
        
        Args:
            detailed_parameters: Optional SOFA parameters object
        
        Returns:
            Most recent parameter timestamp or None
        """
        if not detailed_parameters:
            return None
        
        timestamps = []
        # Check key parameters for timestamps
        key_parameters = [
            detailed_parameters.platelets,
            detailed_parameters.bilirubin,
            detailed_parameters.gcs,
            detailed_parameters.creatinine,
            detailed_parameters.pao2_fio2_ratio,
            detailed_parameters.map_value
        ]
        
        for param in key_parameters:
            if param and param.timestamp:
                timestamps.append(param.timestamp)
        
        return max(timestamps) if timestamps else None


class ProcessingTimer:
    """Simple context manager for timing operations"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
    
    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0