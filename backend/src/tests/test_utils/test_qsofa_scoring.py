"""
qSOFA Score Tests

Comprehensive tests for qSOFA scoring algorithms using clinical patient scenarios
to validate individual component scores and total qSOFA calculations.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from app.utils.qsofa_scoring import (
    calculate_respiratory_score,
    calculate_cardiovascular_score,
    calculate_cns_score,
    calculate_total_qsofa,
    collect_qsofa_parameters
)
from app.models.qsofa import QsofaParameter, QsofaParameters
from tests.fixtures.qsofa_test_data import (
    create_low_risk_patient_data,
    create_medium_risk_patient_data,
    create_high_risk_patient_data,
    create_critical_risk_patient_data,
    EXPECTED_QSOFA_SCORES,
    BOUNDARY_TEST_CASES
)


class TestIndividualComponentScores:
    """Test individual qSOFA component scoring functions"""
    
    def test_calculate_respiratory_score_normal(self):
        """Test respiratory score calculation - normal case"""
        score = calculate_respiratory_score(respiratory_rate=18.0)
        assert score.score == 0
        assert score.component == "Respiratory"
        assert "18" in score.interpretation
        assert not score.threshold_met
    
    def test_calculate_respiratory_score_threshold_met(self):
        """Test respiratory score calculation - threshold met"""
        score = calculate_respiratory_score(respiratory_rate=25.0)
        assert score.score == 1
        assert score.component == "Respiratory"
        assert "25" in score.interpretation
        assert "≥22" in score.interpretation
        assert score.threshold_met
    
    def test_calculate_respiratory_score_exact_threshold(self):
        """Test respiratory score calculation - exact threshold"""
        score = calculate_respiratory_score(respiratory_rate=22.0)
        assert score.score == 1
        assert score.threshold_met
        assert "22" in score.interpretation
    
    def test_calculate_respiratory_score_just_below_threshold(self):
        """Test respiratory score calculation - just below threshold"""
        score = calculate_respiratory_score(respiratory_rate=21.0)
        assert score.score == 0
        assert not score.threshold_met
        assert "21" in score.interpretation
    
    def test_calculate_cardiovascular_score_normal(self):
        """Test cardiovascular score calculation - normal case"""
        score = calculate_cardiovascular_score(systolic_bp=120.0)
        assert score.score == 0
        assert score.component == "Cardiovascular"
        assert "120" in score.interpretation
        assert not score.threshold_met
    
    def test_calculate_cardiovascular_score_threshold_met(self):
        """Test cardiovascular score calculation - threshold met"""
        score = calculate_cardiovascular_score(systolic_bp=85.0)
        assert score.score == 1
        assert score.component == "Cardiovascular"
        assert "85" in score.interpretation
        assert "≤100" in score.interpretation
        assert score.threshold_met
    
    def test_calculate_cardiovascular_score_exact_threshold(self):
        """Test cardiovascular score calculation - exact threshold"""
        score = calculate_cardiovascular_score(systolic_bp=100.0)
        assert score.score == 1
        assert score.threshold_met
        assert "100" in score.interpretation
    
    def test_calculate_cardiovascular_score_just_above_threshold(self):
        """Test cardiovascular score calculation - just above threshold"""
        score = calculate_cardiovascular_score(systolic_bp=101.0)
        assert score.score == 0
        assert not score.threshold_met
        assert "101" in score.interpretation
    
    def test_calculate_cns_score_normal(self):
        """Test CNS score calculation - normal case"""
        score = calculate_cns_score(altered_mental_status=False, gcs=15.0)
        assert score.score == 0
        assert score.component == "Central Nervous System"
        assert "Normal" in score.interpretation
        assert not score.threshold_met
    
    def test_calculate_cns_score_altered_mental_status(self):
        """Test CNS score calculation - altered mental status"""
        score = calculate_cns_score(altered_mental_status=True, gcs=12.0)
        assert score.score == 1
        assert score.component == "Central Nervous System"
        assert "Altered" in score.interpretation
        assert "12" in score.interpretation
        assert score.threshold_met
    
    def test_calculate_cns_score_altered_no_gcs(self):
        """Test CNS score calculation - altered without GCS value"""
        score = calculate_cns_score(altered_mental_status=True, gcs=None)
        assert score.score == 1
        assert "Altered" in score.interpretation
        assert score.threshold_met
    
    def test_calculate_cns_score_normal_no_gcs(self):
        """Test CNS score calculation - normal without GCS value"""
        score = calculate_cns_score(altered_mental_status=False, gcs=None)
        assert score.score == 0
        assert "Normal" in score.interpretation
        assert not score.threshold_met


class TestPatientScenarios:
    """Test complete qSOFA score calculations using patient scenarios"""
    
    @pytest.fixture
    def mock_fhir_client(self):
        """Create a mock FHIR client for testing"""
        client = AsyncMock()
        client._make_request = AsyncMock()
        return client
    
    def test_low_risk_patient_individual_scores(self):
        """Test individual component scores for low risk patient"""
        patient_data = create_low_risk_patient_data()
        
        # Test each component score
        respiratory = calculate_respiratory_score(patient_data.respiratory_rate.value)
        assert respiratory.score == EXPECTED_QSOFA_SCORES["low_risk"]["respiratory"]
        
        cardiovascular = calculate_cardiovascular_score(patient_data.systolic_bp.value)
        assert cardiovascular.score == EXPECTED_QSOFA_SCORES["low_risk"]["cardiovascular"]
        
        cns = calculate_cns_score(patient_data.altered_mental_status, patient_data.gcs.value)
        assert cns.score == EXPECTED_QSOFA_SCORES["low_risk"]["cns"]
        
        # Verify total
        total_score = respiratory.score + cardiovascular.score + cns.score
        assert total_score == EXPECTED_QSOFA_SCORES["low_risk"]["total"]
    
    def test_medium_risk_patient_individual_scores(self):
        """Test individual component scores for medium risk patient"""
        patient_data = create_medium_risk_patient_data()
        
        # Test each component score
        respiratory = calculate_respiratory_score(patient_data.respiratory_rate.value)
        assert respiratory.score == EXPECTED_QSOFA_SCORES["medium_risk"]["respiratory"]
        
        cardiovascular = calculate_cardiovascular_score(patient_data.systolic_bp.value)
        assert cardiovascular.score == EXPECTED_QSOFA_SCORES["medium_risk"]["cardiovascular"]
        
        cns = calculate_cns_score(patient_data.altered_mental_status, patient_data.gcs.value)
        assert cns.score == EXPECTED_QSOFA_SCORES["medium_risk"]["cns"]
        
        # Verify total
        total_score = respiratory.score + cardiovascular.score + cns.score
        assert total_score == EXPECTED_QSOFA_SCORES["medium_risk"]["total"]
    
    def test_high_risk_patient_individual_scores(self):
        """Test individual component scores for high risk patient"""
        patient_data = create_high_risk_patient_data()
        
        # Test each component score
        respiratory = calculate_respiratory_score(patient_data.respiratory_rate.value)
        assert respiratory.score == EXPECTED_QSOFA_SCORES["high_risk"]["respiratory"]
        
        cardiovascular = calculate_cardiovascular_score(patient_data.systolic_bp.value)
        assert cardiovascular.score == EXPECTED_QSOFA_SCORES["high_risk"]["cardiovascular"]
        
        cns = calculate_cns_score(patient_data.altered_mental_status, patient_data.gcs.value)
        assert cns.score == EXPECTED_QSOFA_SCORES["high_risk"]["cns"]
        
        # Verify total
        total_score = respiratory.score + cardiovascular.score + cns.score
        assert total_score == EXPECTED_QSOFA_SCORES["high_risk"]["total"]
    
    def test_critical_risk_patient_individual_scores(self):
        """Test individual component scores for critical risk patient"""
        patient_data = create_critical_risk_patient_data()
        
        # Test each component score
        respiratory = calculate_respiratory_score(patient_data.respiratory_rate.value)
        assert respiratory.score == EXPECTED_QSOFA_SCORES["critical_risk"]["respiratory"]
        
        cardiovascular = calculate_cardiovascular_score(patient_data.systolic_bp.value)
        assert cardiovascular.score == EXPECTED_QSOFA_SCORES["critical_risk"]["cardiovascular"]
        
        cns = calculate_cns_score(patient_data.altered_mental_status, patient_data.gcs.value)
        assert cns.score == EXPECTED_QSOFA_SCORES["critical_risk"]["cns"]
        
        # Verify total
        total_score = respiratory.score + cardiovascular.score + cns.score
        assert total_score == EXPECTED_QSOFA_SCORES["critical_risk"]["total"]


class TestEdgeCases:
    """Test edge cases and error handling for qSOFA scoring"""
    
    def test_respiratory_score_none_value(self):
        """Test respiratory score with None value (uses default)"""
        score = calculate_respiratory_score(respiratory_rate=None)
        assert score.score == 0  # Default is 16.0, which is <22
        assert "16" in score.interpretation
    
    def test_cardiovascular_score_none_value(self):
        """Test cardiovascular score with None value (uses default)"""
        score = calculate_cardiovascular_score(systolic_bp=None)
        assert score.score == 0  # Default is 120.0, which is >100
        assert "120" in score.interpretation
    
    def test_cns_score_false_status(self):
        """Test CNS score with false altered mental status"""
        score = calculate_cns_score(altered_mental_status=False)
        assert score.score == 0
        assert "Normal" in score.interpretation
    
    def test_extreme_values_respiratory(self):
        """Test extreme respiratory rate values"""
        # Very high respiratory rate
        score_high = calculate_respiratory_score(respiratory_rate=60.0)
        assert score_high.score == 1
        assert "60" in score_high.interpretation
        
        # Very low respiratory rate (still above threshold)
        score_low = calculate_respiratory_score(respiratory_rate=5.0)
        assert score_low.score == 0
        assert "5" in score_low.interpretation
    
    def test_extreme_values_cardiovascular(self):
        """Test extreme systolic BP values"""
        # Very low systolic BP
        score_low = calculate_cardiovascular_score(systolic_bp=50.0)
        assert score_low.score == 1
        assert "50" in score_low.interpretation
        
        # Very high systolic BP
        score_high = calculate_cardiovascular_score(systolic_bp=250.0)
        assert score_high.score == 0
        assert "250" in score_high.interpretation
    
    def test_extreme_gcs_values(self):
        """Test extreme GCS values"""
        # Minimum GCS (3)
        score_min = calculate_cns_score(altered_mental_status=True, gcs=3.0)
        assert score_min.score == 1
        assert "3" in score_min.interpretation
        
        # Maximum GCS (15)
        score_max = calculate_cns_score(altered_mental_status=False, gcs=15.0)
        assert score_max.score == 0


class TestBoundaryValues:
    """Test boundary values for qSOFA scoring thresholds"""
    
    def test_respiratory_rate_boundaries(self):
        """Test respiratory rate boundary values"""
        for test_case in BOUNDARY_TEST_CASES["respiratory_rate"]:
            score = calculate_respiratory_score(respiratory_rate=test_case["value"])
            assert score.score == test_case["expected_score"], \
                f"Failed for {test_case['description']}: RR {test_case['value']}"
    
    def test_systolic_bp_boundaries(self):
        """Test systolic blood pressure boundary values"""
        for test_case in BOUNDARY_TEST_CASES["systolic_bp"]:
            score = calculate_cardiovascular_score(systolic_bp=test_case["value"])
            assert score.score == test_case["expected_score"], \
                f"Failed for {test_case['description']}: SBP {test_case['value']}"
    
    def test_gcs_boundaries(self):
        """Test GCS boundary values"""
        for test_case in BOUNDARY_TEST_CASES["gcs"]:
            altered_status = test_case["value"] < 15
            score = calculate_cns_score(altered_mental_status=altered_status, gcs=test_case["value"])
            assert score.score == test_case["expected_score"], \
                f"Failed for {test_case['description']}: GCS {test_case['value']}"


class TestRiskStratification:
    """Test qSOFA risk stratification logic"""
    
    def test_low_risk_identification(self):
        """Test identification of low risk patients (qSOFA 0-1)"""
        patient_data = create_low_risk_patient_data()
        
        respiratory = calculate_respiratory_score(patient_data.respiratory_rate.value)
        cardiovascular = calculate_cardiovascular_score(patient_data.systolic_bp.value)
        cns = calculate_cns_score(patient_data.altered_mental_status, patient_data.gcs.value)
        
        total_score = respiratory.score + cardiovascular.score + cns.score
        high_risk = total_score >= 2
        
        assert total_score == 0
        assert not high_risk
    
    def test_moderate_risk_identification(self):
        """Test identification of moderate risk patients (qSOFA 1)"""
        patient_data = create_medium_risk_patient_data()
        
        respiratory = calculate_respiratory_score(patient_data.respiratory_rate.value)
        cardiovascular = calculate_cardiovascular_score(patient_data.systolic_bp.value)
        cns = calculate_cns_score(patient_data.altered_mental_status, patient_data.gcs.value)
        
        total_score = respiratory.score + cardiovascular.score + cns.score
        high_risk = total_score >= 2
        
        assert total_score == 1
        assert not high_risk
    
    def test_high_risk_identification(self):
        """Test identification of high risk patients (qSOFA ≥2)"""
        patient_data = create_high_risk_patient_data()
        
        respiratory = calculate_respiratory_score(patient_data.respiratory_rate.value)
        cardiovascular = calculate_cardiovascular_score(patient_data.systolic_bp.value)
        cns = calculate_cns_score(patient_data.altered_mental_status, patient_data.gcs.value)
        
        total_score = respiratory.score + cardiovascular.score + cns.score
        high_risk = total_score >= 2
        
        assert total_score == 2
        assert high_risk
    
    def test_critical_risk_identification(self):
        """Test identification of critical risk patients (qSOFA 3)"""
        patient_data = create_critical_risk_patient_data()
        
        respiratory = calculate_respiratory_score(patient_data.respiratory_rate.value)
        cardiovascular = calculate_cardiovascular_score(patient_data.systolic_bp.value)
        cns = calculate_cns_score(patient_data.altered_mental_status, patient_data.gcs.value)
        
        total_score = respiratory.score + cardiovascular.score + cns.score
        high_risk = total_score >= 2
        
        assert total_score == 3
        assert high_risk


@pytest.mark.parametrize("patient_type,expected_total,expected_high_risk", [
    ("low_risk", 0, False),
    ("medium_risk", 1, False),
    ("high_risk", 2, True),
    ("critical_risk", 3, True)
])
def test_patient_total_scores(patient_type, expected_total, expected_high_risk):
    """Parameterized test for patient total qSOFA scores"""
    if patient_type == "low_risk":
        patient_data = create_low_risk_patient_data()
    elif patient_type == "medium_risk":
        patient_data = create_medium_risk_patient_data()
    elif patient_type == "high_risk":
        patient_data = create_high_risk_patient_data()
    else:  # critical_risk
        patient_data = create_critical_risk_patient_data()
    
    # Calculate all individual scores
    respiratory = calculate_respiratory_score(patient_data.respiratory_rate.value)
    cardiovascular = calculate_cardiovascular_score(patient_data.systolic_bp.value)
    cns = calculate_cns_score(patient_data.altered_mental_status, patient_data.gcs.value)
    
    total_score = respiratory.score + cardiovascular.score + cns.score
    high_risk = total_score >= 2
    
    assert total_score == expected_total
    assert high_risk == expected_high_risk


@pytest.mark.parametrize("respiratory_rate,systolic_bp,gcs,altered_status,expected_score", [
    (16, 120, 15, False, 0),  # All normal
    (25, 120, 15, False, 1),  # Only tachypnea
    (16, 95, 15, False, 1),   # Only hypotension
    (16, 120, 12, True, 1),   # Only altered mental status
    (25, 95, 15, False, 2),   # Tachypnea + hypotension
    (25, 120, 12, True, 2),   # Tachypnea + altered mental status
    (16, 95, 12, True, 2),    # Hypotension + altered mental status
    (25, 95, 12, True, 3),    # All abnormal
])
def test_qsofa_combinations(respiratory_rate, systolic_bp, gcs, altered_status, expected_score):
    """Test various combinations of qSOFA parameters"""
    respiratory = calculate_respiratory_score(respiratory_rate)
    cardiovascular = calculate_cardiovascular_score(systolic_bp)
    cns = calculate_cns_score(altered_status, gcs)
    
    total_score = respiratory.score + cardiovascular.score + cns.score
    assert total_score == expected_score