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
from app.models.qsofa import QsofaScoreResult, QsofaParameters, QsofaScoreSummary
from app.models.news2 import News2ScoreResult, News2Parameters, News2ScoreSummary

logger = logging.getLogger(__name__)


class SepsisResponseBuilder:
    """Service for building standardized sepsis assessment responses"""
    
    @staticmethod
    def build_assessment_response(
        patient_id: str,
        sofa_result: Optional[SofaScoreResult] = None,
        qsofa_result: Optional[QsofaScoreResult] = None,
        news2_result: Optional[News2ScoreResult] = None,
        detailed_parameters: Optional[SofaParameters] = None,
        detailed_qsofa_parameters: Optional[QsofaParameters] = None,
        detailed_news2_parameters: Optional[News2Parameters] = None,
        timestamp: Optional[datetime] = None,
        processing_time_ms: Optional[float] = None,
        include_parameters: bool = False
    ) -> SepsisAssessmentResponse:
        """
        Build a standardized sepsis assessment response
        
        Args:
            patient_id: Patient FHIR ID
            sofa_result: Optional calculated SOFA score result
            qsofa_result: Optional calculated qSOFA score result
            news2_result: Optional calculated NEWS2 score result
            detailed_parameters: Optional detailed SOFA parameter data
            detailed_qsofa_parameters: Optional detailed qSOFA parameter data
            detailed_news2_parameters: Optional detailed NEWS2 parameter data
            timestamp: Target timestamp for assessment
            processing_time_ms: Processing time in milliseconds
            include_parameters: Whether to include detailed parameters
        
        Returns:
            Complete sepsis assessment response
        """
        # Create response models
        sofa_summary = None
        qsofa_summary = None
        news2_summary = None
        
        if sofa_result:
            sofa_summary = SofaScoreSummary.from_sofa_result(sofa_result)
        
        if qsofa_result:
            qsofa_summary = QsofaScoreSummary.from_result(qsofa_result)
        
        if news2_result:
            news2_summary = News2ScoreSummary.from_result(news2_result)
        
        # Determine overall sepsis risk from available scores
        sepsis_risk = SepsisRiskLevel.from_scores(sofa_result, qsofa_result, news2_result)
        
        # Determine last parameter update time
        last_update = SepsisResponseBuilder._get_last_parameter_update(
            detailed_parameters, detailed_qsofa_parameters, detailed_news2_parameters
        )
        
        # Calculate combined metadata
        estimated_count = 0
        missing_params = []
        
        if sofa_result:
            estimated_count += sofa_result.estimated_parameters_count
            missing_params.extend(sofa_result.missing_parameters)
        
        if qsofa_result:
            estimated_count += qsofa_result.estimated_parameters_count
            missing_params.extend(qsofa_result.missing_parameters)
        
        if news2_result:
            estimated_count += news2_result.estimated_parameters_count
            missing_params.extend(news2_result.missing_parameters)
        
        # Create calculation metadata
        metadata = CalculationMetadata(
            estimated_parameters=estimated_count,
            missing_parameters=list(set(missing_params)),  # Remove duplicates
            calculation_time_ms=processing_time_ms,
            data_sources=["FHIR"],
            last_parameter_update=last_update
        )
        
        # Build response
        response = SepsisAssessmentResponse(
            patient_id=patient_id,
            timestamp=timestamp or datetime.now(),
            sofa_score=sofa_summary,
            qsofa_score=qsofa_summary,
            news2_score=news2_summary,
            sepsis_assessment=sepsis_risk,
            detailed_parameters=detailed_parameters if include_parameters else None,
            detailed_qsofa_parameters=detailed_qsofa_parameters if include_parameters else None,
            detailed_news2_parameters=detailed_news2_parameters if include_parameters else None,
            full_sofa_result=sofa_result if include_parameters else None,
            calculation_metadata=metadata
        )
        
        # Log assessment response
        score_parts = []
        if sofa_result:
            score_parts.append(f"SOFA {sofa_result.total_score}/24")
        if qsofa_result:
            score_parts.append(f"qSOFA {qsofa_result.total_score}/3")
        if news2_result:
            score_parts.append(f"NEWS2 {news2_result.total_score}/20")
        score_info = ", ".join(score_parts) if score_parts else "No scores"
        
        logger.debug(f"Built assessment response: {score_info}, Risk: {sepsis_risk.risk_level}")
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
    def _get_last_parameter_update(
        detailed_parameters: Optional[SofaParameters] = None,
        detailed_qsofa_parameters: Optional[QsofaParameters] = None,
        detailed_news2_parameters: Optional[News2Parameters] = None
    ) -> Optional[datetime]:
        """
        Determine the last parameter update time from detailed parameters
        
        Args:
            detailed_parameters: Optional SOFA parameters object
            detailed_qsofa_parameters: Optional qSOFA parameters object
            detailed_news2_parameters: Optional NEWS2 parameters object
        
        Returns:
            Most recent parameter timestamp or None
        """
        timestamps = []
        
        # Check SOFA parameters for timestamps
        if detailed_parameters:
            sofa_key_parameters = [
                detailed_parameters.platelets,
                detailed_parameters.bilirubin,
                detailed_parameters.gcs,
                detailed_parameters.creatinine,
                detailed_parameters.pao2_fio2_ratio,
                detailed_parameters.map_value
            ]
            
            for param in sofa_key_parameters:
                if param and param.timestamp:
                    timestamps.append(param.timestamp)
        
        # Check qSOFA parameters for timestamps
        if detailed_qsofa_parameters:
            qsofa_key_parameters = [
                detailed_qsofa_parameters.respiratory_rate,
                detailed_qsofa_parameters.systolic_bp,
                detailed_qsofa_parameters.gcs
            ]
            
            for param in qsofa_key_parameters:
                if param and param.timestamp:
                    timestamps.append(param.timestamp)
        
        # Check NEWS2 parameters for timestamps
        if detailed_news2_parameters:
            news2_key_parameters = [
                detailed_news2_parameters.respiratory_rate,
                detailed_news2_parameters.oxygen_saturation,
                detailed_news2_parameters.temperature,
                detailed_news2_parameters.systolic_bp,
                detailed_news2_parameters.heart_rate,
                detailed_news2_parameters.consciousness_level
            ]
            
            for param in news2_key_parameters:
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