"""
SOFA Score Integration Tests

Tests that demonstrate the complete SOFA scoring pipeline from parameter
collection through final score calculation using the patient scenario data.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.utils.sofa_scoring import calculate_total_sofa, collect_sofa_parameters
from app.models.sofa import SofaParameters, SofaScoreResult
from tests.fixtures.sofa_test_data import (
    create_medium_risk_patient_data,
    create_high_risk_patient_data,
    create_critical_risk_patient_data,
    EXPECTED_SCORES
)


class TestSofaScoreIntegration:
    """Integration tests for complete SOFA scoring pipeline"""
    
    @pytest.fixture
    def mock_fhir_client(self):
        """Mock FHIR client for integration testing"""
        client = AsyncMock()
        client._make_request = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_medium_risk_patient_complete_scoring(self, mock_fhir_client):
        """Test complete SOFA scoring for medium risk patient"""
        patient_data = create_medium_risk_patient_data()
        
        # Mock the parameter collection to return our test data
        with patch('app.utils.sofa_scoring.collect_sofa_parameters') as mock_collect:
            mock_collect.return_value = patient_data
            
            # Calculate SOFA score
            result = await calculate_total_sofa(
                patient_id=patient_data.patient_id,
                fhir_client=mock_fhir_client,
                timestamp=patient_data.timestamp
            )
            
            # Verify result structure
            assert isinstance(result, SofaScoreResult)
            assert result.patient_id == patient_data.patient_id
            assert result.timestamp == patient_data.timestamp
            
            # Verify individual organ scores
            assert result.respiratory_score.score == EXPECTED_SCORES["medium_risk"]["respiratory"]
            assert result.coagulation_score.score == EXPECTED_SCORES["medium_risk"]["coagulation"]
            assert result.liver_score.score == EXPECTED_SCORES["medium_risk"]["liver"]
            assert result.cardiovascular_score.score == EXPECTED_SCORES["medium_risk"]["cardiovascular"]
            assert result.cns_score.score == EXPECTED_SCORES["medium_risk"]["cns"]
            assert result.renal_score.score == EXPECTED_SCORES["medium_risk"]["renal"]
            
            # Verify total score
            assert result.total_score == EXPECTED_SCORES["medium_risk"]["total"]
            
            # Verify organ system names
            assert result.respiratory_score.organ_system == "Respiratory"
            assert result.coagulation_score.organ_system == "Coagulation"
            assert result.liver_score.organ_system == "Liver"
            assert result.cardiovascular_score.organ_system == "Cardiovascular"
            assert result.cns_score.organ_system == "Central Nervous System"
            assert result.renal_score.organ_system == "Renal"
    
    @pytest.mark.asyncio
    async def test_high_risk_patient_complete_scoring(self, mock_fhir_client):
        """Test complete SOFA scoring for high risk patient"""
        patient_data = create_high_risk_patient_data()
        
        with patch('app.utils.sofa_scoring.collect_sofa_parameters') as mock_collect:
            mock_collect.return_value = patient_data
            
            result = await calculate_total_sofa(
                patient_id=patient_data.patient_id,
                fhir_client=mock_fhir_client,
                timestamp=patient_data.timestamp
            )
            
            # Verify high risk scoring
            assert result.total_score == EXPECTED_SCORES["high_risk"]["total"]
            assert result.respiratory_score.score == EXPECTED_SCORES["high_risk"]["respiratory"]
            assert result.coagulation_score.score == EXPECTED_SCORES["high_risk"]["coagulation"]
            assert result.liver_score.score == EXPECTED_SCORES["high_risk"]["liver"]
            assert result.cardiovascular_score.score == EXPECTED_SCORES["high_risk"]["cardiovascular"]
            assert result.cns_score.score == EXPECTED_SCORES["high_risk"]["cns"]
            assert result.renal_score.score == EXPECTED_SCORES["high_risk"]["renal"]
            
            # Verify interpretations contain expected clinical details
            assert "mechanical ventilation" in result.respiratory_score.interpretation
            assert "8.0" in result.cardiovascular_score.interpretation  # Dopamine dose
    
    @pytest.mark.asyncio
    async def test_critical_risk_patient_complete_scoring(self, mock_fhir_client):
        """Test complete SOFA scoring for critical risk patient"""
        patient_data = create_critical_risk_patient_data()
        
        with patch('app.utils.sofa_scoring.collect_sofa_parameters') as mock_collect:
            mock_collect.return_value = patient_data
            
            result = await calculate_total_sofa(
                patient_id=patient_data.patient_id,
                fhir_client=mock_fhir_client,
                timestamp=patient_data.timestamp
            )
            
            # Verify maximum SOFA scoring
            assert result.total_score == EXPECTED_SCORES["critical_risk"]["total"]
            assert result.total_score == 24  # Maximum possible SOFA score
            
            # Verify all organ systems have maximum scores
            assert result.respiratory_score.score == 4
            assert result.coagulation_score.score == 4
            assert result.liver_score.score == 4
            assert result.cardiovascular_score.score == 4
            assert result.cns_score.score == 4
            assert result.renal_score.score == 4
            
            # Verify critical interpretations
            assert "mechanical ventilation" in result.respiratory_score.interpretation
            assert "High-dose" in result.cardiovascular_score.interpretation
    
    @pytest.mark.asyncio
    async def test_sofa_scoring_with_data_reliability(self, mock_fhir_client):
        """Test SOFA scoring includes data reliability metrics"""
        patient_data = create_medium_risk_patient_data()
        
        # Set some parameters as estimated to test reliability scoring
        patient_data.platelets.is_estimated = True
        patient_data.gcs.is_estimated = True
        
        with patch('app.utils.sofa_scoring.collect_sofa_parameters') as mock_collect:
            mock_collect.return_value = patient_data
            
            result = await calculate_total_sofa(
                patient_id=patient_data.patient_id,
                fhir_client=mock_fhir_client,
                timestamp=patient_data.timestamp
            )
            
            # Verify reliability metrics are included
            assert hasattr(result, 'data_reliability_score')
            assert hasattr(result, 'estimated_parameters_count')
            assert hasattr(result, 'missing_parameters')
            
            # Verify estimated parameters are counted
            assert result.estimated_parameters_count == 2  # platelets and gcs
            assert result.data_reliability_score < 1.0  # Should be less than perfect
    
    def test_patient_data_fixture_completeness(self):
        """Test that patient data fixtures contain all required parameters"""
        test_patients = [
            create_medium_risk_patient_data(),
            create_high_risk_patient_data(),
            create_critical_risk_patient_data()
        ]
        
        for patient_data in test_patients:
            # Verify all critical parameters are present
            assert patient_data.pao2_fio2_ratio.value is not None
            assert patient_data.platelets.value is not None
            assert patient_data.bilirubin.value is not None
            assert patient_data.map_value.value is not None
            assert patient_data.gcs.value is not None
            assert patient_data.creatinine.value is not None
            assert patient_data.urine_output_24h.value is not None
            
            # Verify timestamps are set
            assert patient_data.timestamp is not None
            assert patient_data.platelets.timestamp is not None
            assert patient_data.bilirubin.timestamp is not None
            
            # Verify patient ID is set
            assert patient_data.patient_id is not None
            assert len(patient_data.patient_id) > 0
    
    @pytest.mark.parametrize("patient_func,expected_total,risk_level", [
        (create_medium_risk_patient_data, 10, "medium"),
        (create_high_risk_patient_data, 17, "high"), 
        (create_critical_risk_patient_data, 24, "critical")
    ])
    @pytest.mark.asyncio
    async def test_parametrized_sofa_calculations(self, mock_fhir_client, patient_func, expected_total, risk_level):
        """Parametrized test for all patient risk levels"""
        patient_data = patient_func()
        
        with patch('app.utils.sofa_scoring.collect_sofa_parameters') as mock_collect:
            mock_collect.return_value = patient_data
            
            result = await calculate_total_sofa(
                patient_id=patient_data.patient_id,
                fhir_client=mock_fhir_client,
                timestamp=patient_data.timestamp
            )
            
            assert result.total_score == expected_total
            assert result.patient_id == patient_data.patient_id
            
            # Verify all scores are within valid range (0-4 per organ)
            organ_scores = [
                result.respiratory_score.score,
                result.coagulation_score.score,
                result.liver_score.score,
                result.cardiovascular_score.score,
                result.cns_score.score,
                result.renal_score.score
            ]
            
            for score in organ_scores:
                assert 0 <= score <= 4, f"Organ score {score} out of valid range 0-4"
            
            # Verify total is sum of individual scores
            assert result.total_score == sum(organ_scores)