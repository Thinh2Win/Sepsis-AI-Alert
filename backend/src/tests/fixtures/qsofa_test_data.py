"""
qSOFA Score Test Data Fixtures

Contains patient scenarios for testing qSOFA scoring algorithms with
medium, high, and critical risk patients.
"""

from datetime import datetime
from app.models.qsofa import QsofaParameter, QsofaParameters


def create_medium_risk_patient_data() -> QsofaParameters:
    """
    Create medium risk patient data for qSOFA testing
    
    Expected qSOFA Score: 1 (Moderate Risk)
    - Respiratory: 0 (RR 20, <22 threshold)
    - Cardiovascular: 1 (SBP 95, ≤100 threshold)
    - CNS: 0 (GCS 15, not altered)
    """
    timestamp = datetime(2025, 1, 20, 10, 30)
    
    return QsofaParameters(
        patient_id="medium-risk-qsofa-patient-123",
        timestamp=timestamp,
        # Respiratory system - normal
        respiratory_rate=QsofaParameter(
            value=20.0, unit='breaths/min', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        # Cardiovascular system - hypotensive (meets threshold)
        systolic_bp=QsofaParameter(
            value=95.0, unit='mmHg', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        # Central nervous system - normal
        gcs=QsofaParameter(
            value=15.0, unit='score', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        altered_mental_status=False
    )


def create_high_risk_patient_data() -> QsofaParameters:
    """
    Create high risk patient data for qSOFA testing
    
    Expected qSOFA Score: 2 (High Risk - triggers sepsis evaluation)
    - Respiratory: 1 (RR 25, ≥22 threshold)
    - Cardiovascular: 1 (SBP 85, ≤100 threshold)
    - CNS: 0 (GCS 15, not altered)
    """
    timestamp = datetime(2025, 1, 20, 10, 30)
    
    return QsofaParameters(
        patient_id="high-risk-qsofa-patient-456",
        timestamp=timestamp,
        # Respiratory system - tachypneic (meets threshold)
        respiratory_rate=QsofaParameter(
            value=25.0, unit='breaths/min', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        # Cardiovascular system - hypotensive (meets threshold)
        systolic_bp=QsofaParameter(
            value=85.0, unit='mmHg', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        # Central nervous system - normal
        gcs=QsofaParameter(
            value=15.0, unit='score', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        altered_mental_status=False
    )


def create_critical_risk_patient_data() -> QsofaParameters:
    """
    Create critical risk patient data for qSOFA testing
    
    Expected qSOFA Score: 3 (Maximum qSOFA Score - Critical Risk)
    - Respiratory: 1 (RR 28, ≥22 threshold)
    - Cardiovascular: 1 (SBP 75, ≤100 threshold)
    - CNS: 1 (GCS 12, <15 threshold - altered mental status)
    """
    timestamp = datetime(2025, 1, 20, 10, 30)
    
    return QsofaParameters(
        patient_id="critical-risk-qsofa-patient-789",
        timestamp=timestamp,
        # Respiratory system - severely tachypneic (meets threshold)
        respiratory_rate=QsofaParameter(
            value=28.0, unit='breaths/min', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        # Cardiovascular system - severely hypotensive (meets threshold)
        systolic_bp=QsofaParameter(
            value=75.0, unit='mmHg', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        # Central nervous system - altered mental status (meets threshold)
        gcs=QsofaParameter(
            value=12.0, unit='score', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        altered_mental_status=True
    )


def create_low_risk_patient_data() -> QsofaParameters:
    """
    Create low risk patient data for qSOFA testing
    
    Expected qSOFA Score: 0 (Low Risk)
    - Respiratory: 0 (RR 16, <22 threshold)
    - Cardiovascular: 0 (SBP 120, >100 threshold)
    - CNS: 0 (GCS 15, not altered)
    """
    timestamp = datetime(2025, 1, 20, 10, 30)
    
    return QsofaParameters(
        patient_id="low-risk-qsofa-patient-000",
        timestamp=timestamp,
        # Respiratory system - normal
        respiratory_rate=QsofaParameter(
            value=16.0, unit='breaths/min', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        # Cardiovascular system - normal
        systolic_bp=QsofaParameter(
            value=120.0, unit='mmHg', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        # Central nervous system - normal
        gcs=QsofaParameter(
            value=15.0, unit='score', timestamp=timestamp,
            is_estimated=False, source='measured'
        ),
        altered_mental_status=False
    )


# Expected scores for validation
EXPECTED_QSOFA_SCORES = {
    "low_risk": {
        "respiratory": 0,
        "cardiovascular": 0,
        "cns": 0,
        "total": 0,
        "high_risk": False
    },
    "medium_risk": {
        "respiratory": 0,
        "cardiovascular": 1,
        "cns": 0,
        "total": 1,
        "high_risk": False
    },
    "high_risk": {
        "respiratory": 1,
        "cardiovascular": 1,
        "cns": 0,
        "total": 2,
        "high_risk": True
    },
    "critical_risk": {
        "respiratory": 1,
        "cardiovascular": 1,
        "cns": 1,
        "total": 3,
        "high_risk": True
    }
}

# Boundary test cases for each parameter
BOUNDARY_TEST_CASES = {
    "respiratory_rate": [
        {"value": 21.0, "expected_score": 0, "description": "Just below threshold"},
        {"value": 22.0, "expected_score": 1, "description": "At threshold"},
        {"value": 23.0, "expected_score": 1, "description": "Above threshold"}
    ],
    "systolic_bp": [
        {"value": 101.0, "expected_score": 0, "description": "Just above threshold"},
        {"value": 100.0, "expected_score": 1, "description": "At threshold"},
        {"value": 99.0, "expected_score": 1, "description": "Below threshold"}
    ],
    "gcs": [
        {"value": 15.0, "expected_score": 0, "description": "Normal (not altered)"},
        {"value": 14.0, "expected_score": 1, "description": "Altered mental status"},
        {"value": 13.0, "expected_score": 1, "description": "More altered"},
        {"value": 3.0, "expected_score": 1, "description": "Severely altered"}
    ]
}