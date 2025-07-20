"""
qSOFA Scoring Constants and Configuration

Centralizes all default values, thresholds, and constants used in qSOFA scoring
to eliminate duplication and improve maintainability.
"""

from typing import Dict, List
from app.core.loinc_codes import LOINCCodes


class QsofaDefaults:
    """Default values for missing qSOFA parameters"""
    
    # Normal values used when parameters are missing
    RESPIRATORY_RATE = 16.0      # Normal respiratory rate (breaths/min)
    SYSTOLIC_BP = 120.0          # Normal systolic blood pressure (mmHg)
    GCS = 15.0                   # Normal Glasgow Coma Score


class QsofaThresholds:
    """qSOFA scoring thresholds"""
    
    # qSOFA criteria thresholds
    RESPIRATORY_RATE_THRESHOLD = 22    # ≥22 breaths/min = 1 point
    SYSTOLIC_BP_THRESHOLD = 100        # ≤100 mmHg = 1 point
    GCS_THRESHOLD = 15                 # <15 (altered mental status) = 1 point
    
    # Risk stratification
    HIGH_RISK_THRESHOLD = 2            # qSOFA ≥2 = high risk


class QsofaParameterConfigs:
    """Configuration for FHIR parameter collection"""
    
    RESPIRATORY = {
        "codes": [LOINCCodes.VITAL_SIGNS["respiratory_rate"]],  # 9279-1
        "count": 1,
        "parameter_mapping": {
            LOINCCodes.VITAL_SIGNS["respiratory_rate"]: "respiratory_rate"
        },
        "system_name": "respiratory"
    }
    
    CARDIOVASCULAR = {
        "codes": [LOINCCodes.VITAL_SIGNS["systolic_bp"]],  # 8480-6
        "count": 1,
        "parameter_mapping": {
            LOINCCodes.VITAL_SIGNS["systolic_bp"]: "systolic_bp"
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


class QsofaRiskLevels:
    """qSOFA risk level definitions"""
    
    RISK_CATEGORIES = [
        {
            "min_score": 0,
            "max_score": 0, 
            "level": "LOW",
            "description": "Low risk for poor outcome",
            "mortality_risk": "Low",
            "action_required": False
        },
        {
            "min_score": 1,
            "max_score": 1,
            "level": "MODERATE", 
            "description": "Moderate risk - monitor closely",
            "mortality_risk": "Moderate",
            "action_required": False
        },
        {
            "min_score": 2,
            "max_score": 3,
            "level": "HIGH",
            "description": "High risk for poor outcome - consider sepsis evaluation",
            "mortality_risk": "High", 
            "action_required": True
        }
    ]
    
    @classmethod
    def get_risk_level(cls, qsofa_score: int) -> str:
        """Get risk level for qSOFA score"""
        for category in cls.RISK_CATEGORIES:
            if category["min_score"] <= qsofa_score <= category["max_score"]:
                return category["level"]
        return "UNKNOWN"
    
    @classmethod
    def get_risk_description(cls, qsofa_score: int) -> str:
        """Get risk description for qSOFA score"""
        for category in cls.RISK_CATEGORIES:
            if category["min_score"] <= qsofa_score <= category["max_score"]:
                return category["description"]
        return "Unknown risk level"
    
    @classmethod
    def requires_action(cls, qsofa_score: int) -> bool:
        """Check if qSOFA score requires urgent action"""
        for category in cls.RISK_CATEGORIES:
            if category["min_score"] <= qsofa_score <= category["max_score"]:
                return category["action_required"]
        return False


class QsofaClinicalKeywords:
    """Keywords for identifying altered mental status in clinical notes"""
    
    CONFUSION_KEYWORDS = [
        "confused", "confusion", "disoriented", "disorientation",
        "altered", "altered mental status", "altered consciousness",
        "delirious", "delirium", "obtunded", "lethargic", "lethargy",
        "stuporous", "stupor", "encephalopathy", "encephalopathic"
    ]
    
    AVPU_ALTERED = ["verbal", "pain", "unresponsive"]  # AVPU scale - non-alert states
    
    @classmethod
    def check_clinical_notes(cls, notes_text: str) -> bool:
        """Check if clinical notes contain evidence of altered mental status"""
        if not notes_text:
            return False
        
        notes_lower = notes_text.lower()
        return any(keyword in notes_lower for keyword in cls.CONFUSION_KEYWORDS)


class QsofaValidationLimits:
    """Validation limits for qSOFA parameters"""
    
    MIN_QSOFA_SCORE = 0              # Minimum possible qSOFA score
    MAX_QSOFA_SCORE = 3              # Maximum possible qSOFA score
    MAX_COMPONENT_SCORE = 1          # Maximum score per component
    MAX_HOURS_LOOKBACK = 24          # Maximum hours to look back for parameters
    
    # Reasonable ranges for parameter validation
    PARAMETER_RANGES = {
        "respiratory_rate": {"min": 5, "max": 60},
        "systolic_bp": {"min": 50, "max": 250},
        "gcs": {"min": 3, "max": 15}
    }


class QsofaMortalityData:
    """qSOFA score to mortality risk data"""
    
    # Based on clinical literature
    MORTALITY_RISK = {
        0: {"risk_percent": 3, "description": "Low risk (<5%)"},
        1: {"risk_percent": 8, "description": "Moderate risk (5-10%)"},
        2: {"risk_percent": 15, "description": "High risk (10-20%)"},
        3: {"risk_percent": 25, "description": "Very high risk (>20%)"}
    }
    
    @classmethod
    def get_mortality_risk(cls, qsofa_score: int) -> str:
        """Get mortality risk description for qSOFA score"""
        risk_data = cls.MORTALITY_RISK.get(qsofa_score, {"description": "Unknown"})
        return risk_data["description"]
    
    @classmethod
    def get_mortality_percentage(cls, qsofa_score: int) -> int:
        """Get mortality percentage for qSOFA score"""
        risk_data = cls.MORTALITY_RISK.get(qsofa_score, {"risk_percent": 0})
        return risk_data["risk_percent"]


# Legacy support - maintain backward compatibility  
QSOFA_DEFAULTS = {
    "respiratory_rate": QsofaDefaults.RESPIRATORY_RATE,
    "systolic_bp": QsofaDefaults.SYSTOLIC_BP,
    "gcs": QsofaDefaults.GCS
}

QSOFA_THRESHOLDS = {
    "respiratory_rate": QsofaThresholds.RESPIRATORY_RATE_THRESHOLD,
    "systolic_bp": QsofaThresholds.SYSTOLIC_BP_THRESHOLD,
    "gcs": QsofaThresholds.GCS_THRESHOLD
}