# app/models/ml_features.py

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from datetime import datetime

class RawClinicalParameters(BaseModel):
    """Raw clinical parameters matching API schema"""
    
    # Patient identifiers
    patient_id: str
    timestamp: datetime
    
    # Vital signs
    heart_rate: float = Field(..., ge=20, le=300)
    systolic_bp: float = Field(..., ge=40, le=300)
    diastolic_bp: float = Field(..., ge=20, le=200)
    mean_arterial_pressure: Optional[float] = Field(None, ge=40, le=130)
    respiratory_rate: float = Field(..., ge=5, le=60)
    temperature: float = Field(..., ge=30, le=45)
    oxygen_saturation: float = Field(..., ge=50, le=100)
    
    # SOFA parameters
    glasgow_coma_scale: float = Field(15, ge=3, le=15)
    pao2: Optional[float] = Field(None, ge=30, le=600)
    fio2: float = Field(0.21, ge=0.21, le=1.0)
    platelets: Optional[float] = Field(None, ge=1, le=1000)
    bilirubin: Optional[float] = Field(None, ge=0.1, le=50)
    creatinine: Optional[float] = Field(None, ge=0.1, le=25)
    urine_output_24h: Optional[float] = Field(None, ge=0, le=5000)
    
    # Support parameters
    mechanical_ventilation: bool = False
    supplemental_oxygen: bool = False
    
    # Vasopressors
    dopamine: float = Field(0, ge=0)
    dobutamine: float = Field(0, ge=0)
    epinephrine: float = Field(0, ge=0)
    norepinephrine: float = Field(0, ge=0)
    phenylephrine: float = Field(0, ge=0)
    
    @validator('mean_arterial_pressure', always=True)
    def calculate_map(cls, v, values):
        if v is None and 'systolic_bp' in values and 'diastolic_bp' in values:
            return (values['systolic_bp'] + 2 * values['diastolic_bp']) / 3
        return v

class EngineeredFeatureSet(BaseModel):
    """Complete set of engineered features for early sepsis detection"""
    
    # Hemodynamic features (Hidden patterns: Complex interactions)
    shock_index: float = Field(..., description="Heart rate / systolic BP ratio")
    modified_shock_index: float = Field(..., description="Heart rate / MAP ratio")
    age_shock_index: float = Field(..., description="Age-adjusted shock index")
    pulse_pressure: float = Field(..., description="Systolic - diastolic BP")
    pulse_pressure_ratio: float = Field(..., description="Pulse pressure / systolic BP")
    perfusion_pressure: float = Field(..., description="MAP - estimated CVP")
    hypotension_severity: float = Field(..., description="Severity of hypotension score")
    severe_hypotension: int = Field(..., description="Binary flag for severe hypotension")
    tachycardia_severity: float = Field(..., description="Severity of tachycardia")
    vasopressor_load: float = Field(..., description="Norepinephrine equivalent dose")
    on_vasopressors: int = Field(..., description="Binary flag for vasopressor use")
    high_dose_vasopressors: int = Field(..., description="Binary flag for high-dose vasopressors")
    
    # Respiratory features (Early patterns: Subtle changes before obvious failure)
    pf_ratio: float = Field(..., description="PaO2/FiO2 ratio")
    oxygenation_index: float = Field(..., description="FiO2 * 100 / P/F ratio")
    ards_severity: int = Field(..., description="ARDS severity level (0-3)")
    hypoxemia: int = Field(..., description="Binary flag for hypoxemia")
    severe_hypoxemia: int = Field(..., description="Binary flag for severe hypoxemia")
    hypoxemic_index: float = Field(..., description="Hypoxemia severity score")
    respiratory_support_score: float = Field(..., description="Level of respiratory support")
    tachypnea_severity: float = Field(..., description="Severity of tachypnea")
    respiratory_failure: int = Field(..., description="Binary flag for respiratory failure")
    work_of_breathing: float = Field(..., description="Estimated work of breathing")
    
    # Organ dysfunction (Multi-organ interactions)
    organ_failure_count: int = Field(..., description="Number of failing organ systems")
    multi_organ_failure: int = Field(..., description="Binary flag for multi-organ failure")
    aki_risk_score: float = Field(..., description="Acute kidney injury risk score")
    severe_aki: int = Field(..., description="Binary flag for severe AKI")
    oliguria: int = Field(..., description="Binary flag for oliguria")
    anuria: int = Field(..., description="Binary flag for anuria")
    estimated_gfr: float = Field(..., description="Estimated glomerular filtration rate")
    hyperbilirubinemia: int = Field(..., description="Binary flag for hyperbilirubinemia")
    severe_hyperbilirubinemia: int = Field(..., description="Binary flag for severe hyperbilirubinemia")
    hepatic_dysfunction_score: float = Field(..., description="Hepatic dysfunction severity")
    thrombocytopenia: int = Field(..., description="Binary flag for thrombocytopenia")
    severe_thrombocytopenia: int = Field(..., description="Binary flag for severe thrombocytopenia") 
    coagulopathy_score: float = Field(..., description="Coagulopathy severity score")
    altered_mental_status: int = Field(..., description="Binary flag for altered mental status")
    coma: int = Field(..., description="Binary flag for coma")
    neurological_dysfunction_score: float = Field(..., description="Neurological dysfunction score")
    
    # SOFA-like continuous scores
    sofa_respiratory: int = Field(..., description="SOFA respiratory component")
    sofa_coagulation: int = Field(..., description="SOFA coagulation component")
    sofa_liver: int = Field(..., description="SOFA liver component")
    
    # Sepsis pattern features (Personalized patterns: Age/comorbidity-specific)
    qsofa_score: int = Field(..., description="qSOFA total score")
    qsofa_respiratory_component: int = Field(..., description="qSOFA respiratory component")
    qsofa_bp_component: int = Field(..., description="qSOFA blood pressure component")
    qsofa_mental_component: int = Field(..., description="qSOFA mental status component")
    sirs_score: int = Field(..., description="SIRS total score")
    sirs_temp: int = Field(..., description="SIRS temperature component")
    sirs_hr: int = Field(..., description="SIRS heart rate component")
    sirs_rr: int = Field(..., description="SIRS respiratory rate component")
    fever: int = Field(..., description="Binary flag for fever")
    hypothermia: int = Field(..., description="Binary flag for hypothermia")
    temperature_abnormal: int = Field(..., description="Binary flag for abnormal temperature")
    temperature_deviation: float = Field(..., description="Deviation from normal temperature")
    septic_shock_pattern: int = Field(..., description="Binary flag for septic shock pattern")
    relative_bradycardia: int = Field(..., description="Binary flag for relative bradycardia")
    compensated_shock: int = Field(..., description="Binary flag for compensated shock")
    decompensated_shock: int = Field(..., description="Binary flag for decompensated shock")
    
    # Support intervention features
    on_mechanical_ventilation: int = Field(..., description="Binary flag for mechanical ventilation")
    high_fio2_requirement: int = Field(..., description="Binary flag for high FiO2 requirement")
    oxygen_dependency: float = Field(..., description="Oxygen dependency score")
    life_support_score: float = Field(..., description="Life support intervention score")
    critical_illness_score: float = Field(..., description="Critical illness severity score")
    
    # Raw features (selected clinically important parameters)
    heart_rate: float = Field(..., description="Heart rate (bpm)")
    systolic_bp: float = Field(..., description="Systolic blood pressure (mmHg)")
    diastolic_bp: float = Field(..., description="Diastolic blood pressure (mmHg)")
    mean_arterial_pressure: float = Field(..., description="Mean arterial pressure (mmHg)")
    respiratory_rate: float = Field(..., description="Respiratory rate (breaths/min)")
    temperature: float = Field(..., description="Body temperature (°C)")
    oxygen_saturation: float = Field(..., description="Oxygen saturation (%)")
    glasgow_coma_scale: float = Field(..., description="Glasgow Coma Scale")
    creatinine: Optional[float] = Field(None, description="Serum creatinine (mg/dL)")
    bilirubin: Optional[float] = Field(None, description="Total bilirubin (mg/dL)")
    platelets: Optional[float] = Field(None, description="Platelet count (×10³/μL)")
    pao2: Optional[float] = Field(None, description="Partial pressure of oxygen (mmHg)")
    fio2: float = Field(..., description="Fraction of inspired oxygen")
    urine_output_24h: Optional[float] = Field(None, description="24-hour urine output (mL)")
    
    class Config:
        schema_extra = {
            "example": {
                "shock_index": 1.2,
                "modified_shock_index": 1.8,
                "age_shock_index": 1.4,
                "pf_ratio": 180,
                "work_of_breathing": 450,
                "organ_failure_count": 2,
                "multi_organ_failure": 1,
                "qsofa_score": 2,
                "compensated_shock": 1,
                "life_support_score": 6,
                "critical_illness_score": 8.5
            }
        }

class FeatureQualityMetrics(BaseModel):
    """Metadata about feature quality and reliability"""
    
    data_completeness_score: float = Field(..., ge=0, le=1)
    has_invasive_monitoring: bool
    feature_engineering_version: str
    critical_params_available: List[str]
    missing_params: List[str]
    
    class Config:
        schema_extra = {
            "example": {
                "data_completeness_score": 0.85,
                "has_invasive_monitoring": True,
                "feature_engineering_version": "1.0.0",
                "critical_params_available": ["heart_rate", "blood_pressure"],
                "missing_params": ["lactate"]
            }
        }