from pydantic import BaseModel, Field, computed_field
from typing import Optional, Dict, Any, List, Literal, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.models.qsofa import QsofaScoreSummary, QsofaParameters, QsofaScoreResult
    from app.models.news2 import News2ScoreSummary, News2Parameters, News2ScoreResult

class SofaParameter(BaseModel):
    """Individual SOFA parameter with metadata"""
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    is_estimated: bool = False
    last_known_value: Optional[float] = None
    source: Optional[str] = None  # "measured", "estimated", "default"
    
    @computed_field
    @property
    def is_available(self) -> bool:
        return self.value is not None

class VasopressorDoses(BaseModel):
    """Vasopressor dosing information"""
    dopamine: Optional[float] = None  # mcg/kg/min
    dobutamine: Optional[float] = None  # mcg/kg/min
    epinephrine: Optional[float] = None  # mcg/kg/min
    norepinephrine: Optional[float] = None  # mcg/kg/min
    phenylephrine: Optional[float] = None  # mcg/kg/min
    
    @computed_field
    @property
    def has_any_vasopressor(self) -> bool:
        return any([
            self.dopamine and self.dopamine > 0,
            self.dobutamine and self.dobutamine > 0,
            self.epinephrine and self.epinephrine > 0,
            self.norepinephrine and self.norepinephrine > 0,
            self.phenylephrine and self.phenylephrine > 0
        ])

class SofaParameters(BaseModel):
    """Complete set of SOFA parameters"""
    patient_id: str
    timestamp: Optional[datetime] = None
    
    # Respiratory system
    pao2: SofaParameter = Field(default_factory=SofaParameter)
    fio2: SofaParameter = Field(default_factory=SofaParameter)
    pao2_fio2_ratio: SofaParameter = Field(default_factory=SofaParameter)
    mechanical_ventilation: bool = False
    
    # Coagulation system
    platelets: SofaParameter = Field(default_factory=SofaParameter)
    
    # Liver system
    bilirubin: SofaParameter = Field(default_factory=SofaParameter)
    
    # Cardiovascular system
    map_value: SofaParameter = Field(default_factory=SofaParameter)
    systolic_bp: SofaParameter = Field(default_factory=SofaParameter)
    diastolic_bp: SofaParameter = Field(default_factory=SofaParameter)
    vasopressor_doses: VasopressorDoses = Field(default_factory=VasopressorDoses)
    
    # Central nervous system
    gcs: SofaParameter = Field(default_factory=SofaParameter)
    
    # Renal system
    creatinine: SofaParameter = Field(default_factory=SofaParameter)
    urine_output_24h: SofaParameter = Field(default_factory=SofaParameter)
    
    @computed_field
    @property
    def estimated_parameters_count(self) -> int:
        """Count of parameters that were estimated or defaulted"""
        parameters = [
            self.pao2_fio2_ratio, self.platelets, self.bilirubin,
            self.map_value, self.gcs, self.creatinine, self.urine_output_24h
        ]
        return sum(1 for param in parameters if param.is_estimated)
    
    @computed_field
    @property
    def missing_parameters(self) -> List[str]:
        """List of parameter names that are missing or estimated"""
        missing = []
        parameter_mapping = {
            "pao2_fio2_ratio": self.pao2_fio2_ratio,
            "platelets": self.platelets,
            "bilirubin": self.bilirubin,
            "map_value": self.map_value,
            "gcs": self.gcs,
            "creatinine": self.creatinine,
            "urine_output_24h": self.urine_output_24h
        }
        
        for name, param in parameter_mapping.items():
            if not param.is_available or param.is_estimated:
                missing.append(name)
        
        return missing

class SofaComponentScore(BaseModel):
    """Individual organ system SOFA score"""
    organ_system: str
    score: int = Field(ge=0, le=4)
    max_score: int = 4
    parameters_used: List[str] = Field(default_factory=list)
    is_estimated: bool = False
    interpretation: Optional[str] = None
    
    @computed_field
    @property
    def severity_level(self) -> str:
        """Severity interpretation based on score"""
        if self.score == 0:
            return "Normal"
        elif self.score == 1:
            return "Mild dysfunction"
        elif self.score == 2:
            return "Moderate dysfunction"
        elif self.score == 3:
            return "Severe dysfunction"
        elif self.score == 4:
            return "Life-threatening dysfunction"
        else:
            return "Unknown"

class SofaScoreResult(BaseModel):
    """Complete SOFA score result"""
    patient_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Individual organ scores
    respiratory_score: SofaComponentScore
    coagulation_score: SofaComponentScore
    liver_score: SofaComponentScore
    cardiovascular_score: SofaComponentScore
    cns_score: SofaComponentScore
    renal_score: SofaComponentScore
    
    # Total score
    total_score: int = Field(ge=0, le=24)
    
    # Data quality indicators
    estimated_parameters_count: int = 0
    missing_parameters: List[str] = Field(default_factory=list)
    data_reliability_score: float = Field(ge=0.0, le=1.0, default=1.0)
    
    @computed_field
    @property
    def mortality_risk(self) -> str:
        """Mortality risk assessment based on total SOFA score"""
        if self.total_score <= 6:
            return "Low (<10%)"
        elif self.total_score <= 9:
            return "Moderate (15-20%)"
        elif self.total_score <= 12:
            return "High (40-50%)"
        elif self.total_score <= 15:
            return "Very High (50-60%)"
        else:
            return "Extremely High (>80%)"
    
    @computed_field
    @property
    def severity_classification(self) -> str:
        """Overall severity classification"""
        if self.total_score <= 2:
            return "No organ dysfunction"
        elif self.total_score <= 6:
            return "Mild organ dysfunction"
        elif self.total_score <= 12:
            return "Moderate organ dysfunction"
        else:
            return "Severe organ dysfunction"
    
    @computed_field
    @property
    def organ_dysfunction_count(self) -> int:
        """Number of organ systems with dysfunction (score > 0)"""
        scores = [
            self.respiratory_score.score,
            self.coagulation_score.score,
            self.liver_score.score,
            self.cardiovascular_score.score,
            self.cns_score.score,
            self.renal_score.score
        ]
        return sum(1 for score in scores if score > 0)
    
    @computed_field
    @property
    def severely_dysfunctional_organs(self) -> List[str]:
        """List of organ systems with severe dysfunction (score >= 3)"""
        severe_organs = []
        organ_scores = [
            ("Respiratory", self.respiratory_score.score),
            ("Coagulation", self.coagulation_score.score),
            ("Liver", self.liver_score.score),
            ("Cardiovascular", self.cardiovascular_score.score),
            ("Central Nervous System", self.cns_score.score),
            ("Renal", self.renal_score.score)
        ]
        
        for organ, score in organ_scores:
            if score >= 3:
                severe_organs.append(organ)
        
        return severe_organs
    
    @computed_field
    @property
    def clinical_alerts(self) -> List[str]:
        """Clinical alerts based on SOFA score"""
        alerts = []
        
        if self.total_score >= 15:
            alerts.append("CRITICAL: Extremely high mortality risk")
        elif self.total_score >= 10:
            alerts.append("HIGH: Significant mortality risk")
        
        if self.organ_dysfunction_count >= 3:
            alerts.append(f"Multiple organ dysfunction ({self.organ_dysfunction_count} systems)")
        
        if self.severely_dysfunctional_organs:
            for organ in self.severely_dysfunctional_organs:
                alerts.append(f"Severe {organ.lower()} dysfunction")
        
        if self.estimated_parameters_count >= 3:
            alerts.append("Data quality concern: Multiple estimated parameters")
        
        return alerts

class SofaScoreResponse(BaseModel):
    """API response for SOFA score calculation"""
    patient_id: str
    sofa_result: SofaScoreResult
    parameters_used: SofaParameters
    calculation_metadata: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    @computed_field
    @property
    def requires_immediate_attention(self) -> bool:
        """Whether the SOFA score indicates need for immediate clinical attention"""
        return (
            self.sofa_result.total_score >= 10 or
            len(self.sofa_result.severely_dysfunctional_organs) >= 2 or
            self.sofa_result.cardiovascular_score.score >= 3
        )
    
    @computed_field
    @property
    def summary(self) -> str:
        """Clinical summary of SOFA assessment"""
        total = self.sofa_result.total_score
        severity = self.sofa_result.severity_classification
        mortality = self.sofa_result.mortality_risk
        
        summary = f"SOFA Score: {total}/24 - {severity}. Mortality Risk: {mortality}."
        
        if self.sofa_result.severely_dysfunctional_organs:
            organs = ", ".join(self.sofa_result.severely_dysfunctional_organs)
            summary += f" Severe dysfunction: {organs}."
        
        return summary

class SofaScoreTrend(BaseModel):
    """SOFA score trend over time"""
    patient_id: str
    scores: List[SofaScoreResult] = Field(default_factory=list)
    trend_direction: Optional[str] = None  # "improving", "worsening", "stable"
    change_rate: Optional[float] = None
    time_period_hours: Optional[int] = None
    
    @computed_field
    @property
    def latest_score(self) -> Optional[SofaScoreResult]:
        """Most recent SOFA score"""
        if self.scores:
            return max(self.scores, key=lambda x: x.timestamp)
        return None
    
    @computed_field
    @property
    def score_change_24h(self) -> Optional[int]:
        """Change in SOFA score over last 24 hours"""
        if len(self.scores) < 2:
            return None
        
        latest = self.latest_score
        if not latest:
            return None
        
        # Find score from 24 hours ago
        cutoff_time = latest.timestamp.timestamp() - (24 * 3600)
        historical_scores = [
            score for score in self.scores 
            if score.timestamp.timestamp() <= cutoff_time
        ]
        
        if not historical_scores:
            return None
        
        historical = max(historical_scores, key=lambda x: x.timestamp)
        return latest.total_score - historical.total_score

# API Request/Response Models for Sepsis Scoring Endpoint

class SepsisScoreRequest(BaseModel):
    """Request parameters for sepsis score calculation"""
    timestamp: Optional[datetime] = None
    include_parameters: bool = Field(default=False, description="Include detailed parameter data in response")
    scoring_systems: str = Field(default="SOFA", description="Comma-separated list of scoring systems (SOFA, qSOFA, NEWS2)")
    
    @computed_field
    @property
    def requested_systems(self) -> List[str]:
        """Parse requested scoring systems"""
        return [system.strip().upper() for system in self.scoring_systems.split(",")]

class SofaScoreSummary(BaseModel):
    """Summarized SOFA score for API response"""
    total_score: int = Field(ge=0, le=24)
    mortality_risk: str
    severity_classification: str
    individual_scores: Dict[str, int] = Field(default_factory=dict)
    clinical_alerts: List[str] = Field(default_factory=list)
    data_reliability: float = Field(ge=0.0, le=1.0)
    
    @classmethod
    def from_sofa_result(cls, sofa_result: SofaScoreResult) -> "SofaScoreSummary":
        """Create summary from full SOFA result"""
        individual_scores = {
            "respiratory": sofa_result.respiratory_score.score,
            "coagulation": sofa_result.coagulation_score.score,
            "liver": sofa_result.liver_score.score,
            "cardiovascular": sofa_result.cardiovascular_score.score,
            "cns": sofa_result.cns_score.score,
            "renal": sofa_result.renal_score.score
        }
        
        return cls(
            total_score=sofa_result.total_score,
            mortality_risk=sofa_result.mortality_risk,
            severity_classification=sofa_result.severity_classification,
            individual_scores=individual_scores,
            clinical_alerts=sofa_result.clinical_alerts,
            data_reliability=sofa_result.data_reliability_score
        )

class SepsisRiskLevel(BaseModel):
    """Overall sepsis risk assessment"""
    risk_level: Literal["MINIMAL", "LOW", "MODERATE", "HIGH", "CRITICAL"]
    recommendation: str
    requires_immediate_attention: bool
    contributing_factors: List[str] = Field(default_factory=list)
    
    @classmethod
    def from_sofa_score(cls, sofa_result: SofaScoreResult) -> "SepsisRiskLevel":
        """Determine overall sepsis risk from SOFA score"""
        total_score = sofa_result.total_score
        
        # Determine risk level based on SOFA score
        if total_score >= 15:
            risk_level = "CRITICAL"
            recommendation = "Immediate intensive care intervention required"
            requires_attention = True
        elif total_score >= 10:
            risk_level = "HIGH"
            recommendation = "Consider ICU consultation and aggressive treatment"
            requires_attention = True
        elif total_score >= 6:
            risk_level = "MODERATE"
            recommendation = "Close monitoring and consider treatment escalation"
            requires_attention = False
        elif total_score >= 3:
            risk_level = "LOW"
            recommendation = "Monitor for deterioration"
            requires_attention = False
        else:
            risk_level = "MINIMAL"
            recommendation = "Standard monitoring"
            requires_attention = False
        
        # Contributing factors
        factors = []
        if sofa_result.organ_dysfunction_count >= 3:
            factors.append(f"Multiple organ dysfunction ({sofa_result.organ_dysfunction_count} systems)")
        
        for organ in sofa_result.severely_dysfunctional_organs:
            factors.append(f"Severe {organ.lower()} dysfunction")
        
        if sofa_result.estimated_parameters_count >= 3:
            factors.append("Limited data availability")
        
        return cls(
            risk_level=risk_level,
            recommendation=recommendation,
            requires_immediate_attention=requires_attention,
            contributing_factors=factors
        )
    
    @classmethod
    def from_scores(
        cls, 
        sofa_result: Optional[SofaScoreResult] = None, 
        qsofa_result: Optional["QsofaScoreResult"] = None,
        news2_result: Optional["News2ScoreResult"] = None
    ) -> "SepsisRiskLevel":
        """Determine overall sepsis risk from available scores"""
        # If multiple scores are available, combine them intelligently
        if (sofa_result and qsofa_result) or (sofa_result and news2_result) or (qsofa_result and news2_result):
            return cls._from_combined_scores(sofa_result, qsofa_result, news2_result)
        
        # If only SOFA is available, use existing logic
        if sofa_result and not qsofa_result and not news2_result:
            return cls.from_sofa_score(sofa_result)
        
        # If only qSOFA is available, base risk on qSOFA
        if qsofa_result and not sofa_result and not news2_result:
            return cls._from_qsofa_score(qsofa_result)
        
        # If only NEWS2 is available, base risk on NEWS2
        if news2_result and not sofa_result and not qsofa_result:
            return cls._from_news2_score(news2_result)
        
        # Default case (shouldn't happen)
        return cls(
            risk_level="MINIMAL",
            recommendation="Unable to assess - no scoring data available",
            requires_immediate_attention=False,
            contributing_factors=["No scoring data available"]
        )
    
    @classmethod
    def _from_qsofa_score(cls, qsofa_result: "QsofaScoreResult") -> "SepsisRiskLevel":
        """Determine sepsis risk from qSOFA score only"""
        if qsofa_result.total_score >= 2:
            return cls(
                risk_level="HIGH",
                recommendation="High risk for poor outcome - consider sepsis evaluation",
                requires_immediate_attention=True,
                contributing_factors=[f"qSOFA score {qsofa_result.total_score}/3 (≥2)"]
            )
        elif qsofa_result.total_score == 1:
            return cls(
                risk_level="MODERATE",
                recommendation="Moderate risk - monitor closely and reassess",
                requires_immediate_attention=False,
                contributing_factors=[f"qSOFA score {qsofa_result.total_score}/3"]
            )
        else:
            return cls(
                risk_level="LOW",
                recommendation="Low risk for poor outcome - continue routine monitoring",
                requires_immediate_attention=False,
                contributing_factors=[f"qSOFA score {qsofa_result.total_score}/3"]
            )
    
    @classmethod
    def _from_news2_score(cls, news2_result: "News2ScoreResult") -> "SepsisRiskLevel":
        """Determine sepsis risk from NEWS2 score only"""
        # Map NEWS2 risk levels to sepsis risk levels
        news2_to_sepsis_risk = {
            "HIGH": "HIGH",
            "MEDIUM": "MODERATE", 
            "LOW": "LOW"
        }
        
        sepsis_risk = news2_to_sepsis_risk.get(news2_result.risk_level, "LOW")
        
        if news2_result.risk_level == "HIGH":
            return cls(
                risk_level="HIGH",
                recommendation="High risk for clinical deterioration - emergency assessment required",
                requires_immediate_attention=True,
                contributing_factors=[f"NEWS2 score {news2_result.total_score}/20 (≥7)"]
            )
        elif news2_result.risk_level == "MEDIUM":
            return cls(
                risk_level="MODERATE",
                recommendation="Moderate risk for deterioration - urgent clinical review required",
                requires_immediate_attention=True,
                contributing_factors=[f"NEWS2 score {news2_result.total_score}/20 (5-6 or single parameter 3)"]
            )
        else:
            return cls(
                risk_level="LOW",
                recommendation="Low risk for deterioration - continue routine monitoring",
                requires_immediate_attention=False,
                contributing_factors=[f"NEWS2 score {news2_result.total_score}/20 (0-4)"]
            )
    
    @classmethod
    def _from_combined_scores(
        cls, 
        sofa_result: Optional[SofaScoreResult] = None, 
        qsofa_result: Optional["QsofaScoreResult"] = None,
        news2_result: Optional["News2ScoreResult"] = None
    ) -> "SepsisRiskLevel":
        """Determine sepsis risk from combined SOFA, qSOFA, and NEWS2 scores"""
        # Get individual risk assessments for available scores
        individual_risks = []
        combined_factors = []
        
        if sofa_result:
            sofa_risk = cls.from_sofa_score(sofa_result)
            individual_risks.append(sofa_risk)
            combined_factors.append(f"SOFA score {sofa_result.total_score}/24")
        
        if qsofa_result:
            qsofa_risk = cls._from_qsofa_score(qsofa_result)
            individual_risks.append(qsofa_risk)
            combined_factors.append(f"qSOFA score {qsofa_result.total_score}/3")
        
        if news2_result:
            news2_risk = cls._from_news2_score(news2_result)
            individual_risks.append(news2_risk)
            combined_factors.append(f"NEWS2 score {news2_result.total_score}/20")
        
        # Risk level hierarchy for comparison
        risk_hierarchy = {"MINIMAL": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3, "CRITICAL": 4}
        
        # Find the highest risk level among all available scores
        highest_risk_level = 0
        primary_assessment = None
        
        for risk in individual_risks:
            risk_level = risk_hierarchy.get(risk.risk_level, 0)
            if risk_level > highest_risk_level:
                highest_risk_level = risk_level
                primary_assessment = risk
        
        # Determine if immediate attention is required (any system indicates it)
        requires_attention = any(risk.requires_immediate_attention for risk in individual_risks)
        
        # Special high-priority cases that override normal priority
        high_priority_factors = []
        if qsofa_result and qsofa_result.total_score >= 2:
            high_priority_factors.append("qSOFA ≥2 (sepsis concern)")
        if news2_result and news2_result.risk_level == "HIGH":
            high_priority_factors.append("NEWS2 high risk (clinical deterioration)")
        if sofa_result and sofa_result.total_score >= 10:
            high_priority_factors.append("SOFA ≥10 (organ dysfunction)")
        
        # Combine all contributing factors
        if high_priority_factors:
            combined_factors.extend(high_priority_factors)
        
        # Add individual system contributing factors
        for risk in individual_risks:
            combined_factors.extend(risk.contributing_factors)
        
        # Use primary assessment or create default
        if primary_assessment:
            final_risk = primary_assessment.risk_level
            primary_recommendation = primary_assessment.recommendation
        else:
            final_risk = "MINIMAL"
            primary_recommendation = "No scoring data available"
        
        # Enhanced recommendation for combined scores
        if len(individual_risks) > 1:
            system_names = []
            if sofa_result: system_names.append("SOFA")
            if qsofa_result: system_names.append("qSOFA")  
            if news2_result: system_names.append("NEWS2")
            
            combined_system_text = " + ".join(system_names)
            primary_recommendation = f"Combined assessment ({combined_system_text}): {primary_recommendation}"
        
        return cls(
            risk_level=final_risk,
            recommendation=primary_recommendation,
            requires_immediate_attention=requires_attention,
            contributing_factors=combined_factors
        )

class CalculationMetadata(BaseModel):
    """Metadata about the score calculation"""
    estimated_parameters: int
    missing_parameters: List[str]
    calculation_time_ms: Optional[float] = None
    data_sources: List[str] = Field(default_factory=lambda: ["FHIR"])
    last_parameter_update: Optional[datetime] = None

class SepsisAssessmentResponse(BaseModel):
    """Complete sepsis assessment API response"""
    patient_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Scoring systems (at least one must be provided)
    sofa_score: Optional[SofaScoreSummary] = None
    qsofa_score: Optional["QsofaScoreSummary"] = None
    news2_score: Optional["News2ScoreSummary"] = None
    
    # Overall assessment
    sepsis_assessment: SepsisRiskLevel
    
    # Optional detailed data
    detailed_parameters: Optional[SofaParameters] = None
    detailed_qsofa_parameters: Optional["QsofaParameters"] = None
    detailed_news2_parameters: Optional["News2Parameters"] = None
    full_sofa_result: Optional[SofaScoreResult] = None
    
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

class BatchSepsisScoreRequest(BaseModel):
    """Request for batch sepsis score calculation (future use)"""
    patient_ids: List[str] = Field(min_items=1, max_items=50)
    timestamp: Optional[datetime] = None
    include_parameters: bool = False
    scoring_systems: str = "SOFA"

class BatchSepsisScoreResponse(BaseModel):
    """Response for batch sepsis score calculation (future use)"""
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    patient_scores: List[SepsisAssessmentResponse] = Field(default_factory=list)
    errors: List[Dict[str, str]] = Field(default_factory=list)  # patient_id -> error_message
    
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
        high_risk = []
        for score in self.patient_scores:
            if score.sepsis_assessment.risk_level in ["HIGH", "CRITICAL"]:
                high_risk.append(score.patient_id)
        return high_risk


# Rebuild models to resolve forward references
def rebuild_models():
    """Rebuild models to resolve forward references after all imports"""
    try:
        from app.models.qsofa import QsofaScoreSummary, QsofaParameters, QsofaScoreResult
        from app.models.news2 import News2ScoreSummary, News2Parameters, News2ScoreResult
        SepsisAssessmentResponse.model_rebuild()
        SepsisRiskLevel.model_rebuild()
    except ImportError:
        pass  # qSOFA or NEWS2 models not available yet