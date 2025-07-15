from pydantic import BaseModel, Field, computed_field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.utils.calculations import calculate_mean_arterial_pressure, calculate_pulse_pressure, is_fever

class VitalSign(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    status: Optional[str] = None
    interpretation: Optional[str] = None
    reference_range: Optional[str] = None
    loinc_code: Optional[str] = None
    display_name: Optional[str] = None
    
    @computed_field
    @property
    def is_abnormal(self) -> bool:
        if self.interpretation:
            abnormal_codes = ["H", "HH", "L", "LL", "A", "AA", "CRITICAL", "PANIC"]
            return self.interpretation.upper() in abnormal_codes
        return False
    
    @computed_field
    @property
    def is_critical(self) -> bool:
        if self.interpretation:
            critical_codes = ["HH", "LL", "AA", "CRITICAL", "PANIC"]
            return self.interpretation.upper() in critical_codes
        return False

class BloodPressure(BaseModel):
    systolic: Optional[VitalSign] = None
    diastolic: Optional[VitalSign] = None
    
    @computed_field
    @property
    def mean_arterial_pressure(self) -> Optional[float]:
        if self.systolic and self.diastolic and self.systolic.value and self.diastolic.value:
            return calculate_mean_arterial_pressure(self.systolic.value, self.diastolic.value)
        return None
    
    @computed_field
    @property
    def pulse_pressure(self) -> Optional[float]:
        if self.systolic and self.diastolic and self.systolic.value and self.diastolic.value:
            return calculate_pulse_pressure(self.systolic.value, self.diastolic.value)
        return None
    
    @computed_field
    @property
    def is_hypertensive(self) -> bool:
        if self.systolic and self.systolic.value and self.systolic.value >= 140:
            return True
        if self.diastolic and self.diastolic.value and self.diastolic.value >= 90:
            return True
        return False
    
    @computed_field
    @property
    def is_hypotensive(self) -> bool:
        if self.systolic and self.systolic.value and self.systolic.value < 90:
            return True
        return False

class VitalSignsData(BaseModel):
    heart_rate: Optional[VitalSign] = None
    blood_pressure: Optional[BloodPressure] = None
    respiratory_rate: Optional[VitalSign] = None
    body_temperature: Optional[VitalSign] = None
    oxygen_saturation: Optional[VitalSign] = None
    glasgow_coma_score: Optional[VitalSign] = None
    
    @computed_field
    @property
    def has_fever(self) -> Optional[bool]:
        if self.body_temperature and self.body_temperature.value:
            unit = self.body_temperature.unit or "C"
            return is_fever(self.body_temperature.value, unit)
        return None
    
    @computed_field
    @property
    def is_tachycardic(self) -> bool:
        if self.heart_rate and self.heart_rate.value:
            return self.heart_rate.value > 100
        return False
    
    @computed_field
    @property
    def is_bradycardic(self) -> bool:
        if self.heart_rate and self.heart_rate.value:
            return self.heart_rate.value < 60
        return False
    
    @computed_field
    @property
    def is_tachypneic(self) -> bool:
        if self.respiratory_rate and self.respiratory_rate.value:
            return self.respiratory_rate.value > 20
        return False
    
    @computed_field
    @property
    def has_hypoxia(self) -> bool:
        if self.oxygen_saturation and self.oxygen_saturation.value:
            return self.oxygen_saturation.value < 95
        return False
    
    @computed_field
    @property
    def glasgow_coma_interpretation(self) -> Optional[str]:
        if self.glasgow_coma_score and self.glasgow_coma_score.value:
            score = self.glasgow_coma_score.value
            if score >= 13:
                return "Mild"
            elif score >= 9:
                return "Moderate"
            elif score >= 3:
                return "Severe"
        return None

class VitalSignsTimeSeries(BaseModel):
    heart_rate: List[VitalSign] = Field(default_factory=list)
    blood_pressure: List[BloodPressure] = Field(default_factory=list)
    respiratory_rate: List[VitalSign] = Field(default_factory=list)
    body_temperature: List[VitalSign] = Field(default_factory=list)
    oxygen_saturation: List[VitalSign] = Field(default_factory=list)
    glasgow_coma_score: List[VitalSign] = Field(default_factory=list)
    
    @computed_field
    @property
    def has_abnormal_values(self) -> bool:
        all_vitals = (
            self.heart_rate + self.respiratory_rate + 
            self.body_temperature + self.oxygen_saturation + 
            self.glasgow_coma_score
        )
        
        for bp in self.blood_pressure:
            if bp.systolic:
                all_vitals.append(bp.systolic)
            if bp.diastolic:
                all_vitals.append(bp.diastolic)
        
        return any(vital.is_abnormal for vital in all_vitals)
    
    @computed_field
    @property
    def critical_values_count(self) -> int:
        all_vitals = (
            self.heart_rate + self.respiratory_rate + 
            self.body_temperature + self.oxygen_saturation + 
            self.glasgow_coma_score
        )
        
        for bp in self.blood_pressure:
            if bp.systolic:
                all_vitals.append(bp.systolic)
            if bp.diastolic:
                all_vitals.append(bp.diastolic)
        
        return sum(1 for vital in all_vitals if vital.is_critical)

class VitalSignsResponse(BaseModel):
    patient_id: str
    vital_signs: VitalSignsTimeSeries
    total_entries: int = 0
    date_range: Optional[Dict[str, datetime]] = None
    
    @computed_field
    @property
    def sepsis_alert_score(self) -> int:
        """Calculate simple sepsis alert score based on vital signs"""
        score = 0
        latest_vitals = self._get_latest_vitals()
        
        if latest_vitals.has_fever:
            score += 1
        if latest_vitals.is_tachycardic:
            score += 1
        if latest_vitals.is_tachypneic:
            score += 1
        if latest_vitals.has_hypoxia:
            score += 1
        if latest_vitals.blood_pressure and latest_vitals.blood_pressure.is_hypotensive:
            score += 2
        if latest_vitals.glasgow_coma_score and latest_vitals.glasgow_coma_score.value and latest_vitals.glasgow_coma_score.value < 13:
            score += 1
        
        return score
    
    def _get_latest_vitals(self) -> VitalSignsData:
        """Get the most recent vital signs"""
        latest = VitalSignsData()
        
        if self.vital_signs.heart_rate:
            latest.heart_rate = max(self.vital_signs.heart_rate, key=lambda x: x.timestamp or datetime.min)
        if self.vital_signs.blood_pressure:
            latest.blood_pressure = max(self.vital_signs.blood_pressure, key=lambda x: (x.systolic.timestamp if x.systolic else datetime.min))
        if self.vital_signs.respiratory_rate:
            latest.respiratory_rate = max(self.vital_signs.respiratory_rate, key=lambda x: x.timestamp or datetime.min)
        if self.vital_signs.body_temperature:
            latest.body_temperature = max(self.vital_signs.body_temperature, key=lambda x: x.timestamp or datetime.min)
        if self.vital_signs.oxygen_saturation:
            latest.oxygen_saturation = max(self.vital_signs.oxygen_saturation, key=lambda x: x.timestamp or datetime.min)
        if self.vital_signs.glasgow_coma_score:
            latest.glasgow_coma_score = max(self.vital_signs.glasgow_coma_score, key=lambda x: x.timestamp or datetime.min)
        
        return latest

class VitalSignsLatestResponse(BaseModel):
    patient_id: str
    vital_signs: VitalSignsData
    last_updated: Optional[datetime] = None
    
    @computed_field
    @property
    def sepsis_risk_level(self) -> str:
        """Assess sepsis risk level based on vital signs"""
        risk_factors = 0
        
        if self.vital_signs.has_fever:
            risk_factors += 1
        if self.vital_signs.is_tachycardic:
            risk_factors += 1
        if self.vital_signs.is_tachypneic:
            risk_factors += 1
        if self.vital_signs.has_hypoxia:
            risk_factors += 1
        if self.vital_signs.blood_pressure and self.vital_signs.blood_pressure.is_hypotensive:
            risk_factors += 2
        
        if risk_factors >= 3:
            return "HIGH"
        elif risk_factors >= 2:
            return "MODERATE"
        elif risk_factors >= 1:
            return "LOW"
        else:
            return "MINIMAL"

class VitalSignsTrend(BaseModel):
    parameter: str
    trend: str  # "increasing", "decreasing", "stable"
    change_rate: Optional[float] = None
    time_period_hours: Optional[int] = None
    
class VitalSignsTrendResponse(BaseModel):
    patient_id: str
    trends: List[VitalSignsTrend] = Field(default_factory=list)
    analysis_period: Dict[str, datetime]
    
class VitalSignsAlert(BaseModel):
    parameter: str
    alert_type: str  # "critical", "abnormal", "trending"
    message: str
    severity: str  # "high", "medium", "low"
    timestamp: datetime
    
class VitalSignsAlertResponse(BaseModel):
    patient_id: str
    alerts: List[VitalSignsAlert] = Field(default_factory=list)
    alert_summary: str
    requires_immediate_attention: bool = False