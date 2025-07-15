from pydantic import BaseModel, Field, computed_field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from app.utils.date_utils import calculate_time_since_observation

class Period(BaseModel):
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    
    @computed_field
    @property
    def duration_hours(self) -> Optional[float]:
        if self.start and self.end:
            return (self.end - self.start).total_seconds() / 3600
        return None
    
    @computed_field
    @property
    def is_current(self) -> bool:
        if self.start and not self.end:
            return True
        if self.start and self.end:
            return self.start <= datetime.now() <= self.end
        return False

class Coding(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None

class CodeableConcept(BaseModel):
    coding: List[Coding] = Field(default_factory=list)
    text: Optional[str] = None
    
    @computed_field
    @property
    def primary_code(self) -> Optional[str]:
        if self.coding:
            return self.coding[0].code
        return None
    
    @computed_field
    @property
    def primary_display(self) -> Optional[str]:
        if self.text:
            return self.text
        if self.coding:
            return self.coding[0].display
        return None

class Location(BaseModel):
    location: Optional[str] = None
    status: Optional[str] = None
    period: Optional[Period] = None

class Encounter(BaseModel):
    id: str
    status: Optional[str] = None
    class_: Optional[Dict[str, Any]] = Field(None, alias="class")
    type: List[CodeableConcept] = Field(default_factory=list)
    period: Optional[Period] = None
    hospitalization: Optional[Dict[str, Any]] = None
    location: List[Location] = Field(default_factory=list)
    admission_source: Optional[str] = None
    discharge_disposition: Optional[str] = None
    
    class Config:
        populate_by_name = True
    
    @computed_field
    @property
    def is_inpatient(self) -> bool:
        if self.class_ and self.class_.get("code"):
            return self.class_["code"] in ["IMP", "ACUTE", "NONAC"]
        return False
    
    @computed_field
    @property
    def is_emergency(self) -> bool:
        if self.class_ and self.class_.get("code"):
            return self.class_["code"] == "EMER"
        return False
    
    @computed_field
    @property
    def is_icu(self) -> bool:
        for loc in self.location:
            if loc.location and "ICU" in loc.location.upper():
                return True
        return False
    
    @computed_field
    @property
    def current_location(self) -> Optional[str]:
        current_locations = [loc for loc in self.location if loc.period and loc.period.is_current]
        if current_locations:
            return current_locations[0].location
        return None
    
    @computed_field
    @property
    def length_of_stay_hours(self) -> Optional[float]:
        if self.period:
            return self.period.duration_hours
        return None

class EncounterResponse(BaseModel):
    patient_id: str
    current_encounter: Optional[Encounter] = None
    encounter_history: List[Encounter] = Field(default_factory=list)
    
    @computed_field
    @property
    def is_currently_admitted(self) -> bool:
        return self.current_encounter is not None and self.current_encounter.status == "in-progress"
    
    @computed_field
    @property
    def is_in_icu(self) -> bool:
        return self.current_encounter is not None and self.current_encounter.is_icu
    
    @computed_field
    @property
    def admission_type(self) -> Optional[str]:
        if self.current_encounter:
            if self.current_encounter.is_emergency:
                return "Emergency"
            elif self.current_encounter.is_inpatient:
                return "Inpatient"
            else:
                return "Outpatient"
        return None

class Condition(BaseModel):
    id: str
    clinical_status: Optional[str] = None
    verification_status: Optional[str] = None
    category: List[str] = Field(default_factory=list)
    severity: Optional[str] = None
    code: Optional[str] = None
    code_text: Optional[str] = None
    subject: Optional[str] = None
    onset_date_time: Optional[datetime] = None
    recorded_date: Optional[datetime] = None
    abatement_date_time: Optional[datetime] = None
    
    @computed_field
    @property
    def is_active(self) -> bool:
        return self.clinical_status in ["active", "recurrence", "relapse"]
    
    @computed_field
    @property
    def is_resolved(self) -> bool:
        return self.clinical_status in ["resolved", "remission"]
    
    @computed_field
    @property
    def is_infection_related(self) -> bool:
        if self.code_text:
            infection_keywords = ["infection", "sepsis", "pneumonia", "bacteremia", "cellulitis", "abscess"]
            return any(keyword in self.code_text.lower() for keyword in infection_keywords)
        return False
    
    @computed_field
    @property
    def time_since_onset(self) -> Optional[str]:
        if self.onset_date_time:
            return calculate_time_since_observation(self.onset_date_time)
        return None

class ConditionsResponse(BaseModel):
    patient_id: str
    active_conditions: List[Condition] = Field(default_factory=list)
    resolved_conditions: List[Condition] = Field(default_factory=list)
    total_conditions: int = 0
    
    @computed_field
    @property
    def infection_conditions(self) -> List[Condition]:
        return [cond for cond in self.active_conditions if cond.is_infection_related]
    
    @computed_field
    @property
    def has_active_infection(self) -> bool:
        return len(self.infection_conditions) > 0
    
    @computed_field
    @property
    def sepsis_related_conditions(self) -> List[Condition]:
        return [cond for cond in self.active_conditions 
                if cond.code_text and "sepsis" in cond.code_text.lower()]

class Dosage(BaseModel):
    text: Optional[str] = None
    timing: Optional[Dict[str, Any]] = None
    route: Optional[str] = None
    dose_and_rate: Optional[List[Dict[str, Any]]] = None

class Medication(BaseModel):
    id: str
    status: Optional[str] = None
    intent: Optional[str] = None
    medication_name: Optional[str] = None
    authored_on: Optional[datetime] = None
    dosage_instruction: List[Dosage] = Field(default_factory=list)
    is_antibiotic: bool = False
    is_vasopressor: bool = False
    
    @computed_field
    @property
    def is_active(self) -> bool:
        return self.status == "active"
    
    @computed_field
    @property
    def route_of_administration(self) -> Optional[str]:
        if self.dosage_instruction:
            return self.dosage_instruction[0].route
        return None
    
    @computed_field
    @property
    def medication_category(self) -> str:
        if self.is_antibiotic:
            return "Antibiotic"
        elif self.is_vasopressor:
            return "Vasopressor"
        else:
            return "Other"
    
    @computed_field
    @property
    def time_since_ordered(self) -> Optional[str]:
        if self.authored_on:
            return calculate_time_since_observation(self.authored_on)
        return None

class MedicationsResponse(BaseModel):
    patient_id: str
    active_medications: List[Medication] = Field(default_factory=list)
    antibiotics: List[Medication] = Field(default_factory=list)
    vasopressors: List[Medication] = Field(default_factory=list)
    total_medications: int = 0
    
    @computed_field
    @property
    def is_on_antibiotics(self) -> bool:
        return len(self.antibiotics) > 0
    
    @computed_field
    @property
    def is_on_vasopressors(self) -> bool:
        return len(self.vasopressors) > 0
    
    @computed_field
    @property
    def antibiotic_names(self) -> List[str]:
        return [med.medication_name for med in self.antibiotics if med.medication_name]
    
    @computed_field
    @property
    def vasopressor_names(self) -> List[str]:
        return [med.medication_name for med in self.vasopressors if med.medication_name]
    
    @computed_field
    @property
    def sepsis_treatment_score(self) -> int:
        """Score based on sepsis-relevant medications"""
        score = 0
        if self.is_on_antibiotics:
            score += 2
        if self.is_on_vasopressors:
            score += 3
        return score

class FluidObservation(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    category: Optional[str] = None
    
    @computed_field
    @property
    def is_recent(self) -> bool:
        if self.timestamp:
            return (datetime.now() - self.timestamp).total_seconds() < 3600  # Last hour
        return False

class FluidBalanceResponse(BaseModel):
    patient_id: str
    fluid_intake: List[FluidObservation] = Field(default_factory=list)
    urine_output: List[FluidObservation] = Field(default_factory=list)
    fluid_balance: Optional[float] = None
    date_range: Optional[Dict[str, datetime]] = None
    
    @computed_field
    @property
    def total_intake_24h(self) -> Optional[float]:
        if not self.fluid_intake:
            return None
        
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_intake = [obs for obs in self.fluid_intake 
                        if obs.timestamp and obs.timestamp >= cutoff_time]
        
        if recent_intake:
            return sum(obs.value for obs in recent_intake if obs.value)
        return None
    
    @computed_field
    @property
    def total_output_24h(self) -> Optional[float]:
        if not self.urine_output:
            return None
        
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_output = [obs for obs in self.urine_output 
                        if obs.timestamp and obs.timestamp >= cutoff_time]
        
        if recent_output:
            return sum(obs.value for obs in recent_output if obs.value)
        return None
    
    @computed_field
    @property
    def net_balance_24h(self) -> Optional[float]:
        intake = self.total_intake_24h
        output = self.total_output_24h
        
        if intake is not None and output is not None:
            return intake - output
        return None
    
    @computed_field
    @property
    def is_oliguric(self) -> bool:
        """Check if patient is oliguric (<0.5 mL/kg/hr)"""
        output = self.total_output_24h
        if output is not None:
            # Assuming 70kg patient for calculation
            return output < (0.5 * 70 * 24)  # <840 mL/24h
        return False
    
    @computed_field
    @property
    def fluid_status(self) -> str:
        """Assess fluid status"""
        balance = self.net_balance_24h
        
        if balance is None:
            return "Unknown"
        elif balance > 2000:
            return "Positive - Overloaded"
        elif balance > 500:
            return "Positive - Adequate"
        elif balance > -500:
            return "Balanced"
        elif balance > -1000:
            return "Negative - Mild"
        else:
            return "Negative - Severe"

class ClinicalSummary(BaseModel):
    """Summary of clinical context for sepsis assessment"""
    patient_id: str
    is_admitted: bool = False
    is_in_icu: bool = False
    length_of_stay_hours: Optional[float] = None
    has_active_infection: bool = False
    infection_conditions: List[str] = Field(default_factory=list)
    is_on_antibiotics: bool = False
    is_on_vasopressors: bool = False
    antibiotic_names: List[str] = Field(default_factory=list)
    vasopressor_names: List[str] = Field(default_factory=list)
    fluid_status: str = "Unknown"
    is_oliguric: bool = False
    
    @computed_field
    @property
    def sepsis_risk_factors(self) -> List[str]:
        """List of sepsis risk factors present"""
        factors = []
        
        if self.has_active_infection:
            factors.append("Active infection")
        if self.is_in_icu:
            factors.append("ICU admission")
        if self.is_on_antibiotics:
            factors.append("On antibiotics")
        if self.is_on_vasopressors:
            factors.append("On vasopressors")
        if self.is_oliguric:
            factors.append("Oliguria")
        if self.length_of_stay_hours and self.length_of_stay_hours > 72:
            factors.append("Extended stay")
        
        return factors
    
    @computed_field
    @property
    def sepsis_likelihood(self) -> str:
        """Assess sepsis likelihood based on clinical factors"""
        risk_count = len(self.sepsis_risk_factors)
        
        if risk_count >= 4:
            return "HIGH"
        elif risk_count >= 2:
            return "MODERATE"
        elif risk_count >= 1:
            return "LOW"
        else:
            return "MINIMAL"

class ClinicalSummaryResponse(BaseModel):
    patient_id: str
    summary: ClinicalSummary
    last_updated: datetime = Field(default_factory=datetime.now)