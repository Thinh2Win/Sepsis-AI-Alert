"""
SOFA Score Tests

Comprehensive tests for SOFA scoring algorithms using clinical patient scenarios
to validate individual organ system scores and total SOFA calculations.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from app.utils.sofa_scoring import (
    calculate_respiratory_score,
    calculate_coagulation_score,
    calculate_liver_score,
    calculate_cardiovascular_score,
    calculate_cns_score,
    calculate_renal_score,
    calculate_total_sofa,
    collect_sofa_parameters
)
from app.models.sofa import SofaParameter, VasopressorDoses, SofaParameters
from tests.fixtures.sofa_test_data import (
    create_medium_risk_patient_data,
    create_high_risk_patient_data,
    create_critical_risk_patient_data,
    EXPECTED_SCORES
)


class TestIndividualOrganScores:
    """Test individual organ system SOFA scoring functions"""
    
    def test_calculate_respiratory_score_normal(self):
        """Test respiratory score calculation - normal case"""
        score = calculate_respiratory_score(pao2=400, fio2=1.0, on_ventilation=False)
        assert score.score == 0
        assert score.organ_system == "Respiratory"
        assert "400.0" in score.interpretation
    
    def test_calculate_respiratory_score_medium_risk(self):
        """Test respiratory score calculation - medium risk patient"""
        score = calculate_respiratory_score(pao2=75, fio2=0.3, on_ventilation=False)
        assert score.score == 2  # PaO2/FiO2 = 250, score = 2
        assert "250.0" in score.interpretation
    
    def test_calculate_respiratory_score_high_risk_ventilated(self):
        """Test respiratory score calculation - high risk with ventilation"""
        score = calculate_respiratory_score(pao2=75, fio2=0.5, on_ventilation=True)
        assert score.score == 3  # PaO2/FiO2 = 150, on ventilation, score = 3
        assert "150.0" in score.interpretation
        assert "mechanical ventilation" in score.interpretation
    
    def test_calculate_respiratory_score_critical_ventilated(self):
        """Test respiratory score calculation - critical with ventilation"""
        score = calculate_respiratory_score(pao2=60, fio2=0.7, on_ventilation=True)
        assert score.score == 4  # PaO2/FiO2 = 85.7, on ventilation, score = 4
        assert "mechanical ventilation" in score.interpretation
    
    def test_calculate_coagulation_score_normal(self):
        """Test coagulation score calculation - normal platelets"""
        score = calculate_coagulation_score(platelets=200)
        assert score.score == 0
        assert score.organ_system == "Coagulation"
        assert "200" in score.interpretation
    
    def test_calculate_coagulation_score_medium_risk(self):
        """Test coagulation score calculation - medium risk patient"""
        score = calculate_coagulation_score(platelets=80)
        assert score.score == 2  # 50-99 range
        assert "80" in score.interpretation
    
    def test_calculate_coagulation_score_critical(self):
        """Test coagulation score calculation - critical patient"""
        score = calculate_coagulation_score(platelets=15)
        assert score.score == 4  # <20 range
        assert "15" in score.interpretation
    
    def test_calculate_liver_score_normal(self):
        """Test liver score calculation - normal bilirubin"""
        score = calculate_liver_score(bilirubin=1.0)
        assert score.score == 0
        assert score.organ_system == "Liver"
        assert "1.0" in score.interpretation
    
    def test_calculate_liver_score_medium_risk(self):
        """Test liver score calculation - medium risk patient"""
        score = calculate_liver_score(bilirubin=3.5)
        assert score.score == 2  # 2.0-5.9 range
        assert "3.5" in score.interpretation
    
    def test_calculate_liver_score_critical(self):
        """Test liver score calculation - critical patient"""
        score = calculate_liver_score(bilirubin=14.5)
        assert score.score == 4  # ≥12.0 range
        assert "14.5" in score.interpretation
    
    def test_calculate_cardiovascular_score_normal(self):
        """Test cardiovascular score calculation - normal MAP"""
        score = calculate_cardiovascular_score(map_value=80, vasopressor_doses=VasopressorDoses())
        assert score.score == 0
        assert "80" in score.interpretation
    
    def test_calculate_cardiovascular_score_hypotension(self):
        """Test cardiovascular score calculation - hypotension only"""
        score = calculate_cardiovascular_score(map_value=62, vasopressor_doses=VasopressorDoses())
        assert score.score == 1  # MAP < 70
        assert "62" in score.interpretation
    
    def test_calculate_cardiovascular_score_dopamine_medium(self):
        """Test cardiovascular score calculation - medium dose dopamine"""
        vasopressors = VasopressorDoses(dopamine=8.0)
        score = calculate_cardiovascular_score(map_value=53, vasopressor_doses=vasopressors)
        assert score.score == 3  # Dopamine 5-15 mcg/kg/min
        assert "8.0" in score.interpretation
    
    def test_calculate_cardiovascular_score_high_dose_vasopressors(self):
        """Test cardiovascular score calculation - high dose vasopressors"""
        vasopressors = VasopressorDoses(epinephrine=0.15, norepinephrine=0.3)
        score = calculate_cardiovascular_score(map_value=47, vasopressor_doses=vasopressors)
        assert score.score == 4  # High-dose vasopressors
        assert "High-dose" in score.interpretation
    
    def test_calculate_cns_score_normal(self):
        """Test CNS score calculation - normal GCS"""
        score = calculate_cns_score(gcs=15)
        assert score.score == 0
        assert score.organ_system == "Central Nervous System"
        assert "15" in score.interpretation
    
    def test_calculate_cns_score_medium_risk(self):
        """Test CNS score calculation - medium risk patient"""
        score = calculate_cns_score(gcs=13)
        assert score.score == 1  # GCS 13-14
        assert "13" in score.interpretation
    
    def test_calculate_cns_score_critical(self):
        """Test CNS score calculation - critical patient"""
        score = calculate_cns_score(gcs=5)
        assert score.score == 4  # GCS <6
        assert "5" in score.interpretation
    
    def test_calculate_renal_score_normal(self):
        """Test renal score calculation - normal values"""
        score = calculate_renal_score(creatinine=1.0, urine_output_24h=1000)
        assert score.score == 0
        assert score.organ_system == "Renal"
        assert "1.0" in score.interpretation
    
    def test_calculate_renal_score_medium_risk(self):
        """Test renal score calculation - medium risk patient"""
        score = calculate_renal_score(creatinine=2.5, urine_output_24h=600)
        assert score.score == 2  # Creatinine 2.0-3.4 range
        assert "2.5" in score.interpretation
    
    def test_calculate_renal_score_critical_oliguria(self):
        """Test renal score calculation - critical with severe oliguria"""
        score = calculate_renal_score(creatinine=5.8, urine_output_24h=150)
        assert score.score == 4  # Creatinine ≥5.0 OR urine <200 mL/day
        assert "5.8" in score.interpretation
        assert "150" in score.interpretation


class TestPatientScenarios:
    """Test complete SOFA score calculations using patient scenarios"""
    
    @pytest.fixture
    def mock_fhir_client(self):
        """Create a mock FHIR client for testing"""
        client = AsyncMock()
        client._make_request = AsyncMock()
        return client
    
    def test_medium_risk_patient_individual_scores(self):
        """Test individual organ scores for medium risk patient"""
        patient_data = create_medium_risk_patient_data()
        
        # Test each organ system score
        respiratory = calculate_respiratory_score(
            patient_data.pao2.value,
            patient_data.fio2.value,
            patient_data.mechanical_ventilation
        )
        assert respiratory.score == EXPECTED_SCORES["medium_risk"]["respiratory"]
        
        coagulation = calculate_coagulation_score(patient_data.platelets.value)
        assert coagulation.score == EXPECTED_SCORES["medium_risk"]["coagulation"]
        
        liver = calculate_liver_score(patient_data.bilirubin.value)
        assert liver.score == EXPECTED_SCORES["medium_risk"]["liver"]
        
        cardiovascular = calculate_cardiovascular_score(
            patient_data.map_value.value,
            patient_data.vasopressor_doses
        )
        assert cardiovascular.score == EXPECTED_SCORES["medium_risk"]["cardiovascular"]
        
        cns = calculate_cns_score(patient_data.gcs.value)
        assert cns.score == EXPECTED_SCORES["medium_risk"]["cns"]
        
        renal = calculate_renal_score(
            patient_data.creatinine.value,
            patient_data.urine_output_24h.value
        )
        assert renal.score == EXPECTED_SCORES["medium_risk"]["renal"]
        
        # Verify total
        total_score = (respiratory.score + coagulation.score + liver.score + 
                      cardiovascular.score + cns.score + renal.score)
        assert total_score == EXPECTED_SCORES["medium_risk"]["total"]
    
    def test_high_risk_patient_individual_scores(self):
        """Test individual organ scores for high risk patient"""
        patient_data = create_high_risk_patient_data()
        
        # Test each organ system score
        respiratory = calculate_respiratory_score(
            patient_data.pao2.value,
            patient_data.fio2.value,
            patient_data.mechanical_ventilation
        )
        assert respiratory.score == EXPECTED_SCORES["high_risk"]["respiratory"]
        
        coagulation = calculate_coagulation_score(patient_data.platelets.value)
        assert coagulation.score == EXPECTED_SCORES["high_risk"]["coagulation"]
        
        liver = calculate_liver_score(patient_data.bilirubin.value)
        assert liver.score == EXPECTED_SCORES["high_risk"]["liver"]
        
        cardiovascular = calculate_cardiovascular_score(
            patient_data.map_value.value,
            patient_data.vasopressor_doses
        )
        assert cardiovascular.score == EXPECTED_SCORES["high_risk"]["cardiovascular"]
        
        cns = calculate_cns_score(patient_data.gcs.value)
        assert cns.score == EXPECTED_SCORES["high_risk"]["cns"]
        
        renal = calculate_renal_score(
            patient_data.creatinine.value,
            patient_data.urine_output_24h.value
        )
        assert renal.score == EXPECTED_SCORES["high_risk"]["renal"]
        
        # Verify total
        total_score = (respiratory.score + coagulation.score + liver.score + 
                      cardiovascular.score + cns.score + renal.score)
        assert total_score == EXPECTED_SCORES["high_risk"]["total"]
    
    def test_critical_risk_patient_individual_scores(self):
        """Test individual organ scores for critical risk patient"""
        patient_data = create_critical_risk_patient_data()
        
        # Test each organ system score
        respiratory = calculate_respiratory_score(
            patient_data.pao2.value,
            patient_data.fio2.value,
            patient_data.mechanical_ventilation
        )
        assert respiratory.score == EXPECTED_SCORES["critical_risk"]["respiratory"]
        
        coagulation = calculate_coagulation_score(patient_data.platelets.value)
        assert coagulation.score == EXPECTED_SCORES["critical_risk"]["coagulation"]
        
        liver = calculate_liver_score(patient_data.bilirubin.value)
        assert liver.score == EXPECTED_SCORES["critical_risk"]["liver"]
        
        cardiovascular = calculate_cardiovascular_score(
            patient_data.map_value.value,
            patient_data.vasopressor_doses
        )
        assert cardiovascular.score == EXPECTED_SCORES["critical_risk"]["cardiovascular"]
        
        cns = calculate_cns_score(patient_data.gcs.value)
        assert cns.score == EXPECTED_SCORES["critical_risk"]["cns"]
        
        renal = calculate_renal_score(
            patient_data.creatinine.value,
            patient_data.urine_output_24h.value
        )
        assert renal.score == EXPECTED_SCORES["critical_risk"]["renal"]
        
        # Verify total
        total_score = (respiratory.score + coagulation.score + liver.score + 
                      cardiovascular.score + cns.score + renal.score)
        assert total_score == EXPECTED_SCORES["critical_risk"]["total"]


class TestEdgeCases:
    """Test edge cases and error handling for SOFA scoring"""
    
    def test_respiratory_score_missing_fio2(self):
        """Test respiratory score when FiO2 is missing (assumes room air)"""
        score = calculate_respiratory_score(pao2=100, fio2=None, on_ventilation=False)
        # PaO2/FiO2 = 100/0.21 ≈ 476, should be score 0
        assert score.score == 0
    
    def test_respiratory_score_room_air_assumption(self):
        """Test respiratory score with room air assumption"""
        score = calculate_respiratory_score(pao2=80, fio2=None, on_ventilation=False)
        # PaO2/FiO2 = 80/0.21 ≈ 381, should be score 1
        assert score.score == 1
    
    def test_coagulation_score_none_value(self):
        """Test coagulation score with None platelet value (uses default)"""
        score = calculate_coagulation_score(platelets=None)
        assert score.score == 0  # Default is 150, which is normal
    
    def test_liver_score_none_value(self):
        """Test liver score with None bilirubin value (uses default)"""
        score = calculate_liver_score(bilirubin=None)
        assert score.score == 0  # Default is 1.0, which is normal
    
    def test_cardiovascular_score_none_map(self):
        """Test cardiovascular score with None MAP value (uses default)"""
        score = calculate_cardiovascular_score(map_value=None, vasopressor_doses=VasopressorDoses())
        assert score.score == 0  # Default is 70, which is normal
    
    def test_cns_score_none_value(self):
        """Test CNS score with None GCS value (uses default)"""
        score = calculate_cns_score(gcs=None)
        assert score.score == 0  # Default is 15, which is normal
    
    def test_renal_score_none_values(self):
        """Test renal score with None values (uses defaults)"""
        score = calculate_renal_score(creatinine=None, urine_output_24h=None)
        assert score.score == 0  # Defaults are normal values
    
    def test_boundary_values_respiratory(self):
        """Test boundary values for respiratory scoring"""
        # Test exact boundary values
        score_400 = calculate_respiratory_score(pao2=400, fio2=1.0, on_ventilation=False)
        assert score_400.score == 0
        
        score_399 = calculate_respiratory_score(pao2=399, fio2=1.0, on_ventilation=False)
        assert score_399.score == 1
        
        score_300 = calculate_respiratory_score(pao2=300, fio2=1.0, on_ventilation=False)
        assert score_300.score == 1
        
        score_299 = calculate_respiratory_score(pao2=299, fio2=1.0, on_ventilation=False)
        assert score_299.score == 2
    
    def test_boundary_values_coagulation(self):
        """Test boundary values for coagulation scoring"""
        # Test exact boundary values
        assert calculate_coagulation_score(platelets=150).score == 0
        assert calculate_coagulation_score(platelets=149).score == 1
        assert calculate_coagulation_score(platelets=100).score == 1
        assert calculate_coagulation_score(platelets=99).score == 2
        assert calculate_coagulation_score(platelets=50).score == 2
        assert calculate_coagulation_score(platelets=49).score == 3
        assert calculate_coagulation_score(platelets=20).score == 3
        assert calculate_coagulation_score(platelets=19).score == 4
    
    def test_vasopressor_combinations(self):
        """Test various vasopressor combinations"""
        # Low dose dopamine
        low_dopamine = VasopressorDoses(dopamine=3.0)
        score = calculate_cardiovascular_score(map_value=65, vasopressor_doses=low_dopamine)
        assert score.score == 2
        
        # Medium dose dopamine
        med_dopamine = VasopressorDoses(dopamine=10.0)
        score = calculate_cardiovascular_score(map_value=65, vasopressor_doses=med_dopamine)
        assert score.score == 3
        
        # High dose dopamine
        high_dopamine = VasopressorDoses(dopamine=20.0)
        score = calculate_cardiovascular_score(map_value=65, vasopressor_doses=high_dopamine)
        assert score.score == 4
        
        # High dose epinephrine
        high_epi = VasopressorDoses(epinephrine=0.2)
        score = calculate_cardiovascular_score(map_value=65, vasopressor_doses=high_epi)
        assert score.score == 4


@pytest.mark.parametrize("patient_type,expected_total", [
    ("medium_risk", 10),
    ("high_risk", 17), 
    ("critical_risk", 24)
])
def test_patient_total_scores(patient_type, expected_total):
    """Parameterized test for patient total SOFA scores"""
    if patient_type == "medium_risk":
        patient_data = create_medium_risk_patient_data()
    elif patient_type == "high_risk":
        patient_data = create_high_risk_patient_data()
    else:  # critical_risk
        patient_data = create_critical_risk_patient_data()
    
    # Calculate all individual scores
    respiratory = calculate_respiratory_score(
        patient_data.pao2.value, patient_data.fio2.value, patient_data.mechanical_ventilation
    )
    coagulation = calculate_coagulation_score(patient_data.platelets.value)
    liver = calculate_liver_score(patient_data.bilirubin.value)
    cardiovascular = calculate_cardiovascular_score(
        patient_data.map_value.value, patient_data.vasopressor_doses
    )
    cns = calculate_cns_score(patient_data.gcs.value)
    renal = calculate_renal_score(
        patient_data.creatinine.value, patient_data.urine_output_24h.value
    )
    
    total_score = (respiratory.score + coagulation.score + liver.score + 
                  cardiovascular.score + cns.score + renal.score)
    
    assert total_score == expected_total