from pydantic import BaseModel, Field, computed_field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime

class News2Parameter(BaseModel):
    """Individual NEWS2 parameter with metadata"""
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    is_estimated: bool = False
    last_known_value: Optional[float] = None
    source: Optional[str] = None  # "measured", "estimated", "default", "calculated", "reused"
    
    @computed_field
    @property
    def is_available(self) -> bool:
        return self.value is not None

class News2Parameters(BaseModel):
    """Complete set of NEWS2 parameters"""
    patient_id: str
    timestamp: Optional[datetime] = None
    
    # NEWS2 components (7 parameters)
    respiratory_rate: News2Parameter = Field(default_factory=News2Parameter)
    oxygen_saturation: News2Parameter = Field(default_factory=News2Parameter)
    supplemental_oxygen: bool = False
    temperature: News2Parameter = Field(default_factory=News2Parameter)
    systolic_bp: News2Parameter = Field(default_factory=News2Parameter)
    heart_rate: News2Parameter = Field(default_factory=News2Parameter)
    consciousness_level: News2Parameter = Field(default_factory=News2Parameter)  # AVPU or GCS
    
    # For COPD patients (Scale 2)
    hypercapnic_respiratory_failure: bool = False
    
    @computed_field
    @property
    def estimated_parameters_count(self) -> int:
        """Count of parameters that were estimated or defaulted"""
        parameters = [
            self.respiratory_rate, self.oxygen_saturation, self.temperature,
            self.systolic_bp, self.heart_rate, self.consciousness_level
        ]
        return sum(1 for param in parameters if param.is_estimated)
    
    @computed_field
    @property
    def missing_parameters(self) -> List[str]:
        """List of parameter names that are missing or estimated"""
        missing = []
        parameter_mapping = {
            "respiratory_rate": self.respiratory_rate,
            "oxygen_saturation": self.oxygen_saturation,
            "temperature": self.temperature,
            "systolic_bp": self.systolic_bp,
            "heart_rate": self.heart_rate,
            "consciousness_level": self.consciousness_level
        }
        
        for name, param in parameter_mapping.items():
            if not param.is_available or param.is_estimated:
                missing.append(name)
        
        return missing
    
    @classmethod
    def from_existing_parameters(
        cls,
        patient_id: str,
        sofa_params: Optional[Any] = None,
        qsofa_params: Optional[Any] = None,
        timestamp: Optional[datetime] = None
    ) -> "News2Parameters":
        """
        Create NEWS2 parameters by reusing data from SOFA and qSOFA parameters
        
        Args:
            patient_id: Patient FHIR ID
            sofa_params: SOFA parameters object (if available)
            qsofa_params: qSOFA parameters object (if available)
            timestamp: Target timestamp
            
        Returns:
            NEWS2Parameters with reused data
        """
        params = cls(patient_id=patient_id, timestamp=timestamp)
        
        # Reuse respiratory rate from qSOFA (preferred) or SOFA
        if qsofa_params and qsofa_params.respiratory_rate.is_available:
            params.respiratory_rate = News2Parameter(
                value=qsofa_params.respiratory_rate.value,
                unit=qsofa_params.respiratory_rate.unit,
                timestamp=qsofa_params.respiratory_rate.timestamp,
                is_estimated=qsofa_params.respiratory_rate.is_estimated,
                source="reused_qsofa"
            )
        
        # Reuse systolic BP from qSOFA (preferred) or SOFA
        if qsofa_params and qsofa_params.systolic_bp.is_available:
            params.systolic_bp = News2Parameter(
                value=qsofa_params.systolic_bp.value,
                unit=qsofa_params.systolic_bp.unit,
                timestamp=qsofa_params.systolic_bp.timestamp,
                is_estimated=qsofa_params.systolic_bp.is_estimated,
                source="reused_qsofa"
            )
        elif sofa_params and sofa_params.systolic_bp.is_available:
            params.systolic_bp = News2Parameter(
                value=sofa_params.systolic_bp.value,
                unit=sofa_params.systolic_bp.unit,
                timestamp=sofa_params.systolic_bp.timestamp,
                is_estimated=sofa_params.systolic_bp.is_estimated,
                source="reused_sofa"
            )
        
        # Reuse GCS from qSOFA (preferred) or SOFA for consciousness level
        if qsofa_params and qsofa_params.gcs.is_available:
            params.consciousness_level = News2Parameter(
                value=qsofa_params.gcs.value,
                unit="points",
                timestamp=qsofa_params.gcs.timestamp,
                is_estimated=qsofa_params.gcs.is_estimated,
                source="reused_qsofa"
            )
        elif sofa_params and sofa_params.gcs.is_available:
            params.consciousness_level = News2Parameter(
                value=sofa_params.gcs.value,
                unit="points",
                timestamp=sofa_params.gcs.timestamp,
                is_estimated=sofa_params.gcs.is_estimated,
                source="reused_sofa"
            )
        
        # Reuse parameters from SOFA where available
        if sofa_params:
            # Heart rate (not in qSOFA)
            if hasattr(sofa_params, 'heart_rate') and sofa_params.heart_rate and sofa_params.heart_rate.is_available:
                params.heart_rate = News2Parameter(
                    value=sofa_params.heart_rate.value,
                    unit=sofa_params.heart_rate.unit,
                    timestamp=sofa_params.heart_rate.timestamp,
                    is_estimated=sofa_params.heart_rate.is_estimated,
                    source="reused_sofa"
                )
            
            # Temperature (not in qSOFA)  
            if hasattr(sofa_params, 'temperature') and sofa_params.temperature and sofa_params.temperature.is_available:
                params.temperature = News2Parameter(
                    value=sofa_params.temperature.value,
                    unit=sofa_params.temperature.unit,
                    timestamp=sofa_params.temperature.timestamp,
                    is_estimated=sofa_params.temperature.is_estimated,
                    source="reused_sofa"
                )
            
            # Oxygen saturation from PaO2/FiO2 calculation or direct SpO2
            if hasattr(sofa_params, 'oxygen_saturation') and sofa_params.oxygen_saturation and sofa_params.oxygen_saturation.is_available:
                params.oxygen_saturation = News2Parameter(
                    value=sofa_params.oxygen_saturation.value,
                    unit=sofa_params.oxygen_saturation.unit,
                    timestamp=sofa_params.oxygen_saturation.timestamp,
                    is_estimated=sofa_params.oxygen_saturation.is_estimated,
                    source="reused_sofa"
                )
        
        return params

class News2ComponentScore(BaseModel):
    """Individual NEWS2 component score"""
    component: str
    score: int = Field(ge=0, le=3, description="NEWS2 component score (0-3)")
    threshold_met: bool
    interpretation: str
    parameters_used: List[str]

class News2ScoreResult(BaseModel):
    """Complete NEWS2 score calculation result"""
    patient_id: str
    timestamp: datetime
    
    # Component scores (7 components)
    respiratory_rate_score: News2ComponentScore
    oxygen_saturation_score: News2ComponentScore
    supplemental_oxygen_score: News2ComponentScore
    temperature_score: News2ComponentScore
    systolic_bp_score: News2ComponentScore
    heart_rate_score: News2ComponentScore
    consciousness_score: News2ComponentScore
    
    # Total score and assessment
    total_score: int = Field(ge=0, le=20, description="Total NEWS2 score (0-20)")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    clinical_response: str
    
    # Data quality indicators
    estimated_parameters_count: int = Field(ge=0, description="Number of estimated parameters")
    missing_parameters: List[str] = Field(description="List of missing parameter names")
    data_reliability_score: float = Field(ge=0.0, le=1.0, description="Data reliability (0-1)")
    
    # Special flags
    any_parameter_score_3: bool = Field(description="Any single parameter scored 3 points")
    
    @computed_field
    @property
    def clinical_interpretation(self) -> str:
        """Clinical interpretation of NEWS2 score"""
        if self.risk_level == "HIGH":
            return "High risk - Emergency assessment and continuous monitoring required"
        elif self.risk_level == "MEDIUM" or self.any_parameter_score_3:
            return "Medium risk - Urgent clinical review within 1 hour required"
        else:
            return "Low risk - Routine monitoring (4-12 hourly)"
    
    @computed_field
    @property
    def monitoring_frequency(self) -> str:
        """Recommended monitoring frequency"""
        if self.risk_level == "HIGH":
            return "Continuous monitoring"
        elif self.risk_level == "MEDIUM" or self.any_parameter_score_3:
            return "Hourly monitoring"
        else:
            return "4-12 hourly monitoring"
    
    @computed_field
    @property
    def escalation_required(self) -> bool:
        """Whether escalation is required"""
        return self.risk_level in ["MEDIUM", "HIGH"] or self.any_parameter_score_3

class News2ScoreSummary(BaseModel):
    """Summary version of NEWS2 score for API responses"""
    total_score: int = Field(ge=0, le=20)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    clinical_response: str
    clinical_interpretation: str
    monitoring_frequency: str
    escalation_required: bool
    data_reliability_score: float
    timestamp: datetime
    
    # Component breakdown (True means scored points)
    respiratory_rate_elevated: bool = Field(description="Respiratory rate scored points")
    oxygen_saturation_low: bool = Field(description="Oxygen saturation scored points")
    on_supplemental_oxygen: bool = Field(description="Patient on supplemental oxygen (2 points)")
    temperature_abnormal: bool = Field(description="Temperature scored points")
    hypotension_present: bool = Field(description="Systolic BP scored points")
    heart_rate_abnormal: bool = Field(description="Heart rate scored points")
    consciousness_impaired: bool = Field(description="Consciousness scored points")
    any_single_parameter_high: bool = Field(description="Any parameter scored 3 points")
    
    @classmethod
    def from_result(cls, result: News2ScoreResult) -> "News2ScoreSummary":
        """Create summary from full NEWS2 result"""
        return cls(
            total_score=result.total_score,
            risk_level=result.risk_level,
            clinical_response=result.clinical_response,
            clinical_interpretation=result.clinical_interpretation,
            monitoring_frequency=result.monitoring_frequency,
            escalation_required=result.escalation_required,
            data_reliability_score=result.data_reliability_score,
            timestamp=result.timestamp,
            respiratory_rate_elevated=result.respiratory_rate_score.score > 0,
            oxygen_saturation_low=result.oxygen_saturation_score.score > 0,
            on_supplemental_oxygen=result.supplemental_oxygen_score.score > 0,
            temperature_abnormal=result.temperature_score.score > 0,
            hypotension_present=result.systolic_bp_score.score > 0,
            heart_rate_abnormal=result.heart_rate_score.score > 0,
            consciousness_impaired=result.consciousness_score.score > 0,
            any_single_parameter_high=result.any_parameter_score_3
        )

class News2RiskAssessment(BaseModel):
    """Detailed risk assessment based on NEWS2 score"""
    score: int
    risk_level: str
    clinical_response: str
    recommendations: List[str]
    monitoring_frequency: str
    urgent_action_required: bool
    
    @classmethod
    def from_news2_score(cls, news2_score: int, any_parameter_score_3: bool = False) -> "News2RiskAssessment":
        """Create risk assessment from NEWS2 score"""
        # Determine base risk level from total score
        if news2_score >= 7:
            base_risk = "HIGH"
        elif news2_score >= 5:
            base_risk = "MEDIUM"
        else:
            base_risk = "LOW"
        
        # Override to MEDIUM if any single parameter is 3
        if any_parameter_score_3 and base_risk == "LOW":
            base_risk = "MEDIUM"
        
        if base_risk == "HIGH":
            return cls(
                score=news2_score,
                risk_level="HIGH",
                clinical_response="Emergency assessment",
                recommendations=[
                    "Emergency clinical assessment",
                    "Continuous monitoring",
                    "Critical care team involvement",
                    "Consider immediate intervention",
                    "Escalate to senior clinician immediately"
                ],
                monitoring_frequency="Continuous",
                urgent_action_required=True
            )
        elif base_risk == "MEDIUM":
            return cls(
                score=news2_score,
                risk_level="MEDIUM",
                clinical_response="Urgent review within 1 hour",
                recommendations=[
                    "Urgent clinical review within 1 hour",
                    "Increase monitoring to hourly",
                    "Consider escalation to critical care",
                    "Reassess frequently",
                    "Document clinical decisions"
                ],
                monitoring_frequency="Hourly",
                urgent_action_required=True
            )
        else:
            return cls(
                score=news2_score,
                risk_level="LOW",
                clinical_response="Routine monitoring",
                recommendations=[
                    "Continue routine monitoring",
                    "Reassess at 4-12 hourly intervals",
                    "Monitor for clinical deterioration"
                ],
                monitoring_frequency="4-12 hourly",
                urgent_action_required=False
            )


def rebuild_models():
    """Rebuild models to resolve forward references after all imports"""
    try:
        # Rebuild all NEWS2 models
        News2Parameter.model_rebuild()
        News2Parameters.model_rebuild()
        News2ComponentScore.model_rebuild()
        News2ScoreResult.model_rebuild()
        News2ScoreSummary.model_rebuild()
        News2RiskAssessment.model_rebuild()
    except Exception:
        pass  # Handle any import issues gracefully