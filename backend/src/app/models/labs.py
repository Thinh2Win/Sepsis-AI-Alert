from pydantic import BaseModel, Field, computed_field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

class LabValue(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    status: Optional[str] = None
    interpretation: Optional[Union[str, List[str]]] = None
    reference_range: Optional[str] = Field(None, alias="referenceRange")
    loinc_code: Optional[str] = None
    display_name: Optional[str] = None
    
    class Config:
        populate_by_name = True
    
    def _get_interpretation_codes(self) -> List[str]:
        """Helper to normalize interpretation to list of codes."""
        if not self.interpretation:
            return []
        if isinstance(self.interpretation, str):
            return [self.interpretation.upper()]
        return [code.upper() for code in self.interpretation]
    
    @computed_field
    @property
    def is_abnormal(self) -> bool:
        codes = self._get_interpretation_codes()
        abnormal_codes = ["H", "HH", "L", "LL", "A", "AA", "CRITICAL", "PANIC"]
        return any(code in abnormal_codes for code in codes)
    
    @computed_field
    @property
    def is_critical(self) -> bool:
        codes = self._get_interpretation_codes()
        critical_codes = ["HH", "LL", "AA", "CRITICAL", "PANIC"]
        return any(code in critical_codes for code in codes)
    
    @computed_field
    @property
    def is_high(self) -> bool:
        codes = self._get_interpretation_codes()
        high_codes = ["H", "HH", "AA"]
        return any(code in high_codes for code in codes)
    
    @computed_field
    @property
    def is_low(self) -> bool:
        codes = self._get_interpretation_codes()
        low_codes = ["L", "LL", "AA"]
        return any(code in low_codes for code in codes)

class CBCResults(BaseModel):
    white_blood_cell_count: Optional[LabValue] = None
    red_blood_cell_count: Optional[LabValue] = None
    hemoglobin: Optional[LabValue] = None
    hematocrit: Optional[LabValue] = None
    platelet_count: Optional[LabValue] = None
    mean_corpuscular_volume: Optional[LabValue] = None
    mean_corpuscular_hemoglobin: Optional[LabValue] = None
    mean_corpuscular_hemoglobin_concentration: Optional[LabValue] = None
    
    @computed_field
    @property
    def indicates_infection(self) -> bool:
        """Check if CBC indicates possible infection"""
        if self.white_blood_cell_count and self.white_blood_cell_count.value:
            wbc = self.white_blood_cell_count.value
            # Normal WBC: 4.0-11.0 K/uL
            return wbc > 12.0 or wbc < 4.0
        return False
    
    @computed_field
    @property
    def indicates_severe_infection(self) -> bool:
        """Check if CBC indicates severe infection"""
        if self.white_blood_cell_count and self.white_blood_cell_count.value:
            wbc = self.white_blood_cell_count.value
            # Severe infection indicators
            return wbc > 20.0 or wbc < 1.0
        return False
    
    @computed_field
    @property
    def indicates_bleeding_risk(self) -> bool:
        """Check if platelet count indicates bleeding risk"""
        if self.platelet_count and self.platelet_count.value:
            plt = self.platelet_count.value
            # Normal platelets: 150-450 K/uL
            return plt < 100.0
        return False

class MetabolicPanel(BaseModel):
    glucose: Optional[LabValue] = None
    creatinine: Optional[LabValue] = None
    blood_urea_nitrogen: Optional[LabValue] = None
    sodium: Optional[LabValue] = None
    potassium: Optional[LabValue] = None
    chloride: Optional[LabValue] = None
    carbon_dioxide: Optional[LabValue] = None
    anion_gap: Optional[LabValue] = None
    
    @computed_field
    @property
    def indicates_kidney_dysfunction(self) -> bool:
        """Check if metabolic panel indicates kidney dysfunction"""
        if self.creatinine and self.creatinine.value:
            creat = self.creatinine.value
            # Normal creatinine: 0.6-1.2 mg/dL
            return creat > 1.5
        return False
    
    @computed_field
    @property
    def indicates_severe_kidney_dysfunction(self) -> bool:
        """Check if metabolic panel indicates severe kidney dysfunction"""
        if self.creatinine and self.creatinine.value:
            creat = self.creatinine.value
            return creat > 2.0
        return False
    
    @computed_field
    @property
    def indicates_electrolyte_imbalance(self) -> bool:
        """Check for electrolyte imbalances"""
        imbalances = []
        
        if self.sodium and self.sodium.value:
            # Normal sodium: 135-145 mEq/L
            if self.sodium.value < 135 or self.sodium.value > 145:
                imbalances.append("sodium")
        
        if self.potassium and self.potassium.value:
            # Normal potassium: 3.5-5.0 mEq/L
            if self.potassium.value < 3.5 or self.potassium.value > 5.0:
                imbalances.append("potassium")
        
        return len(imbalances) > 0

class LiverFunction(BaseModel):
    bilirubin_total: Optional[LabValue] = None
    bilirubin_direct: Optional[LabValue] = None
    albumin: Optional[LabValue] = None
    total_protein: Optional[LabValue] = None
    alkaline_phosphatase: Optional[LabValue] = None
    alanine_aminotransferase: Optional[LabValue] = None
    aspartate_aminotransferase: Optional[LabValue] = None
    lactate_dehydrogenase: Optional[LabValue] = None
    
    @computed_field
    @property
    def indicates_liver_dysfunction(self) -> bool:
        """Check if liver function tests indicate dysfunction"""
        if self.bilirubin_total and self.bilirubin_total.value:
            # Normal total bilirubin: 0.2-1.2 mg/dL
            if self.bilirubin_total.value > 2.0:
                return True
        
        if self.alanine_aminotransferase and self.alanine_aminotransferase.value:
            # Normal ALT: 7-56 U/L
            if self.alanine_aminotransferase.value > 100:
                return True
        
        if self.aspartate_aminotransferase and self.aspartate_aminotransferase.value:
            # Normal AST: 10-40 U/L
            if self.aspartate_aminotransferase.value > 100:
                return True
        
        return False
    
    @computed_field
    @property
    def indicates_severe_liver_dysfunction(self) -> bool:
        """Check if liver function tests indicate severe dysfunction"""
        if self.bilirubin_total and self.bilirubin_total.value:
            if self.bilirubin_total.value > 5.0:
                return True
        
        if self.alanine_aminotransferase and self.alanine_aminotransferase.value:
            if self.alanine_aminotransferase.value > 300:
                return True
        
        return False

class InflammatoryMarkers(BaseModel):
    c_reactive_protein: Optional[LabValue] = None
    procalcitonin: Optional[LabValue] = None
    erythrocyte_sedimentation_rate: Optional[LabValue] = None
    interleukin_6: Optional[LabValue] = None
    
    @computed_field
    @property
    def indicates_inflammation(self) -> bool:
        """Check if inflammatory markers indicate inflammation"""
        if self.c_reactive_protein and self.c_reactive_protein.value:
            # Normal CRP: <3.0 mg/L
            if self.c_reactive_protein.value > 10.0:
                return True
        
        if self.procalcitonin and self.procalcitonin.value:
            # Normal procalcitonin: <0.25 ng/mL
            if self.procalcitonin.value > 0.5:
                return True
        
        return False
    
    @computed_field
    @property
    def indicates_severe_inflammation(self) -> bool:
        """Check if inflammatory markers indicate severe inflammation"""
        if self.c_reactive_protein and self.c_reactive_protein.value:
            if self.c_reactive_protein.value > 50.0:
                return True
        
        if self.procalcitonin and self.procalcitonin.value:
            if self.procalcitonin.value > 2.0:
                return True
        
        return False
    
    @computed_field
    @property
    def sepsis_likelihood(self) -> str:
        """Assess sepsis likelihood based on inflammatory markers"""
        if self.procalcitonin and self.procalcitonin.value:
            pct = self.procalcitonin.value
            if pct >= 2.0:
                return "HIGH"
            elif pct >= 0.5:
                return "MODERATE"
            elif pct >= 0.25:
                return "LOW"
        
        if self.c_reactive_protein and self.c_reactive_protein.value:
            crp = self.c_reactive_protein.value
            if crp >= 50.0:
                return "HIGH"
            elif crp >= 10.0:
                return "MODERATE"
        
        return "MINIMAL"

class BloodGas(BaseModel):
    ph: Optional[LabValue] = None
    pco2: Optional[LabValue] = None
    po2: Optional[LabValue] = None
    lactate: Optional[LabValue] = None
    base_excess: Optional[LabValue] = None
    bicarbonate: Optional[LabValue] = None
    pao2_fio2_ratio: Optional[LabValue] = None
    
    @computed_field
    @property
    def indicates_acidosis(self) -> bool:
        """Check if blood gas indicates acidosis"""
        if self.ph and self.ph.value:
            return self.ph.value < 7.35
        return False
    
    @computed_field
    @property
    def indicates_severe_acidosis(self) -> bool:
        """Check if blood gas indicates severe acidosis"""
        if self.ph and self.ph.value:
            return self.ph.value < 7.25
        return False
    
    @computed_field
    @property
    def indicates_hyperlactatemia(self) -> bool:
        """Check if lactate indicates hyperlactatemia"""
        if self.lactate and self.lactate.value:
            # Normal lactate: 0.5-2.2 mmol/L
            return self.lactate.value > 2.5
        return False
    
    @computed_field
    @property
    def indicates_severe_hyperlactatemia(self) -> bool:
        """Check if lactate indicates severe hyperlactatemia"""
        if self.lactate and self.lactate.value:
            return self.lactate.value > 4.0
        return False
    
    @computed_field
    @property
    def indicates_respiratory_failure(self) -> bool:
        """Check if PaO2/FiO2 ratio indicates respiratory failure"""
        if self.pao2_fio2_ratio and self.pao2_fio2_ratio.value:
            # Normal PaO2/FiO2: >300
            return self.pao2_fio2_ratio.value < 300
        return False

class Coagulation(BaseModel):
    prothrombin_time: Optional[LabValue] = None
    inr: Optional[LabValue] = None
    partial_thromboplastin_time: Optional[LabValue] = None
    fibrinogen: Optional[LabValue] = None
    d_dimer: Optional[LabValue] = None
    
    @computed_field
    @property
    def indicates_coagulopathy(self) -> bool:
        """Check if coagulation tests indicate coagulopathy"""
        if self.inr and self.inr.value:
            # Normal INR: 0.8-1.2
            if self.inr.value > 1.5:
                return True
        
        if self.partial_thromboplastin_time and self.partial_thromboplastin_time.value:
            # Normal PTT: 25-35 seconds
            if self.partial_thromboplastin_time.value > 45:
                return True
        
        return False
    
    @computed_field
    @property
    def indicates_severe_coagulopathy(self) -> bool:
        """Check if coagulation tests indicate severe coagulopathy"""
        if self.inr and self.inr.value:
            if self.inr.value > 2.0:
                return True
        
        return False

class CardiacMarkers(BaseModel):
    troponin_i: Optional[LabValue] = None
    troponin_t: Optional[LabValue] = None
    brain_natriuretic_peptide: Optional[LabValue] = None
    nt_pro_bnp: Optional[LabValue] = None
    
    @computed_field
    @property
    def indicates_cardiac_injury(self) -> bool:
        """Check if cardiac markers indicate injury"""
        if self.troponin_i and self.troponin_i.value:
            # Normal troponin I: <0.04 ng/mL
            if self.troponin_i.value > 0.04:
                return True
        
        if self.troponin_t and self.troponin_t.value:
            # Normal troponin T: <0.01 ng/mL
            if self.troponin_t.value > 0.01:
                return True
        
        return False

class LabResultsData(BaseModel):
    cbc: CBCResults = Field(default_factory=CBCResults)
    metabolic_panel: MetabolicPanel = Field(default_factory=MetabolicPanel)
    liver_function: LiverFunction = Field(default_factory=LiverFunction)
    inflammatory_markers: InflammatoryMarkers = Field(default_factory=InflammatoryMarkers)
    blood_gas: BloodGas = Field(default_factory=BloodGas)
    coagulation: Coagulation = Field(default_factory=Coagulation)
    cardiac_markers: CardiacMarkers = Field(default_factory=CardiacMarkers)
    
    @computed_field
    @property
    def sepsis_score(self) -> int:
        """Calculate sepsis score based on lab values"""
        score = 0
        
        if self.cbc.indicates_severe_infection:
            score += 2
        elif self.cbc.indicates_infection:
            score += 1
        
        if self.inflammatory_markers.indicates_severe_inflammation:
            score += 2
        elif self.inflammatory_markers.indicates_inflammation:
            score += 1
        
        if self.blood_gas.indicates_severe_hyperlactatemia:
            score += 2
        elif self.blood_gas.indicates_hyperlactatemia:
            score += 1
        
        if self.metabolic_panel.indicates_severe_kidney_dysfunction:
            score += 2
        elif self.metabolic_panel.indicates_kidney_dysfunction:
            score += 1
        
        if self.liver_function.indicates_severe_liver_dysfunction:
            score += 2
        elif self.liver_function.indicates_liver_dysfunction:
            score += 1
        
        if self.coagulation.indicates_severe_coagulopathy:
            score += 2
        elif self.coagulation.indicates_coagulopathy:
            score += 1
        
        return score
    
    @computed_field
    @property
    def organ_dysfunction_count(self) -> int:
        """Count number of organ systems with dysfunction"""
        count = 0
        
        if self.metabolic_panel.indicates_kidney_dysfunction:
            count += 1
        if self.liver_function.indicates_liver_dysfunction:
            count += 1
        if self.blood_gas.indicates_respiratory_failure:
            count += 1
        if self.coagulation.indicates_coagulopathy:
            count += 1
        if self.cardiac_markers.indicates_cardiac_injury:
            count += 1
        
        return count

class LabResultsResponse(BaseModel):
    patient_id: str
    lab_results: LabResultsData
    total_entries: int = 0
    date_range: Optional[Dict[str, datetime]] = None
    
    @computed_field
    @property
    def sepsis_risk_assessment(self) -> str:
        """Overall sepsis risk assessment"""
        score = self.lab_results.sepsis_score
        
        if score >= 6:
            return "CRITICAL"
        elif score >= 4:
            return "HIGH"
        elif score >= 2:
            return "MODERATE"
        elif score >= 1:
            return "LOW"
        else:
            return "MINIMAL"

class CriticalLabsResponse(BaseModel):
    patient_id: str
    critical_values: List[LabValue] = Field(default_factory=list)
    abnormal_values: List[LabValue] = Field(default_factory=list)
    last_updated: Optional[datetime] = None
    
    @computed_field
    @property
    def critical_count(self) -> int:
        return len(self.critical_values)
    
    @computed_field
    @property
    def abnormal_count(self) -> int:
        return len(self.abnormal_values)
    
    @computed_field
    @property
    def requires_immediate_attention(self) -> bool:
        return self.critical_count > 0

class LabTrend(BaseModel):
    parameter: str
    trend: str  # "improving", "worsening", "stable"
    change_percentage: Optional[float] = None
    time_period_hours: Optional[int] = None
    
class LabTrendsResponse(BaseModel):
    patient_id: str
    trends: List[LabTrend] = Field(default_factory=list)
    analysis_period: Dict[str, datetime]
    
class LabAlert(BaseModel):
    parameter: str
    alert_type: str  # "critical", "abnormal", "trending"
    message: str
    severity: str  # "critical", "high", "medium", "low"
    timestamp: datetime
    
class LabAlertsResponse(BaseModel):
    patient_id: str
    alerts: List[LabAlert] = Field(default_factory=list)
    alert_summary: str
    requires_immediate_attention: bool = False