"""
Simplified SOFA Models

Streamlined model structure that follows KISS principles by:
1. Combining related models
2. Reducing unnecessary intermediate models
3. Simplifying computed field logic
4. Maintaining essential functionality
"""

from pydantic import BaseModel, Field, computed_field
from typing import Optional, Dict, Any, List, Literal, Union
from datetime import datetime
from app.core.sofa_constants import SofaMortalityRisk, SofaSeverityClassification


class SofaParameter(BaseModel):
    """Individual SOFA parameter with simplified metadata"""
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    is_estimated: bool = False
    source: str = "measured"  # "measured", "estimated", "default", "calculated"
    
    @computed_field
    @property
    def is_available(self) -> bool:
        return self.value is not None


class SofaOrganScore(BaseModel):
    """Individual organ system score with essential information"""
    organ: str
    score: int = Field(ge=0, le=4)
    interpretation: str
    parameters_used: List[str] = Field(default_factory=list)
    
    @computed_field
    @property
    def severity(self) -> str:
        """Simple severity interpretation"""
        severity_map = {0: "Normal", 1: "Mild", 2: "Moderate", 3: "Severe", 4: "Critical"}
        return severity_map.get(self.score, "Unknown")


class SofaScoreResult(BaseModel):
    """Complete SOFA score with essential clinical information"""
    patient_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Individual organ scores
    respiratory: SofaOrganScore
    coagulation: SofaOrganScore
    liver: SofaOrganScore
    cardiovascular: SofaOrganScore
    cns: SofaOrganScore
    renal: SofaOrganScore
    
    # Total score and metadata
    total_score: int = Field(ge=0, le=24)
    estimated_parameters_count: int = 0
    missing_parameters: List[str] = Field(default_factory=list)
    data_reliability: float = Field(ge=0.0, le=1.0, default=1.0)
    
    @computed_field
    @property
    def mortality_risk(self) -> str:
        """Get mortality risk from total score"""
        return SofaMortalityRisk.get_mortality_risk(self.total_score)
    
    @computed_field
    @property
    def severity_classification(self) -> str:
        """Get severity classification from total score"""
        return SofaSeverityClassification.get_severity(self.total_score)
    
    @computed_field
    @property
    def organ_scores_dict(self) -> Dict[str, int]:
        """Dictionary of organ scores for easy access"""
        return {
            "respiratory": self.respiratory.score,
            "coagulation": self.coagulation.score,
            "liver": self.liver.score,
            "cardiovascular": self.cardiovascular.score,
            "cns": self.cns.score,
            "renal": self.renal.score
        }
    
    @computed_field
    @property
    def dysfunctional_organs_count(self) -> int:
        """Count of organs with dysfunction (score > 0)"""
        return sum(1 for score in self.organ_scores_dict.values() if score > 0)
    
    @computed_field
    @property
    def severe_organs(self) -> List[str]:
        """List of organs with severe dysfunction (score >= 3)"""
        severe = []
        for organ, score in self.organ_scores_dict.items():
            if score >= 3:
                severe.append(organ.title())
        return severe
    
    @computed_field
    @property
    def clinical_alerts(self) -> List[str]:
        """Generated clinical alerts based on score"""
        alerts = []
        
        if self.total_score >= 15:
            alerts.append("CRITICAL: Extremely high mortality risk")
        elif self.total_score >= 10:
            alerts.append("HIGH: Significant mortality risk")
        
        if self.dysfunctional_organs_count >= 3:
            alerts.append(f"Multiple organ dysfunction ({self.dysfunctional_organs_count} systems)")
        
        for organ in self.severe_organs:
            alerts.append(f"Severe {organ.lower()} dysfunction")
        
        if self.estimated_parameters_count >= 3:
            alerts.append("Data quality concern: Multiple estimated parameters")
        
        return alerts


class SepsisAssessment(BaseModel):
    """Simplified sepsis risk assessment"""
    risk_level: Literal["MINIMAL", "LOW", "MODERATE", "HIGH", "CRITICAL"]
    recommendation: str
    requires_immediate_attention: bool
    contributing_factors: List[str] = Field(default_factory=list)
    
    @classmethod
    def from_sofa_score(cls, sofa_score: int, organ_dysfunction_count: int, 
                       severe_organs: List[str], estimated_params: int) -> "SepsisAssessment":
        """Create assessment from SOFA score and related metrics"""
        # Determine risk level and recommendation
        if sofa_score >= 15:
            risk_level = "CRITICAL"
            recommendation = "Immediate intensive care intervention required"
            requires_attention = True
        elif sofa_score >= 10:
            risk_level = "HIGH"
            recommendation = "Consider ICU consultation and aggressive treatment"
            requires_attention = True
        elif sofa_score >= 6:
            risk_level = "MODERATE"
            recommendation = "Close monitoring and consider treatment escalation"
            requires_attention = False
        elif sofa_score >= 3:
            risk_level = "LOW"
            recommendation = "Monitor for deterioration"
            requires_attention = False
        else:
            risk_level = "MINIMAL"
            recommendation = "Standard monitoring"
            requires_attention = False
        
        # Contributing factors
        factors = []
        if organ_dysfunction_count >= 3:
            factors.append(f"Multiple organ dysfunction ({organ_dysfunction_count} systems)")
        
        for organ in severe_organs:
            factors.append(f"Severe {organ.lower()} dysfunction")
        
        if estimated_params >= 3:
            factors.append("Limited data availability")
        
        return cls(
            risk_level=risk_level,
            recommendation=recommendation,
            requires_immediate_attention=requires_attention,
            contributing_factors=factors
        )


class SepsisScoreRequest(BaseModel):
    """Simplified request parameters"""
    timestamp: Optional[datetime] = None
    include_parameters: bool = False
    scoring_systems: str = "SOFA"
    
    @computed_field
    @property
    def requested_systems(self) -> List[str]:
        """Parse requested scoring systems"""
        return [system.strip().upper() for system in self.scoring_systems.split(",")]


class CalculationMetadata(BaseModel):
    """Essential calculation metadata"""
    estimated_parameters: int
    missing_parameters: List[str]
    calculation_time_ms: Optional[float] = None
    data_sources: List[str] = Field(default_factory=lambda: ["FHIR"])
    last_parameter_update: Optional[datetime] = None


class SepsisAssessmentResponse(BaseModel):
    """Complete but simplified sepsis assessment response"""
    patient_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Core scoring data
    sofa_score: SofaScoreResult
    sepsis_assessment: SepsisAssessment
    
    # Optional detailed data (only if explicitly requested)
    detailed_parameters: Optional[Dict[str, Any]] = None  # Simplified to generic dict
    
    # Calculation metadata
    calculation_metadata: CalculationMetadata
    
    @computed_field
    @property
    def overall_risk_level(self) -> str:
        """Backward compatibility field"""
        return self.sepsis_assessment.risk_level
    
    @computed_field
    @property
    def requires_immediate_attention(self) -> bool:
        """Backward compatibility field"""
        return self.sepsis_assessment.requires_immediate_attention
    
    @computed_field
    @property
    def summary(self) -> str:
        """One-line clinical summary"""
        return (f"SOFA: {self.sofa_score.total_score}/24 ({self.sofa_score.severity_classification}) "
               f"Risk: {self.sepsis_assessment.risk_level} ({self.sofa_score.mortality_risk})")


class BatchSepsisScoreRequest(BaseModel):
    """Simplified batch request"""
    patient_ids: List[str] = Field(min_items=1, max_items=50)
    timestamp: Optional[datetime] = None
    include_parameters: bool = False
    scoring_systems: str = "SOFA"


class BatchSepsisScoreResponse(BaseModel):
    """Simplified batch response"""
    timestamp: datetime = Field(default_factory=datetime.now)
    patient_scores: List[SepsisAssessmentResponse] = Field(default_factory=list)
    errors: List[Dict[str, str]] = Field(default_factory=list)
    
    @computed_field
    @property
    def success_count(self) -> int:
        return len(self.patient_scores)
    
    @computed_field
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @computed_field
    @property
    def high_risk_patients(self) -> List[str]:
        """Patient IDs with high or critical risk"""
        return [
            score.patient_id for score in self.patient_scores
            if score.sepsis_assessment.risk_level in ["HIGH", "CRITICAL"]
        ]


# Legacy compatibility models - simplified versions of original complex models
class VasopressorDoses(BaseModel):
    """Simplified vasopressor doses"""
    dopamine: Optional[float] = None
    epinephrine: Optional[float] = None
    norepinephrine: Optional[float] = None
    
    @computed_field
    @property
    def has_any(self) -> bool:
        return any(dose and dose > 0 for dose in [self.dopamine, self.epinephrine, self.norepinephrine])


# For backward compatibility, create aliases to the original model names
SofaScoreSummary = SofaScoreResult  # Simplified - use the main result directly
SepsisRiskLevel = SepsisAssessment  # Simplified naming