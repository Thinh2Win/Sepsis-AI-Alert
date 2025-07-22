"""
NEWS2 (National Early Warning Score 2) Constants

Configuration constants for NEWS2 scoring including:
- Clinical thresholds and scoring rules
- LOINC code mappings for FHIR data collection
- Default values and parameter configurations
- Clinical response thresholds
"""

from app.core.loinc_codes import LOINCCodes

# =============================================================================
# NEWS2 SCORING THRESHOLDS
# =============================================================================

class NEWS2Thresholds:
    """Clinical thresholds for NEWS2 scoring based on official NHS guidelines"""
    
    # Respiratory Rate (breaths per minute)
    RESPIRATORY_RATE = {
        "score_3": [None, 8],       # ≤8 or ≥25
        "score_2": [9, 11],         # 9-11
        "score_1": [21, 24],        # 21-24
        "score_0": [12, 20],        # 12-20 (normal)
        "score_3_upper": 25         # ≥25
    }
    
    # Oxygen Saturation (%) - Scale 1 (standard patients)
    OXYGEN_SATURATION_SCALE1 = {
        "score_3": [None, 91],      # ≤91
        "score_2": [92, 93],        # 92-93
        "score_1": [94, 95],        # 94-95
        "score_0": [96, 100]        # ≥96 (normal)
    }
    
    # Oxygen Saturation (%) - Scale 2 (COPD/hypercapnic respiratory failure)
    OXYGEN_SATURATION_SCALE2 = {
        "score_3": [None, 83],      # ≤83
        "score_2": [84, 85],        # 84-85
        "score_1": [86, 87],        # 86-87
        "score_0": [88, 92],        # 88-92 (target for COPD)
        "score_3_upper": 93         # ≥93 (paradoxically high for COPD)
    }
    
    # Supplemental Oxygen
    SUPPLEMENTAL_OXYGEN = {
        "score_2": True,            # On any supplemental oxygen = 2 points
        "score_0": False            # Room air = 0 points
    }
    
    # Temperature (°C)
    TEMPERATURE = {
        "score_3": [None, 35.0],    # ≤35.0
        "score_1": [35.1, 36.0],    # 35.1-36.0 or 38.1-39.0
        "score_0": [36.1, 38.0],    # 36.1-38.0 (normal)
        "score_1_upper": [38.1, 39.0],
        "score_2": [39.1, 100.0]    # ≥39.1
    }
    
    # Systolic Blood Pressure (mmHg)
    SYSTOLIC_BP = {
        "score_3": [None, 90],      # ≤90
        "score_2": [91, 100],       # 91-100
        "score_1": [101, 110],      # 101-110
        "score_0": [111, 219],      # 111-219 (normal)
        "score_3_upper": 220        # ≥220
    }
    
    # Heart Rate (beats per minute)
    HEART_RATE = {
        "score_3": [None, 40],      # ≤40 or ≥131
        "score_1": [41, 50],        # 41-50 or 91-110
        "score_0": [51, 90],        # 51-90 (normal)
        "score_1_upper": [91, 110],
        "score_2": [111, 130],      # 111-130
        "score_3_upper": 131        # ≥131
    }
    
    # Level of Consciousness (AVPU/GCS)
    CONSCIOUSNESS = {
        "score_0": 15,              # Alert (GCS 15)
        "score_3": [3, 14]          # Any impairment (GCS <15 or AVPU != Alert)
    }

# =============================================================================
# NEWS2 RISK THRESHOLDS
# =============================================================================

class NEWS2RiskThresholds:
    """Clinical response thresholds for NEWS2 scores"""
    
    # Total score thresholds
    LOW_RISK_MAX = 4        # 0-4: Low risk
    MEDIUM_RISK_MIN = 5     # 5-6: Medium risk
    MEDIUM_RISK_MAX = 6
    HIGH_RISK_MIN = 7       # ≥7: High risk
    
    # Single parameter threshold for medium risk upgrade
    SINGLE_PARAMETER_URGENT = 3  # Any single parameter = 3 triggers urgent review
    
    # Clinical response requirements
    RESPONSES = {
        "LOW": {
            "frequency": "4-12 hourly",
            "action": "Routine monitoring",
            "escalation": False
        },
        "MEDIUM": {
            "frequency": "Hourly",
            "action": "Urgent review within 1 hour",
            "escalation": True
        },
        "HIGH": {
            "frequency": "Continuous",
            "action": "Emergency assessment",
            "escalation": True
        }
    }

# =============================================================================
# FHIR PARAMETER CONFIGURATIONS
# =============================================================================

class NEWS2FHIRConfig:
    """FHIR parameter collection configurations for NEWS2"""
    
    # Core vital signs parameters (reused from SOFA/qSOFA)
    VITAL_SIGNS_PARAMETERS = {
        "respiratory_rate": {
            "codes": [LOINCCodes.VITAL_SIGNS["respiratory_rate"]],  # 9279-1
            "count": 3,
            "system_name": "respiratory_rate",
            "parameter_mapping": {
                LOINCCodes.VITAL_SIGNS["respiratory_rate"]: "respiratory_rate"
            }
        },
        "oxygen_saturation": {
            "codes": [LOINCCodes.VITAL_SIGNS["oxygen_saturation"]],  # 2708-6
            "count": 3,
            "system_name": "oxygen_saturation",
            "parameter_mapping": {
                LOINCCodes.VITAL_SIGNS["oxygen_saturation"]: "oxygen_saturation"
            }
        },
        "temperature": {
            "codes": [LOINCCodes.VITAL_SIGNS["body_temperature"]],  # 8310-5
            "count": 3,
            "system_name": "temperature",
            "parameter_mapping": {
                LOINCCodes.VITAL_SIGNS["body_temperature"]: "temperature"
            }
        },
        "systolic_bp": {
            "codes": [LOINCCodes.VITAL_SIGNS["systolic_bp"]],  # 8480-6
            "count": 3,
            "system_name": "systolic_bp",
            "parameter_mapping": {
                LOINCCodes.VITAL_SIGNS["systolic_bp"]: "systolic_bp"
            }
        },
        "heart_rate": {
            "codes": [LOINCCodes.VITAL_SIGNS["heart_rate"]],  # 8867-4
            "count": 3,
            "system_name": "heart_rate",
            "parameter_mapping": {
                LOINCCodes.VITAL_SIGNS["heart_rate"]: "heart_rate"
            }
        }
    }
    
    # GCS parameter (reused from SOFA/qSOFA)
    NEUROLOGICAL_PARAMETERS = {
        "gcs": {
            "codes": [LOINCCodes.VITAL_SIGNS["glasgow_coma_score"]],  # 9269-2
            "count": 3,
            "system_name": "gcs",
            "parameter_mapping": {
                LOINCCodes.VITAL_SIGNS["glasgow_coma_score"]: "gcs"
            }
        }
    }
    
    # Supplemental oxygen - NEW parameter (not in SOFA/qSOFA)
    SUPPLEMENTAL_OXYGEN_PARAMETERS = {
        "supplemental_oxygen": {
            # Check medication administration for oxygen therapy
            "medication_codes": [
                "oxygen",
                "O2", 
                "supplemental oxygen",
                "nasal cannula",
                "face mask",
                "non-rebreather",
                "high-flow nasal cannula"
            ],
            # Check device/procedure codes
            "device_codes": [
                "371907003",  # SNOMED: Oxygen administration
                "57485005",   # SNOMED: Nasal cannula
                "26412008"    # SNOMED: Face mask oxygen therapy
            ]
        }
    }

# =============================================================================
# DEFAULT VALUES
# =============================================================================

class NEWS2Defaults:
    """Default values for missing NEWS2 parameters"""
    
    PARAMETER_DEFAULTS = {
        "respiratory_rate": 16.0,       # Normal RR
        "oxygen_saturation": 98.0,      # Normal SpO2
        "supplemental_oxygen": False,   # Assume room air
        "temperature": 37.0,            # Normal temp (°C)
        "systolic_bp": 120.0,          # Normal SBP
        "heart_rate": 75.0,            # Normal HR
        "consciousness_level": 15.0     # Normal GCS (Alert)
    }
    
    PARAMETER_UNITS = {
        "respiratory_rate": "breaths/min",
        "oxygen_saturation": "%",
        "temperature": "°C",
        "systolic_bp": "mmHg",
        "heart_rate": "bpm",
        "consciousness_level": "points"
    }
    
    # Data lookback window for NEWS2 (shorter than SOFA for rapid assessment)
    LOOKBACK_HOURS = 4  # 4-hour window for rapid assessment
    
    # Minimum data reliability threshold
    MIN_RELIABILITY_THRESHOLD = 0.6

# =============================================================================
# CLINICAL MAPPINGS
# =============================================================================

class NEWS2ClinicalMappings:
    """Clinical interpretation mappings for NEWS2"""
    
    AVPU_TO_GCS = {
        "A": 15,  # Alert = GCS 15
        "C": 14,  # Confused = GCS 14 (new confusion)
        "V": 10,  # Voice = GCS ~10
        "P": 8,   # Pain = GCS ~8
        "U": 3    # Unresponsive = GCS 3
    }
    
    CONSCIOUSNESS_INTERPRETATIONS = {
        15: "Alert",
        14: "New confusion",
        13: "Mild impairment",
        10: "Responds to voice",
        8: "Responds to pain",
        3: "Unresponsive"
    }
    
    RISK_LEVEL_COLORS = {
        "LOW": "green",
        "MEDIUM": "amber", 
        "HIGH": "red"
    }
    
    COMPONENT_NAMES = {
        "respiratory_rate": "Respiratory Rate",
        "oxygen_saturation": "Oxygen Saturation", 
        "supplemental_oxygen": "Supplemental Oxygen",
        "temperature": "Temperature",
        "systolic_bp": "Systolic Blood Pressure",
        "heart_rate": "Heart Rate",
        "consciousness": "Level of Consciousness"
    }