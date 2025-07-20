from pydantic import BaseModel, Field, computed_field
from typing import Optional, List, Literal
from datetime import datetime

class QsofaParameter(BaseModel):
    """Individual qSOFA parameter with metadata"""
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    is_estimated: bool = False
    last_known_value: Optional[float] = None
    source: Optional[str] = None  # "measured", "estimated", "default", "calculated"
    
    @computed_field
    @property
    def is_available(self) -> bool:
        return self.value is not None

class QsofaParameters(BaseModel):
    """Complete set of qSOFA parameters"""
    patient_id: str
    timestamp: Optional[datetime] = None
    
    # qSOFA components
    respiratory_rate: QsofaParameter = Field(default_factory=QsofaParameter)
    systolic_bp: QsofaParameter = Field(default_factory=QsofaParameter)
    gcs: QsofaParameter = Field(default_factory=QsofaParameter)
    altered_mental_status: bool = False
    
    @computed_field
    @property
    def estimated_parameters_count(self) -> int:
        """Count of parameters that were estimated or defaulted"""
        parameters = [self.respiratory_rate, self.systolic_bp, self.gcs]
        return sum(1 for param in parameters if param.is_estimated)
    
    @computed_field
    @property
    def missing_parameters(self) -> List[str]:
        """List of parameter names that are missing or estimated"""
        missing = []
        parameter_mapping = {
            "respiratory_rate": self.respiratory_rate,
            "systolic_bp": self.systolic_bp,
            "gcs": self.gcs
        }
        
        for name, param in parameter_mapping.items():
            if not param.is_available or param.is_estimated:
                missing.append(name)
        
        return missing

class QsofaComponentScore(BaseModel):
    """Individual qSOFA component score"""
    component: str
    score: int = Field(ge=0, le=1, description="qSOFA component score (0 or 1)")
    threshold_met: bool
    interpretation: str
    parameters_used: List[str]

class QsofaScoreResult(BaseModel):
    """Complete qSOFA score calculation result"""
    patient_id: str
    timestamp: datetime
    
    # Component scores
    respiratory_score: QsofaComponentScore
    cardiovascular_score: QsofaComponentScore
    cns_score: QsofaComponentScore
    
    # Total score and assessment
    total_score: int = Field(ge=0, le=3, description="Total qSOFA score (0-3)")
    high_risk: bool = Field(description="qSOFA ≥2 indicates high risk")
    
    # Data quality indicators
    estimated_parameters_count: int = Field(ge=0, description="Number of estimated parameters")
    missing_parameters: List[str] = Field(description="List of missing parameter names")
    data_reliability_score: float = Field(ge=0.0, le=1.0, description="Data reliability (0-1)")
    
    @computed_field
    @property
    def risk_level(self) -> str:
        """Risk level based on qSOFA score"""
        if self.total_score >= 2:
            return "HIGH"
        elif self.total_score == 1:
            return "MODERATE"
        else:
            return "LOW"
    
    @computed_field
    @property
    def clinical_interpretation(self) -> str:
        """Clinical interpretation of qSOFA score"""
        if self.total_score >= 2:
            return "High risk for poor outcome. Consider sepsis evaluation and management."
        elif self.total_score == 1:
            return "Moderate risk. Monitor closely and reassess."
        else:
            return "Low risk for poor outcome."

class QsofaScoreSummary(BaseModel):
    """Summary version of qSOFA score for API responses"""
    total_score: int = Field(ge=0, le=3)
    risk_level: Literal["LOW", "MODERATE", "HIGH"]
    high_risk: bool
    clinical_interpretation: str
    data_reliability_score: float
    timestamp: datetime
    
    # Component breakdown
    respiratory_rate_elevated: bool = Field(description="Respiratory rate ≥22")
    hypotension_present: bool = Field(description="Systolic BP ≤100")
    altered_mental_status_present: bool = Field(description="GCS <15 or altered consciousness")
    
    @classmethod
    def from_result(cls, result: QsofaScoreResult) -> "QsofaScoreSummary":
        """Create summary from full qSOFA result"""
        return cls(
            total_score=result.total_score,
            risk_level=result.risk_level,
            high_risk=result.high_risk,
            clinical_interpretation=result.clinical_interpretation,
            data_reliability_score=result.data_reliability_score,
            timestamp=result.timestamp,
            respiratory_rate_elevated=result.respiratory_score.threshold_met,
            hypotension_present=result.cardiovascular_score.threshold_met,
            altered_mental_status_present=result.cns_score.threshold_met
        )

class QsofaRiskAssessment(BaseModel):
    """Detailed risk assessment based on qSOFA score"""
    score: int
    risk_level: str
    mortality_risk_description: str
    recommendations: List[str]
    urgent_action_required: bool
    
    @classmethod
    def from_qsofa_score(cls, qsofa_score: int) -> "QsofaRiskAssessment":
        """Create risk assessment from qSOFA score"""
        if qsofa_score >= 2:
            return cls(
                score=qsofa_score,
                risk_level="HIGH",
                mortality_risk_description="High risk for in-hospital mortality and ICU admission",
                recommendations=[
                    "Consider immediate sepsis evaluation",
                    "Initiate sepsis management protocols",
                    "Consider ICU consultation",
                    "Monitor vital signs frequently",
                    "Reassess within 1 hour"
                ],
                urgent_action_required=True
            )
        elif qsofa_score == 1:
            return cls(
                score=qsofa_score,
                risk_level="MODERATE", 
                mortality_risk_description="Moderate risk for adverse outcomes",
                recommendations=[
                    "Monitor closely for clinical deterioration",
                    "Reassess qSOFA score frequently",
                    "Consider infectious workup if indicated",
                    "Monitor vital signs every 2-4 hours"
                ],
                urgent_action_required=False
            )
        else:
            return cls(
                score=qsofa_score,
                risk_level="LOW",
                mortality_risk_description="Low risk for adverse outcomes",
                recommendations=[
                    "Continue routine monitoring",
                    "Reassess if clinical status changes"
                ],
                urgent_action_required=False
            )


# Rebuild models to resolve any forward references
def rebuild_models():
    """Rebuild models to resolve forward references after all imports"""
    try:
        # Rebuild all qSOFA models
        QsofaParameter.model_rebuild()
        QsofaParameters.model_rebuild()
        QsofaComponentScore.model_rebuild()
        QsofaScoreResult.model_rebuild()
        QsofaScoreSummary.model_rebuild()
        QsofaRiskAssessment.model_rebuild()
        
        # Also rebuild SOFA models that reference qSOFA
        from app.models.sofa import rebuild_models as rebuild_sofa_models
        rebuild_sofa_models()
    except ImportError:
        pass  # SOFA models not available yet