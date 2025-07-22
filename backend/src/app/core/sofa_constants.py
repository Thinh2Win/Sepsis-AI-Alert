"""
SOFA Scoring Constants and Configuration

Centralizes all default values, thresholds, and constants used in SOFA scoring
to eliminate duplication and improve maintainability.
"""

from typing import Dict, List
from app.core.loinc_codes import LOINCCodes


class SofaDefaults:
    """Default values for missing SOFA parameters"""
    
    # Normal values used when parameters are missing
    PAO2_FIO2_RATIO = 400.0      # Normal PaO2/FiO2 ratio
    PLATELETS = 150.0            # Normal platelet count (10^3/μL)
    BILIRUBIN = 1.0              # Normal bilirubin (mg/dL)
    MAP = 70.0                   # Normal mean arterial pressure (mmHg)
    GCS = 15.0                   # Normal Glasgow Coma Score
    CREATININE = 1.0             # Normal creatinine (mg/dL)
    URINE_OUTPUT = 1000.0        # Normal urine output (mL/24h)
    
    # Additional vital signs for NEWS2 reuse optimization
    HEART_RATE = 75.0            # Normal heart rate (bpm)
    TEMPERATURE = 37.0           # Normal temperature (°C)
    RESPIRATORY_RATE = 16.0      # Normal respiratory rate (breaths/min)
    OXYGEN_SATURATION = 98.0     # Normal oxygen saturation (%)
    
    # Assumed values for calculations
    ROOM_AIR_FIO2 = 0.21         # Room air oxygen fraction


class SofaThresholds:
    """SOFA scoring thresholds for each organ system"""
    
    # Respiratory system (PaO2/FiO2 ratio)
    RESPIRATORY = {
        "normal": 400,           # Score 0: ≥400
        "mild": 300,             # Score 1: 300-399
        "moderate": 200,         # Score 2: 200-299
        "severe": 100,           # Score 3: 100-199 with ventilation
        "critical": 0            # Score 4: <100 with ventilation
    }
    
    # Coagulation system (platelet count in 10^3/μL)
    COAGULATION = {
        "normal": 150,           # Score 0: ≥150
        "mild": 100,             # Score 1: 100-149
        "moderate": 50,          # Score 2: 50-99
        "severe": 20,            # Score 3: 20-49
        "critical": 0            # Score 4: <20
    }
    
    # Liver system (bilirubin in mg/dL)
    LIVER = {
        "normal": 1.2,           # Score 0: <1.2
        "mild": 2.0,             # Score 1: 1.2-1.9
        "moderate": 6.0,         # Score 2: 2.0-5.9
        "severe": 12.0,          # Score 3: 6.0-11.9
        "critical": float('inf') # Score 4: ≥12.0
    }
    
    # Cardiovascular system (MAP in mmHg)
    CARDIOVASCULAR = {
        "normal_map": 70,        # Score 0: MAP ≥70
        "hypotension": 70        # Score 1: MAP <70
    }
    
    # Vasopressor doses (mcg/kg/min)
    VASOPRESSOR = {
        "low_dopamine": 5,       # Score 2: dopamine ≤5
        "med_dopamine": 15,      # Score 3: dopamine 5-15
        "high_dopamine": 15,     # Score 4: dopamine >15
        "epi_norepi": 0.1       # Score 4: epinephrine/norepinephrine >0.1
    }
    
    # Central nervous system (Glasgow Coma Score)
    CNS = {
        "normal": 15,            # Score 0: GCS 15
        "mild": 13,              # Score 1: GCS 13-14
        "moderate": 10,          # Score 2: GCS 10-12
        "severe": 6,             # Score 3: GCS 6-9
        "critical": 0            # Score 4: GCS <6
    }
    
    # Renal system (creatinine in mg/dL, urine output in mL/day)
    RENAL = {
        "creatinine": {
            "normal": 1.2,       # Score 0: <1.2
            "mild": 2.0,         # Score 1: 1.2-1.9
            "moderate": 3.5,     # Score 2: 2.0-3.4
            "severe": 5.0,       # Score 3: 3.5-4.9
            "critical": float('inf') # Score 4: ≥5.0
        },
        "urine_output": {
            "normal": 500,       # Score 0: ≥500 mL/day
            "oliguria": 200      # Score 3: <500 mL/day, Score 4: <200 mL/day
        }
    }


class SofaMortalityRisk:
    """SOFA score to mortality risk mapping"""
    
    RISK_RANGES = [
        {"min": 0, "max": 6, "risk": "Low (<10%)", "percentage": 5},
        {"min": 7, "max": 9, "risk": "Moderate (15-20%)", "percentage": 17},
        {"min": 10, "max": 12, "risk": "High (40-50%)", "percentage": 45},
        {"min": 13, "max": 15, "risk": "Very High (50-60%)", "percentage": 55},
        {"min": 16, "max": 24, "risk": "Extremely High (>80%)", "percentage": 85}
    ]
    
    @classmethod
    def get_mortality_risk(cls, sofa_score: int) -> str:
        """Get mortality risk description for SOFA score"""
        for risk_range in cls.RISK_RANGES:
            if risk_range["min"] <= sofa_score <= risk_range["max"]:
                return risk_range["risk"]
        return "Unknown"
    
    @classmethod
    def get_mortality_percentage(cls, sofa_score: int) -> int:
        """Get mortality percentage for SOFA score"""
        for risk_range in cls.RISK_RANGES:
            if risk_range["min"] <= sofa_score <= risk_range["max"]:
                return risk_range["percentage"]
        return 0


class SofaSeverityClassification:
    """SOFA score severity classification"""
    
    CLASSIFICATIONS = [
        {"min": 0, "max": 2, "severity": "No organ dysfunction"},
        {"min": 3, "max": 6, "severity": "Mild organ dysfunction"},
        {"min": 7, "max": 12, "severity": "Moderate organ dysfunction"},
        {"min": 13, "max": 24, "severity": "Severe organ dysfunction"}
    ]
    
    @classmethod
    def get_severity(cls, sofa_score: int) -> str:
        """Get severity classification for SOFA score"""
        for classification in cls.CLASSIFICATIONS:
            if classification["min"] <= sofa_score <= classification["max"]:
                return classification["severity"]
        return "Unknown"


class SofaParameterConfigs:
    """Configuration for FHIR parameter collection"""
    
    RESPIRATORY = {
        "codes": ["50984-4"],  # PaO2/FiO2 ratio
        "count": 1,
        "parameter_mapping": {
            "50984-4": "pao2_fio2_ratio"
        },
        "extra_data": {
            "mechanical_ventilation": False,
            "pao2": None,
            "fio2": None
        },
        "system_name": "respiratory"
    }
    
    COAGULATION = {
        "codes": [LOINCCodes.CBC["platelet_count"]],  # 777-3
        "count": 1,
        "parameter_mapping": {
            LOINCCodes.CBC["platelet_count"]: "platelets"
        },
        "system_name": "coagulation"
    }
    
    LIVER = {
        "codes": [LOINCCodes.LIVER["bilirubin_total"]],  # 1975-2
        "count": 1,
        "parameter_mapping": {
            LOINCCodes.LIVER["bilirubin_total"]: "bilirubin"
        },
        "system_name": "liver"
    }
    
    CARDIOVASCULAR = {
        "codes": [LOINCCodes.VITAL_SIGNS["systolic_bp"], LOINCCodes.VITAL_SIGNS["diastolic_bp"]],
        "count": 2,
        "parameter_mapping": {
            LOINCCodes.VITAL_SIGNS["systolic_bp"]: "systolic_bp",
            LOINCCodes.VITAL_SIGNS["diastolic_bp"]: "diastolic_bp"
        },
        "extra_data": {
            "map_value": None
        },
        "system_name": "cardiovascular"
    }
    
    CNS = {
        "codes": [LOINCCodes.VITAL_SIGNS["glasgow_coma_score"]],  # 9269-2
        "count": 1,
        "parameter_mapping": {
            LOINCCodes.VITAL_SIGNS["glasgow_coma_score"]: "gcs"
        },
        "system_name": "CNS"
    }
    
    RENAL = {
        "codes": [
            LOINCCodes.METABOLIC["creatinine"],  # 2160-0
            LOINCCodes.FLUID_BALANCE["urine_output_24hr"]  # 9188-4
        ],
        "count": 2,
        "parameter_mapping": {
            LOINCCodes.METABOLIC["creatinine"]: "creatinine",
            LOINCCodes.FLUID_BALANCE["urine_output_24hr"]: "urine_output_24h"
        },
        "system_name": "renal"
    }
    
    # Additional vital signs for NEWS2 reuse optimization
    VITAL_SIGNS = {
        "codes": [
            LOINCCodes.VITAL_SIGNS["heart_rate"],  # 8867-4
            LOINCCodes.VITAL_SIGNS["body_temperature"],  # 8310-5
            LOINCCodes.VITAL_SIGNS["respiratory_rate"],  # 9279-1
            LOINCCodes.VITAL_SIGNS["oxygen_saturation"]  # 2708-6
        ],
        "count": 4,
        "parameter_mapping": {
            LOINCCodes.VITAL_SIGNS["heart_rate"]: "heart_rate",
            LOINCCodes.VITAL_SIGNS["body_temperature"]: "temperature",
            LOINCCodes.VITAL_SIGNS["respiratory_rate"]: "respiratory_rate",
            LOINCCodes.VITAL_SIGNS["oxygen_saturation"]: "oxygen_saturation"
        },
        "system_name": "vital_signs"
    }


class SepsisRiskThresholds:
    """Thresholds for overall sepsis risk assessment"""
    
    CRITICAL_THRESHOLD = 15      # SOFA ≥15 = Critical risk
    HIGH_THRESHOLD = 10          # SOFA ≥10 = High risk
    MODERATE_THRESHOLD = 6       # SOFA ≥6 = Moderate risk
    LOW_THRESHOLD = 3            # SOFA ≥3 = Low risk
    
    SEVERE_DYSFUNCTION_THRESHOLD = 3  # Individual organ score ≥3
    MULTIPLE_ORGAN_THRESHOLD = 3      # Number of organs with dysfunction


class SofaValidationLimits:
    """Validation limits for SOFA parameters"""
    
    MAX_PATIENTS_BATCH = 50      # Maximum patients per batch request
    MAX_HOURS_LOOKBACK = 24      # Maximum hours to look back for parameters
    MIN_SOFA_SCORE = 0           # Minimum possible SOFA score
    MAX_SOFA_SCORE = 24          # Maximum possible SOFA score
    MAX_ORGAN_SCORE = 4          # Maximum score per organ system
    
    # Reasonable ranges for parameter validation
    PARAMETER_RANGES = {
        "pao2_fio2_ratio": {"min": 50, "max": 600},
        "platelets": {"min": 1, "max": 1000},
        "bilirubin": {"min": 0.1, "max": 50},
        "map": {"min": 30, "max": 150},
        "gcs": {"min": 3, "max": 15},
        "creatinine": {"min": 0.1, "max": 20},
        "urine_output": {"min": 0, "max": 5000}
    }


# Legacy support - maintain backward compatibility
SOFA_DEFAULTS = {
    "pao2_fio2_ratio": SofaDefaults.PAO2_FIO2_RATIO,
    "platelets": SofaDefaults.PLATELETS,
    "bilirubin": SofaDefaults.BILIRUBIN,
    "map": SofaDefaults.MAP,
    "gcs": SofaDefaults.GCS,
    "creatinine": SofaDefaults.CREATININE,
    "urine_output": SofaDefaults.URINE_OUTPUT
}