"""
SOFA Score Test Data Fixtures

Contains patient scenarios for testing SOFA scoring algorithms with
medium, high, and critical risk patients.
"""

from datetime import datetime
from app.models.sofa import SofaParameter, VasopressorDoses, SofaParameters


def create_medium_risk_patient_data() -> SofaParameters:
    """
    Create medium risk patient data for SOFA testing
    
    Expected SOFA Score: 10 (High Risk Range)
    - Respiratory: 2 (PaO2/FiO2 250, no ventilation)
    - Coagulation: 2 (Platelets 80)  
    - Liver: 2 (Bilirubin 3.5)
    - Cardiovascular: 1 (MAP 62, no vasopressors)
    - CNS: 1 (GCS 13)
    - Renal: 2 (Creatinine 2.5)
    """
    timestamp = datetime(2025, 1, 18, 10, 30)
    
    return SofaParameters(
        patient_id="medium-risk-patient-123",
        timestamp=timestamp,
        # Respiratory system
        pao2=SofaParameter(
            value=75, unit='mmHg', timestamp=timestamp, 
            is_estimated=False, source='measured'
        ),
        fio2=SofaParameter(
            value=0.3, unit='fraction', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        pao2_fio2_ratio=SofaParameter(
            value=250, unit='mmHg', timestamp=timestamp,
            is_estimated=False, source='calculated'
        ),
        mechanical_ventilation=False,
        # Coagulation system
        platelets=SofaParameter(
            value=80, unit='K/µL', timestamp=datetime(2025, 1, 18, 9, 0),
            is_estimated=False, source='measured'
        ),
        # Liver system
        bilirubin=SofaParameter(
            value=3.5, unit='mg/dL', timestamp=datetime(2025, 1, 18, 9, 0),
            is_estimated=False, source='measured'
        ),
        # Cardiovascular system
        systolic_bp=SofaParameter(
            value=85, unit='mmHg', timestamp=datetime(2025, 1, 18, 10, 15),
            is_estimated=False, source='measured'
        ),
        diastolic_bp=SofaParameter(
            value=50, unit='mmHg', timestamp=datetime(2025, 1, 18, 10, 15),
            is_estimated=False, source='measured'
        ),
        map_value=SofaParameter(
            value=62, unit='mmHg', timestamp=datetime(2025, 1, 18, 10, 15),
            is_estimated=False, source='calculated'
        ),
        vasopressor_doses=VasopressorDoses(),
        # Central nervous system
        gcs=SofaParameter(
            value=13, unit='score', timestamp=datetime(2025, 1, 18, 10, 0),
            is_estimated=False, source='measured'
        ),
        # Renal system
        creatinine=SofaParameter(
            value=2.5, unit='mg/dL', timestamp=datetime(2025, 1, 18, 9, 0),
            is_estimated=False, source='measured'
        ),
        urine_output_24h=SofaParameter(
            value=600, unit='mL', timestamp=datetime(2025, 1, 18, 10, 0),
            is_estimated=False, source='measured'
        )
    )


def create_high_risk_patient_data() -> SofaParameters:
    """
    Create high risk patient data for SOFA testing
    
    Expected SOFA Score: 17 (Extremely High Risk)
    - Respiratory: 3 (PaO2/FiO2 150, on ventilation)
    - Coagulation: 3 (Platelets 40)
    - Liver: 3 (Bilirubin 7.5) 
    - Cardiovascular: 3 (MAP 53 + dopamine 8.0)
    - CNS: 2 (GCS 10)
    - Renal: 3 (Creatinine 4.2)
    """
    timestamp = datetime(2025, 1, 18, 10, 30)
    
    return SofaParameters(
        patient_id="high-risk-patient-456",
        timestamp=timestamp,
        # Respiratory system
        pao2=SofaParameter(
            value=75, unit='mmHg', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        fio2=SofaParameter(
            value=0.5, unit='fraction', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        pao2_fio2_ratio=SofaParameter(
            value=150, unit='mmHg', timestamp=timestamp,
            is_estimated=False, source='calculated'
        ),
        mechanical_ventilation=True,
        # Coagulation system
        platelets=SofaParameter(
            value=40, unit='K/µL', timestamp=datetime(2025, 1, 18, 9, 0),
            is_estimated=False, source='measured'
        ),
        # Liver system
        bilirubin=SofaParameter(
            value=7.5, unit='mg/dL', timestamp=datetime(2025, 1, 18, 9, 0),
            is_estimated=False, source='measured'
        ),
        # Cardiovascular system
        systolic_bp=SofaParameter(
            value=80, unit='mmHg', timestamp=datetime(2025, 1, 18, 10, 15),
            is_estimated=False, source='measured'
        ),
        diastolic_bp=SofaParameter(
            value=40, unit='mmHg', timestamp=datetime(2025, 1, 18, 10, 15),
            is_estimated=False, source='measured'
        ),
        map_value=SofaParameter(
            value=53, unit='mmHg', timestamp=datetime(2025, 1, 18, 10, 15),
            is_estimated=False, source='calculated'
        ),
        vasopressor_doses=VasopressorDoses(
            dopamine=8.0
        ),
        # Central nervous system
        gcs=SofaParameter(
            value=10, unit='score', timestamp=datetime(2025, 1, 18, 10, 0),
            is_estimated=False, source='measured'
        ),
        # Renal system
        creatinine=SofaParameter(
            value=4.2, unit='mg/dL', timestamp=datetime(2025, 1, 18, 9, 0),
            is_estimated=False, source='measured'
        ),
        urine_output_24h=SofaParameter(
            value=350, unit='mL', timestamp=datetime(2025, 1, 18, 10, 0),
            is_estimated=False, source='measured'
        )
    )


def create_critical_risk_patient_data() -> SofaParameters:
    """
    Create critical risk patient data for SOFA testing
    
    Expected SOFA Score: 24 (Maximum SOFA Score)
    - Respiratory: 4 (PaO2/FiO2 85, on ventilation)
    - Coagulation: 4 (Platelets 15)
    - Liver: 4 (Bilirubin 14.5)
    - Cardiovascular: 4 (High-dose epinephrine/norepinephrine)
    - CNS: 4 (GCS 5)
    - Renal: 4 (Creatinine 5.8, oliguria <200mL)
    """
    timestamp = datetime(2025, 1, 18, 10, 30)
    
    return SofaParameters(
        patient_id="critical-risk-patient-789",
        timestamp=timestamp,
        # Respiratory system
        pao2=SofaParameter(
            value=60, unit='mmHg', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        fio2=SofaParameter(
            value=0.7, unit='fraction', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        pao2_fio2_ratio=SofaParameter(
            value=85, unit='mmHg', timestamp=timestamp,
            is_estimated=False, source='calculated'
        ),
        mechanical_ventilation=True,
        # Coagulation system
        platelets=SofaParameter(
            value=15, unit='K/µL', timestamp=datetime(2025, 1, 18, 9, 0),
            is_estimated=False, source='measured'
        ),
        # Liver system
        bilirubin=SofaParameter(
            value=14.5, unit='mg/dL', timestamp=datetime(2025, 1, 18, 9, 0),
            is_estimated=False, source='measured'
        ),
        # Cardiovascular system
        systolic_bp=SofaParameter(
            value=70, unit='mmHg', timestamp=datetime(2025, 1, 18, 10, 15),
            is_estimated=False, source='measured'
        ),
        diastolic_bp=SofaParameter(
            value=35, unit='mmHg', timestamp=datetime(2025, 1, 18, 10, 15),
            is_estimated=False, source='measured'
        ),
        map_value=SofaParameter(
            value=47, unit='mmHg', timestamp=datetime(2025, 1, 18, 10, 15),
            is_estimated=False, source='calculated'
        ),
        vasopressor_doses=VasopressorDoses(
            epinephrine=0.15,
            norepinephrine=0.3
        ),
        # Central nervous system
        gcs=SofaParameter(
            value=5, unit='score', timestamp=datetime(2025, 1, 18, 10, 0),
            is_estimated=False, source='measured'
        ),
        # Renal system
        creatinine=SofaParameter(
            value=5.8, unit='mg/dL', timestamp=datetime(2025, 1, 18, 9, 0),
            is_estimated=False, source='measured'
        ),
        urine_output_24h=SofaParameter(
            value=150, unit='mL', timestamp=datetime(2025, 1, 18, 10, 0),
            is_estimated=False, source='measured'
        )
    )


# Expected scores for validation
EXPECTED_SCORES = {
    "medium_risk": {
        "respiratory": 2,
        "coagulation": 2,
        "liver": 2,
        "cardiovascular": 1,
        "cns": 1,
        "renal": 2,
        "total": 10
    },
    "high_risk": {
        "respiratory": 3,
        "coagulation": 3,
        "liver": 3,
        "cardiovascular": 3,
        "cns": 2,
        "renal": 3,
        "total": 17
    },
    "critical_risk": {
        "respiratory": 4,
        "coagulation": 4,
        "liver": 4,
        "cardiovascular": 4,
        "cns": 4,
        "renal": 4,
        "total": 24
    }
}