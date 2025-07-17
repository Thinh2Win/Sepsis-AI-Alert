"""
Integration tests for clinical endpoints.
"""

import pytest
from fastapi import status
from datetime import datetime
from unittest.mock import AsyncMock

from app.models.clinical import (
    EncounterResponse, ConditionsResponse, MedicationsResponse, FluidBalanceResponse,
    Encounter, Condition, Medication, FluidObservation
)
from app.core.exceptions import FHIRException
from tests.fixtures.fhir_responses import encounter_response, condition_response


class TestEncounterEndpoint:
    """Test encounter endpoint."""

    def test_get_encounter_success(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test successful encounter retrieval."""
        # Arrange
        expected_encounter = EncounterResponse(
            patient_id=sample_patient_id,
            current_encounter=Encounter(
                id="encounter-123",
                status="in-progress",
                class_={"code": "IMP", "display": "inpatient"},
                period={"start": datetime(2023, 1, 1, 8, 0, 0), "end": None},
                location=[{"location": "ICU Room 101", "status": "active"}],
                admission_source="Emergency Department",
                discharge_disposition=None
            )
        )
        
        mock_fhir_client_dependency.get_encounter.return_value = expected_encounter
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/encounter")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["current_encounter"]["id"] == "encounter-123"
        assert data["current_encounter"]["status"] == "in-progress"
        assert data["current_encounter"]["admission_source"] == "Emergency Department"
        
        mock_fhir_client_dependency.get_encounter.assert_called_once_with(sample_patient_id)

    def test_get_encounter_no_active_encounter(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test encounter retrieval with no active encounter."""
        # Arrange
        expected_encounter = EncounterResponse(
            patient_id=sample_patient_id,
            current_encounter=None
        )
        
        mock_fhir_client_dependency.get_encounter.return_value = expected_encounter
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/encounter")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["current_encounter"] is None

    def test_get_encounter_patient_not_found(self, test_client, mock_fhir_client_dependency):
        """Test encounter retrieval for non-existent patient."""
        # Arrange
        patient_id = "nonexistent-patient"
        mock_fhir_client_dependency.get_encounter.side_effect = FHIRException(404, "Patient not found")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{patient_id}/encounter")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "Patient not found" in data["message"]

    def test_get_encounter_access_denied(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test encounter retrieval with access denied."""
        # Arrange
        mock_fhir_client_dependency.get_encounter.side_effect = FHIRException(403, "Access denied to encounter data")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/encounter")
        
        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "Access denied" in data["message"]


class TestConditionsEndpoint:
    """Test conditions endpoint."""

    def test_get_conditions_success(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test successful conditions retrieval."""
        # Arrange
        expected_conditions = ConditionsResponse(
            patient_id=sample_patient_id,
            active_conditions=[
                Condition(
                    id="condition-sepsis-123",
                    clinical_status="active",
                    verification_status="confirmed",
                    code="A41.9",
                    code_text="Sepsis, unspecified organism",
                    onset_date_time=datetime(2023, 1, 1, 10, 0, 0),
                    is_active=True,
                    is_resolved=False
                )
            ],
            resolved_conditions=[
                Condition(
                    id="condition-pneumonia-456",
                    clinical_status="resolved",
                    verification_status="confirmed",
                    code="J18.9",
                    code_text="Pneumonia, unspecified organism",
                    onset_date_time=datetime(2022, 12, 15, 14, 0, 0),
                    abatement_date_time=datetime(2023, 1, 5, 10, 0, 0),
                    is_active=False,
                    is_resolved=True
                )
            ],
            total_conditions=2
        )
        
        mock_fhir_client_dependency.get_conditions.return_value = expected_conditions
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/conditions")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["total_conditions"] == 2
        assert len(data["active_conditions"]) == 1
        assert len(data["resolved_conditions"]) == 1
        
        # Verify active condition details
        active_condition = data["active_conditions"][0]
        assert active_condition["code"] == "A41.9"
        assert active_condition["code_text"] == "Sepsis, unspecified organism"
        assert active_condition["clinical_status"] == "active"
        
        # Verify resolved condition details
        resolved_condition = data["resolved_conditions"][0]
        assert resolved_condition["code"] == "J18.9"
        assert resolved_condition["clinical_status"] == "resolved"
        
        mock_fhir_client_dependency.get_conditions.assert_called_once_with(sample_patient_id)

    def test_get_conditions_no_conditions(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test conditions retrieval with no conditions."""
        # Arrange
        expected_conditions = ConditionsResponse(
            patient_id=sample_patient_id,
            active_conditions=[],
            resolved_conditions=[],
            total_conditions=0
        )
        
        mock_fhir_client_dependency.get_conditions.return_value = expected_conditions
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/conditions")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["total_conditions"] == 0
        assert len(data["active_conditions"]) == 0
        assert len(data["resolved_conditions"]) == 0

    def test_get_conditions_patient_not_found(self, test_client, mock_fhir_client_dependency):
        """Test conditions retrieval for non-existent patient."""
        # Arrange
        patient_id = "nonexistent-patient"
        mock_fhir_client_dependency.get_conditions.side_effect = FHIRException(404, "Patient not found")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{patient_id}/conditions")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "Patient not found" in data["message"]


class TestMedicationsEndpoint:
    """Test medications endpoint."""

    def test_get_medications_all(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test successful medications retrieval for all medications."""
        # Arrange
        expected_medications = MedicationsResponse(
            patient_id=sample_patient_id,
            active_medications=[
                Medication(
                    id="med-antibiotic-123",
                    status="active",
                    medication_name="Ceftriaxone",
                    is_antibiotic=True,
                    is_vasopressor=False
                ),
                Medication(
                    id="med-vasopressor-456",
                    status="active",
                    medication_name="Norepinephrine",
                    is_antibiotic=False,
                    is_vasopressor=True
                ),
                Medication(
                    id="med-other-789",
                    status="active",
                    medication_name="Acetaminophen",
                    is_antibiotic=False,
                    is_vasopressor=False
                )
            ],
            antibiotics=[
                Medication(
                    id="med-antibiotic-123",
                    status="active",
                    medication_name="Ceftriaxone",
                    is_antibiotic=True,
                    is_vasopressor=False
                )
            ],
            vasopressors=[
                Medication(
                    id="med-vasopressor-456",
                    status="active",
                    medication_name="Norepinephrine",
                    is_antibiotic=False,
                    is_vasopressor=True
                )
            ],
            total_medications=3
        )
        
        mock_fhir_client_dependency.get_medications.return_value = expected_medications
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/medications")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["total_medications"] == 3
        assert len(data["active_medications"]) == 3
        assert len(data["antibiotics"]) == 1
        assert len(data["vasopressors"]) == 1
        
        # Verify medication details
        assert data["antibiotics"][0]["medication_name"] == "Ceftriaxone"
        assert data["vasopressors"][0]["medication_name"] == "Norepinephrine"
        
        mock_fhir_client_dependency.get_medications.assert_called_once_with(
            sample_patient_id, False, False
        )

    def test_get_medications_antibiotics_only(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test medications retrieval filtered for antibiotics only."""
        # Arrange
        expected_medications = MedicationsResponse(
            patient_id=sample_patient_id,
            active_medications=[
                Medication(
                    id="med-antibiotic-123",
                    status="active",
                    medication_name="Ceftriaxone",
                    is_antibiotic=True,
                    is_vasopressor=False
                ),
                Medication(
                    id="med-antibiotic-456",
                    status="active",
                    medication_name="Vancomycin",
                    is_antibiotic=True,
                    is_vasopressor=False
                )
            ],
            antibiotics=[
                Medication(id="med-antibiotic-123", medication_name="Ceftriaxone", is_antibiotic=True),
                Medication(id="med-antibiotic-456", medication_name="Vancomycin", is_antibiotic=True)
            ],
            vasopressors=[],
            total_medications=2
        )
        
        mock_fhir_client_dependency.get_medications.return_value = expected_medications
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/medications",
            params={"medication_type": "ANTIBIOTICS"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_medications"] == 2
        assert len(data["antibiotics"]) == 2
        assert len(data["vasopressors"]) == 0
        
        mock_fhir_client_dependency.get_medications.assert_called_once_with(
            sample_patient_id, True, False
        )

    def test_get_medications_vasopressors_only(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test medications retrieval filtered for vasopressors only."""
        # Arrange
        expected_medications = MedicationsResponse(
            patient_id=sample_patient_id,
            active_medications=[
                Medication(
                    id="med-vasopressor-123",
                    status="active",
                    medication_name="Norepinephrine",
                    is_antibiotic=False,
                    is_vasopressor=True
                )
            ],
            antibiotics=[],
            vasopressors=[
                Medication(id="med-vasopressor-123", medication_name="Norepinephrine", is_vasopressor=True)
            ],
            total_medications=1
        )
        
        mock_fhir_client_dependency.get_medications.return_value = expected_medications
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/medications",
            params={"medication_type": "VASOPRESSORS"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_medications"] == 1
        assert len(data["antibiotics"]) == 0
        assert len(data["vasopressors"]) == 1
        
        mock_fhir_client_dependency.get_medications.assert_called_once_with(
            sample_patient_id, False, True
        )

    def test_get_medications_invalid_type(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test medications retrieval with invalid medication type."""
        # Arrange
        expected_medications = MedicationsResponse(
            patient_id=sample_patient_id,
            active_medications=[],
            antibiotics=[],
            vasopressors=[],
            total_medications=0
        )
        
        mock_fhir_client_dependency.get_medications.return_value = expected_medications
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/medications",
            params={"medication_type": "INVALID_TYPE"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        # Invalid type should default to all medications (neither antibiotics_only nor vasopressors_only)
        mock_fhir_client_dependency.get_medications.assert_called_once_with(
            sample_patient_id, False, False
        )

    def test_get_medications_no_medications(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test medications retrieval with no medications."""
        # Arrange
        expected_medications = MedicationsResponse(
            patient_id=sample_patient_id,
            active_medications=[],
            antibiotics=[],
            vasopressors=[],
            total_medications=0
        )
        
        mock_fhir_client_dependency.get_medications.return_value = expected_medications
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/medications")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_medications"] == 0
        assert len(data["active_medications"]) == 0


class TestFluidBalanceEndpoint:
    """Test fluid balance endpoint."""

    def test_get_fluid_balance_success(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test successful fluid balance retrieval."""
        # Arrange
        expected_fluid_balance = FluidBalanceResponse(
            patient_id=sample_patient_id,
            fluid_intake=[
                FluidObservation(
                    value=1500.0,
                    unit="mL",
                    timestamp=datetime(2023, 1, 1, 12, 0, 0),
                    category="intake"
                ),
                FluidObservation(
                    value=500.0,
                    unit="mL",
                    timestamp=datetime(2023, 1, 1, 18, 0, 0),
                    category="intake"
                )
            ],
            urine_output=[
                FluidObservation(
                    value=800.0,
                    unit="mL",
                    timestamp=datetime(2023, 1, 1, 12, 0, 0),
                    category="urine_output"
                ),
                FluidObservation(
                    value=400.0,
                    unit="mL",
                    timestamp=datetime(2023, 1, 1, 18, 0, 0),
                    category="urine_output"
                )
            ],
            fluid_balance=800.0  # 2000 intake - 1200 output
        )
        
        mock_fhir_client_dependency.get_fluid_balance.return_value = expected_fluid_balance
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/fluid-balance")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert len(data["fluid_intake"]) == 2
        assert len(data["urine_output"]) == 2
        assert data["fluid_balance"] == 800.0
        
        # Verify fluid intake details
        assert data["fluid_intake"][0]["value"] == 1500.0
        assert data["fluid_intake"][0]["category"] == "intake"
        
        # Verify urine output details
        assert data["urine_output"][0]["value"] == 800.0
        assert data["urine_output"][0]["category"] == "urine_output"
        
        mock_fhir_client_dependency.get_fluid_balance.assert_called_once_with(
            sample_patient_id, None, None
        )

    def test_get_fluid_balance_with_date_range(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test fluid balance retrieval with date range."""
        # Arrange
        start_date = "2023-01-01T00:00:00"
        end_date = "2023-01-02T23:59:59"
        
        expected_fluid_balance = FluidBalanceResponse(
            patient_id=sample_patient_id,
            fluid_intake=[],
            urine_output=[],
            fluid_balance=0.0
        )
        
        mock_fhir_client_dependency.get_fluid_balance.return_value = expected_fluid_balance
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/fluid-balance",
            params={"start_date": start_date, "end_date": end_date}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        # Verify the FHIR client was called with parsed datetime objects
        call_args = mock_fhir_client_dependency.get_fluid_balance.call_args[0]
        assert isinstance(call_args[1], datetime)  # start_date
        assert isinstance(call_args[2], datetime)  # end_date

    def test_get_fluid_balance_no_data(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test fluid balance retrieval with no data."""
        # Arrange
        expected_fluid_balance = FluidBalanceResponse(
            patient_id=sample_patient_id,
            fluid_intake=[],
            urine_output=[],
            fluid_balance=None
        )
        
        mock_fhir_client_dependency.get_fluid_balance.return_value = expected_fluid_balance
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/fluid-balance")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["fluid_intake"]) == 0
        assert len(data["urine_output"]) == 0
        assert data["fluid_balance"] is None

    def test_get_fluid_balance_negative_balance(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test fluid balance retrieval with negative balance (more output than intake)."""
        # Arrange
        expected_fluid_balance = FluidBalanceResponse(
            patient_id=sample_patient_id,
            fluid_intake=[
                FluidObservation(value=500.0, unit="mL", timestamp=datetime.now(), category="intake")
            ],
            urine_output=[
                FluidObservation(value=800.0, unit="mL", timestamp=datetime.now(), category="urine_output")
            ],
            fluid_balance=-300.0  # 500 intake - 800 output
        )
        
        mock_fhir_client_dependency.get_fluid_balance.return_value = expected_fluid_balance
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/fluid-balance")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["fluid_balance"] == -300.0

    def test_get_fluid_balance_patient_not_found(self, test_client, mock_fhir_client_dependency):
        """Test fluid balance retrieval for non-existent patient."""
        # Arrange
        patient_id = "nonexistent-patient"
        mock_fhir_client_dependency.get_fluid_balance.side_effect = FHIRException(404, "Patient not found")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{patient_id}/fluid-balance")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "Patient not found" in data["message"]

    def test_get_fluid_balance_access_denied(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test fluid balance retrieval with access denied."""
        # Arrange
        mock_fhir_client_dependency.get_fluid_balance.side_effect = FHIRException(403, "Access denied to fluid balance data")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/fluid-balance")
        
        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "Access denied" in data["message"]

    def test_get_fluid_balance_invalid_date_format(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test fluid balance retrieval with invalid date format."""
        # Arrange
        invalid_start_date = "invalid-date"
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/fluid-balance",
            params={"start_date": invalid_start_date}
        )
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data