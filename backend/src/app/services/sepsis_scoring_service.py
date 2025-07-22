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
    BatchSepsisScoreResponse, DirectSepsisScoreRequest, SofaParameters, 
    SofaParameter, VasopressorDoses
)
from app.services.fhir_client import FHIRClient
from app.services.sepsis_response_builder import SepsisResponseBuilder, ProcessingTimer
from app.utils.sofa_scoring import calculate_total_sofa, collect_sofa_parameters
from app.utils.qsofa_scoring import calculate_total_qsofa, collect_qsofa_parameters
from app.utils.news2_scoring import calculate_total_news2, collect_news2_parameters
from app.utils.error_handling import validate_patient_id, validate_scoring_systems
from app.models.qsofa import QsofaParameters, QsofaParameter
from app.models.news2 import News2Parameters, News2Parameter
from app.utils.calculations import calculate_mean_arterial_pressure

# Ensure models are rebuilt to resolve forward references
try:
    from app.models.qsofa import rebuild_models as rebuild_qsofa_models
    rebuild_qsofa_models()
    from app.models.news2 import rebuild_models as rebuild_news2_models
    rebuild_news2_models()
    from app.models.sofa import rebuild_models as rebuild_sofa_models
    rebuild_sofa_models()
except ImportError:
    pass

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
            
            # Parse requested scoring systems
            requested_systems = [system.strip().upper() for system in scoring_systems.split(",")]
            
            # Initialize results
            sofa_result = None
            qsofa_result = None
            news2_result = None
            detailed_parameters = None
            detailed_qsofa_parameters = None
            detailed_news2_parameters = None
            
            # Calculate SOFA score if requested
            if "SOFA" in requested_systems:
                sofa_result = await calculate_total_sofa(
                    patient_id=patient_id,
                    fhir_client=self.fhir_client,
                    timestamp=timestamp
                )
                
                # Always collect SOFA parameters for potential reuse by NEWS2
                detailed_parameters = await collect_sofa_parameters(
                    patient_id=patient_id,
                    fhir_client=self.fhir_client,
                    timestamp=timestamp
                )
            
            # Calculate qSOFA score if requested  
            if "QSOFA" in requested_systems:
                qsofa_result = await calculate_total_qsofa(
                    patient_id=patient_id,
                    fhir_client=self.fhir_client,
                    timestamp=timestamp
                )
                
                # Always collect qSOFA parameters for potential reuse by NEWS2
                detailed_qsofa_parameters = await collect_qsofa_parameters(
                    patient_id=patient_id,
                    fhir_client=self.fhir_client,
                    timestamp=timestamp
                )
            
            # If NEWS2 is requested but SOFA/qSOFA aren't, collect minimal parameters for reuse
            elif "NEWS2" in requested_systems and "SOFA" not in requested_systems:
                # Collect SOFA parameters silently for NEWS2 optimization (don't calculate SOFA score)
                logger.debug("Collecting SOFA parameters for NEWS2 data reuse optimization")
                detailed_parameters = await collect_sofa_parameters(
                    patient_id=patient_id,
                    fhir_client=self.fhir_client,
                    timestamp=timestamp
                )
            
            # Calculate NEWS2 score if requested (with data reuse optimization)
            if "NEWS2" in requested_systems:
                news2_result = await calculate_total_news2(
                    patient_id=patient_id,
                    fhir_client=self.fhir_client,
                    timestamp=timestamp,
                    sofa_params=detailed_parameters,  # Reuse SOFA parameters if available
                    qsofa_params=detailed_qsofa_parameters  # Reuse qSOFA parameters if available
                )
                
                # Collect detailed NEWS2 parameters if requested
                if include_parameters:
                    detailed_news2_parameters = await collect_news2_parameters(
                        patient_id=patient_id,
                        fhir_client=self.fhir_client,
                        timestamp=timestamp,
                        sofa_params=detailed_parameters,  # Reuse SOFA parameters
                        qsofa_params=detailed_qsofa_parameters  # Reuse qSOFA parameters
                    )
            
            # Default to SOFA if no valid systems specified
            if not sofa_result and not qsofa_result and not news2_result:
                sofa_result = await calculate_total_sofa(
                    patient_id=patient_id,
                    fhir_client=self.fhir_client,
                    timestamp=timestamp
                )
            
            # Build response using centralized service
            # Only include detailed parameters in response if requested
            response = SepsisResponseBuilder.build_assessment_response(
                patient_id=patient_id,
                sofa_result=sofa_result,
                qsofa_result=qsofa_result,
                news2_result=news2_result,
                detailed_parameters=detailed_parameters if include_parameters else None,
                detailed_qsofa_parameters=detailed_qsofa_parameters if include_parameters else None,
                detailed_news2_parameters=detailed_news2_parameters,
                timestamp=timestamp,
                processing_time_ms=timer.elapsed_ms,
                include_parameters=include_parameters
            )
            
            # Log calculation results
            log_parts = []
            if sofa_result:
                log_parts.append(f"SOFA {sofa_result.total_score}/24")
            if qsofa_result:
                log_parts.append(f"qSOFA {qsofa_result.total_score}/3")
            if news2_result:
                log_parts.append(f"NEWS2 {news2_result.total_score}/20")
            score_info = ", ".join(log_parts) if log_parts else "No scores calculated"
            
            logger.info(f"Sepsis score calculated: {score_info}, Risk: {response.sepsis_assessment.risk_level}, Time: {timer.elapsed_ms:.1f}ms")
            
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
        
        validate_scoring_systems(request_params.requested_systems, ["SOFA", "QSOFA", "NEWS2"])
        return request_params
    
    async def calculate_direct_sepsis_score(
        self,
        request: DirectSepsisScoreRequest
    ) -> SepsisAssessmentResponse:
        """
        Calculate sepsis assessment scores using directly provided parameters
        
        Args:
            request: DirectSepsisScoreRequest with all clinical parameters
        
        Returns:
            Complete sepsis assessment response
        """
        logger.info(f"Calculating direct sepsis score for patient [REDACTED]")
        
        with ProcessingTimer() as timer:
            # Validate inputs
            validate_patient_id(request.patient_id)
            validate_scoring_systems(request.requested_systems, ["SOFA", "QSOFA", "NEWS2"])
            
            timestamp = request.timestamp or datetime.now()
            
            # Convert request to parameter objects
            sofa_params = self._create_sofa_parameters_from_request(request, timestamp)
            qsofa_params = self._create_qsofa_parameters_from_request(request, timestamp) 
            news2_params = self._create_news2_parameters_from_request(request, timestamp)
            
            # Calculate scores for requested systems
            sofa_result = None
            qsofa_result = None
            news2_result = None
            
            if "SOFA" in request.requested_systems:
                sofa_result = self._calculate_sofa_from_parameters(sofa_params)
            
            if "QSOFA" in request.requested_systems:
                qsofa_result = self._calculate_qsofa_from_parameters(qsofa_params)
            
            if "NEWS2" in request.requested_systems:
                news2_result = self._calculate_news2_from_parameters(news2_params)
            
            # Build response using centralized service
            response = SepsisResponseBuilder.build_assessment_response(
                patient_id=request.patient_id,
                sofa_result=sofa_result,
                qsofa_result=qsofa_result,
                news2_result=news2_result,
                detailed_parameters=sofa_params if request.include_parameters else None,
                detailed_qsofa_parameters=qsofa_params if request.include_parameters else None,
                detailed_news2_parameters=news2_params if request.include_parameters else None,
                timestamp=timestamp,
                processing_time_ms=timer.elapsed_ms,
                include_parameters=request.include_parameters
            )
            
            # Log calculation results
            log_parts = []
            if sofa_result:
                log_parts.append(f"SOFA {sofa_result.total_score}/24")
            if qsofa_result:
                log_parts.append(f"qSOFA {qsofa_result.total_score}/3")
            if news2_result:
                log_parts.append(f"NEWS2 {news2_result.total_score}/20")
            score_info = ", ".join(log_parts) if log_parts else "No scores calculated"
            
            logger.info(f"Direct sepsis score calculated: {score_info}, Risk: {response.sepsis_assessment.risk_level}, Time: {timer.elapsed_ms:.1f}ms")
            
            return response
    
    def _create_sofa_parameters_from_request(self, request: DirectSepsisScoreRequest, timestamp: datetime) -> SofaParameters:
        """Create SofaParameters object from request data"""
        
        # Calculate MAP if not provided but systolic/diastolic are available
        map_value = request.mean_arterial_pressure
        if map_value is None and request.systolic_bp and request.diastolic_bp:
            map_value = calculate_mean_arterial_pressure(request.systolic_bp, request.diastolic_bp)
        
        # Create vasopressor doses object
        vasopressor_doses = VasopressorDoses(
            dopamine=request.dopamine,
            dobutamine=request.dobutamine,
            epinephrine=request.epinephrine,
            norepinephrine=request.norepinephrine,
            phenylephrine=request.phenylephrine
        )
        
        # Create SOFA parameters
        sofa_params = SofaParameters(
            patient_id=request.patient_id,
            timestamp=timestamp,
            pao2=SofaParameter(value=request.pao2, unit="mmHg", timestamp=timestamp, source="direct"),
            fio2=SofaParameter(value=request.fio2, unit="fraction", timestamp=timestamp, source="direct"),
            mechanical_ventilation=request.mechanical_ventilation or False,
            platelets=SofaParameter(value=request.platelets, unit="x10^3/uL", timestamp=timestamp, source="direct"),
            bilirubin=SofaParameter(value=request.bilirubin, unit="mg/dL", timestamp=timestamp, source="direct"),
            map_value=SofaParameter(value=map_value, unit="mmHg", timestamp=timestamp, source="direct"),
            systolic_bp=SofaParameter(value=request.systolic_bp, unit="mmHg", timestamp=timestamp, source="direct"),
            diastolic_bp=SofaParameter(value=request.diastolic_bp, unit="mmHg", timestamp=timestamp, source="direct"),
            vasopressor_doses=vasopressor_doses,
            gcs=SofaParameter(value=request.glasgow_coma_scale, unit="points", timestamp=timestamp, source="direct"),
            creatinine=SofaParameter(value=request.creatinine, unit="mg/dL", timestamp=timestamp, source="direct"),
            urine_output_24h=SofaParameter(value=request.urine_output_24h, unit="mL", timestamp=timestamp, source="direct"),
            # Additional vital signs for NEWS2 reuse optimization
            heart_rate=SofaParameter(value=request.heart_rate, unit="bpm", timestamp=timestamp, source="direct"),
            temperature=SofaParameter(value=request.temperature, unit="°C", timestamp=timestamp, source="direct"),
            respiratory_rate=SofaParameter(value=request.respiratory_rate, unit="breaths/min", timestamp=timestamp, source="direct"),
            oxygen_saturation=SofaParameter(value=request.oxygen_saturation, unit="%", timestamp=timestamp, source="direct")
        )
        
        # Calculate PaO2/FiO2 ratio if both values available
        if request.pao2 and request.fio2:
            pao2_fio2_ratio = request.pao2 / request.fio2
            sofa_params.pao2_fio2_ratio = SofaParameter(value=pao2_fio2_ratio, unit="mmHg", timestamp=timestamp, source="calculated")
        
        return sofa_params
    
    def _create_qsofa_parameters_from_request(self, request: DirectSepsisScoreRequest, timestamp: datetime) -> QsofaParameters:
        """Create QsofaParameters object from request data"""
        
        qsofa_params = QsofaParameters(
            patient_id=request.patient_id,
            timestamp=timestamp,
            respiratory_rate=QsofaParameter(value=request.respiratory_rate, unit="breaths/min", timestamp=timestamp, source="direct"),
            systolic_bp=QsofaParameter(value=request.systolic_bp, unit="mmHg", timestamp=timestamp, source="direct"),
            gcs=QsofaParameter(value=request.glasgow_coma_scale, unit="points", timestamp=timestamp, source="direct"),
            altered_mental_status=request.glasgow_coma_scale < 15 if request.glasgow_coma_scale else False
        )
        
        return qsofa_params
    
    def _create_news2_parameters_from_request(self, request: DirectSepsisScoreRequest, timestamp: datetime) -> News2Parameters:
        """Create News2Parameters object from request data"""
        
        # Map AVPU to GCS equivalent if needed
        consciousness_value = request.glasgow_coma_scale
        if request.consciousness_level_avpu:
            avpu_to_gcs = {"A": 15, "V": 13, "P": 8, "U": 3}
            consciousness_value = avpu_to_gcs.get(request.consciousness_level_avpu.upper(), consciousness_value)
        
        news2_params = News2Parameters(
            patient_id=request.patient_id,
            timestamp=timestamp,
            respiratory_rate=News2Parameter(value=request.respiratory_rate, unit="breaths/min", timestamp=timestamp, source="direct"),
            oxygen_saturation=News2Parameter(value=request.oxygen_saturation, unit="%", timestamp=timestamp, source="direct"),
            supplemental_oxygen=request.supplemental_oxygen or False,
            temperature=News2Parameter(value=request.temperature, unit="°C", timestamp=timestamp, source="direct"),
            systolic_bp=News2Parameter(value=request.systolic_bp, unit="mmHg", timestamp=timestamp, source="direct"),
            heart_rate=News2Parameter(value=request.heart_rate, unit="bpm", timestamp=timestamp, source="direct"),
            consciousness_level=News2Parameter(value=consciousness_value, unit="points", timestamp=timestamp, source="direct"),
            hypercapnic_respiratory_failure=request.hypercapnic_respiratory_failure or False
        )
        
        return news2_params
    
    def _calculate_sofa_from_parameters(self, sofa_params: SofaParameters):
        """Calculate SOFA score from parameter object"""
        from app.utils.sofa_scoring import (
            calculate_respiratory_score, calculate_coagulation_score,
            calculate_liver_score, calculate_cardiovascular_score,
            calculate_cns_score, calculate_renal_score
        )
        from app.models.sofa import SofaScoreResult
        from app.utils.scoring_utils import calculate_data_reliability_score
        
        # Calculate individual scores
        respiratory_score = calculate_respiratory_score(
            sofa_params.pao2.value, sofa_params.fio2.value, sofa_params.mechanical_ventilation
        )
        coagulation_score = calculate_coagulation_score(sofa_params.platelets.value)
        liver_score = calculate_liver_score(sofa_params.bilirubin.value)
        cardiovascular_score = calculate_cardiovascular_score(
            sofa_params.map_value.value, sofa_params.vasopressor_doses
        )
        cns_score = calculate_cns_score(sofa_params.gcs.value)
        renal_score = calculate_renal_score(
            sofa_params.creatinine.value, sofa_params.urine_output_24h.value
        )
        
        # Calculate total score
        total_score = (respiratory_score.score + coagulation_score.score + 
                      liver_score.score + cardiovascular_score.score +
                      cns_score.score + renal_score.score)
        
        # Calculate data reliability
        reliability = calculate_data_reliability_score(
            total_parameters=11,  # Total SOFA parameters
            estimated_count=sofa_params.estimated_parameters_count
        )
        
        return SofaScoreResult(
            patient_id=sofa_params.patient_id,
            timestamp=sofa_params.timestamp,
            respiratory_score=respiratory_score,
            coagulation_score=coagulation_score,
            liver_score=liver_score,
            cardiovascular_score=cardiovascular_score,
            cns_score=cns_score,
            renal_score=renal_score,
            total_score=total_score,
            estimated_parameters_count=sofa_params.estimated_parameters_count,
            missing_parameters=sofa_params.missing_parameters,
            data_reliability_score=reliability
        )
    
    def _calculate_qsofa_from_parameters(self, qsofa_params: QsofaParameters):
        """Calculate qSOFA score from parameter object"""
        from app.utils.qsofa_scoring import (
            calculate_respiratory_score, calculate_cardiovascular_score,
            calculate_cns_score
        )
        from app.models.qsofa import QsofaScoreResult
        from app.utils.scoring_utils import calculate_data_reliability_score
        
        # Calculate individual component scores
        respiratory_score = calculate_respiratory_score(qsofa_params.respiratory_rate.value)
        cardiovascular_score = calculate_cardiovascular_score(qsofa_params.systolic_bp.value)
        cns_score = calculate_cns_score(qsofa_params.altered_mental_status, qsofa_params.gcs.value)
        
        # Calculate total score
        total_score = respiratory_score.score + cardiovascular_score.score + cns_score.score
        
        # Calculate data reliability
        reliability = calculate_data_reliability_score(
            total_parameters=3,  # Total qSOFA parameters
            estimated_count=qsofa_params.estimated_parameters_count
        )
        
        return QsofaScoreResult(
            patient_id=qsofa_params.patient_id,
            timestamp=qsofa_params.timestamp,
            respiratory_score=respiratory_score,
            cardiovascular_score=cardiovascular_score,
            cns_score=cns_score,
            total_score=total_score,
            high_risk=total_score >= 2,
            estimated_parameters_count=qsofa_params.estimated_parameters_count,
            missing_parameters=qsofa_params.missing_parameters,
            data_reliability_score=reliability
        )
    
    def _calculate_news2_from_parameters(self, news2_params: News2Parameters):
        """Calculate NEWS2 score from parameter object"""
        from app.utils.news2_scoring import (
            calculate_respiratory_rate_score, calculate_oxygen_saturation_score,
            calculate_supplemental_oxygen_score, calculate_temperature_score, 
            calculate_systolic_bp_score, calculate_heart_rate_score, 
            calculate_consciousness_score
        )
        from app.models.news2 import News2ScoreResult, News2ComponentScore
        from app.utils.scoring_utils import calculate_data_reliability_score
        
        # Calculate individual component scores
        respiratory_score = calculate_respiratory_rate_score(news2_params.respiratory_rate)
        oxygen_score = calculate_oxygen_saturation_score(
            news2_params.oxygen_saturation, news2_params.hypercapnic_respiratory_failure
        )
        supplemental_oxygen_score = calculate_supplemental_oxygen_score(news2_params.supplemental_oxygen)
        temperature_score = calculate_temperature_score(news2_params.temperature)
        systolic_bp_score = calculate_systolic_bp_score(news2_params.systolic_bp)
        heart_rate_score = calculate_heart_rate_score(news2_params.heart_rate)
        consciousness_score = calculate_consciousness_score(news2_params.consciousness_level)
        
        # Calculate total score
        total_score = (respiratory_score.score + oxygen_score.score + 
                      supplemental_oxygen_score.score + temperature_score.score +
                      systolic_bp_score.score + heart_rate_score.score + 
                      consciousness_score.score)
        
        # Determine risk level
        any_parameter_score_3 = any(score.score >= 3 for score in [
            respiratory_score, oxygen_score, supplemental_oxygen_score,
            temperature_score, systolic_bp_score, heart_rate_score, consciousness_score
        ])
        
        if total_score >= 7:
            risk_level = "HIGH"
            clinical_response = "Emergency assessment"
        elif total_score >= 5 or any_parameter_score_3:
            risk_level = "MEDIUM" 
            clinical_response = "Urgent review within 1 hour"
        else:
            risk_level = "LOW"
            clinical_response = "Routine monitoring"
        
        # Calculate data reliability
        reliability = calculate_data_reliability_score(
            total_parameters=7,  # Total NEWS2 parameters
            estimated_count=news2_params.estimated_parameters_count
        )
        
        return News2ScoreResult(
            patient_id=news2_params.patient_id,
            timestamp=news2_params.timestamp,
            respiratory_rate_score=respiratory_score,
            oxygen_saturation_score=oxygen_score,
            supplemental_oxygen_score=supplemental_oxygen_score,
            temperature_score=temperature_score,
            systolic_bp_score=systolic_bp_score,
            heart_rate_score=heart_rate_score,
            consciousness_score=consciousness_score,
            total_score=total_score,
            risk_level=risk_level,
            clinical_response=clinical_response,
            estimated_parameters_count=news2_params.estimated_parameters_count,
            missing_parameters=news2_params.missing_parameters,
            data_reliability_score=reliability,
            any_parameter_score_3=any_parameter_score_3
        )


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