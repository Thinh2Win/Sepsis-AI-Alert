"""
Integration tests for vitals endpoints.
"""

import pytest
from fastapi import status
from datetime import datetime
from unittest.mock import AsyncMock

from app.models.vitals import VitalSignsResponse, VitalSignsLatestResponse, VitalSignsTimeSeries, VitalSignsData, VitalSign, BloodPressure
from app.core.exceptions import FHIRException


class TestVitalsEndpoints:
    """Test vitals-related API endpoints."""

    def test_get_vitals_success(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test successful vitals retrieval."""
        # Arrange
        expected_vitals_data = VitalSignsResponse(
            patient_id=sample_patient_id,
            vital_signs=VitalSignsTimeSeries(
                heart_rate=[
                    VitalSign(
                        value=72.0,
                        unit="beats/min",
                        timestamp=datetime(2023, 1, 1, 12, 0, 0),
                        loinc_code="8867-4",
                        display_name="Heart rate"
                    )
                ],
                blood_pressure=[
                    BloodPressure(
                        systolic=VitalSign(
                            value=120.0,
                            unit="mmHg",
                            timestamp=datetime(2023, 1, 1, 12, 0, 0),
                            loinc_code="8480-6",
                            display_name="Systolic blood pressure"
                        ),
                        diastolic=VitalSign(
                            value=80.0,
                            unit="mmHg",
                            timestamp=datetime(2023, 1, 1, 12, 0, 0),
                            loinc_code="8462-4",
                            display_name="Diastolic blood pressure"
                        )
                    )
                ]
            ),
            total_entries=3,
            date_range=None
        )
        
        mock_fhir_client_dependency.get_vitals.return_value = expected_vitals_data
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/vitals")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["total_entries"] == 3
        assert "vital_signs" in data
        assert len(data["vital_signs"]["heart_rate"]) == 1
        assert data["vital_signs"]["heart_rate"][0]["value"] == 72.0
        
        mock_fhir_client_dependency.get_vitals.assert_called_once_with(
            sample_patient_id, None, None, None
        )

    def test_get_vitals_with_date_range(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test vitals retrieval with date range parameters."""
        # Arrange
        start_date = "2023-01-01T00:00:00"
        end_date = "2023-01-02T23:59:59"
        
        expected_vitals_data = VitalSignsResponse(
            patient_id=sample_patient_id,
            vital_signs=VitalSignsTimeSeries(),
            total_entries=0,
            date_range={"start": datetime(2023, 1, 1), "end": datetime(2023, 1, 2, 23, 59, 59)}
        )
        
        mock_fhir_client_dependency.get_vitals.return_value = expected_vitals_data
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/vitals",
            params={"start_date": start_date, "end_date": end_date}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["date_range"] is not None
        
        # Verify the FHIR client was called with parsed datetime objects
        call_args = mock_fhir_client_dependency.get_vitals.call_args[0]
        assert isinstance(call_args[1], datetime)  # start_date
        assert isinstance(call_args[2], datetime)  # end_date

    def test_get_vitals_with_vital_type_filter(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test vitals retrieval with specific vital type filter."""
        # Arrange
        vital_type = "HR"  # Heart Rate only
        
        expected_vitals_data = VitalSignsResponse(
            patient_id=sample_patient_id,
            vital_signs=VitalSignsTimeSeries(
                heart_rate=[
                    VitalSign(
                        value=75.0,
                        unit="beats/min",
                        timestamp=datetime(2023, 1, 1, 12, 0, 0),
                        loinc_code="8867-4",
                        display_name="Heart rate"
                    )
                ]
            ),
            total_entries=1,
            date_range=None
        )
        
        mock_fhir_client_dependency.get_vitals.return_value = expected_vitals_data
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/vitals",
            params={"vital_type": vital_type}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert len(data["vital_signs"]["heart_rate"]) == 1
        assert len(data["vital_signs"]["blood_pressure"]) == 0  # Should be empty
        
        mock_fhir_client_dependency.get_vitals.assert_called_once_with(
            sample_patient_id, None, None, vital_type
        )

    def test_get_vitals_patient_not_found(self, test_client, mock_fhir_client_dependency):
        """Test vitals retrieval for non-existent patient."""
        # Arrange
        patient_id = "nonexistent-patient"
        mock_fhir_client_dependency.get_vitals.side_effect = FHIRException(404, "Patient not found")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{patient_id}/vitals")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "Patient not found" in data["message"]

    def test_get_vitals_access_denied(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test vitals retrieval with access denied."""
        # Arrange
        mock_fhir_client_dependency.get_vitals.side_effect = FHIRException(403, "Access denied to patient vitals")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/vitals")
        
        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "Access denied" in data["message"]

    def test_get_vitals_invalid_date_format(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test vitals retrieval with invalid date format."""
        # Arrange
        invalid_start_date = "invalid-date"
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/vitals",
            params={"start_date": invalid_start_date}
        )
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    def test_get_vitals_all_vital_types(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test vitals retrieval for all vital sign types."""
        # Arrange
        expected_vitals_data = VitalSignsResponse(
            patient_id=sample_patient_id,
            vital_signs=VitalSignsTimeSeries(
                heart_rate=[VitalSign(value=72.0, unit="beats/min", timestamp=datetime.now(), loinc_code="8867-4")],
                respiratory_rate=[VitalSign(value=16.0, unit="breaths/min", timestamp=datetime.now(), loinc_code="9279-1")],
                body_temperature=[VitalSign(value=98.6, unit="°F", timestamp=datetime.now(), loinc_code="8310-5")],
                oxygen_saturation=[VitalSign(value=98.0, unit="%", timestamp=datetime.now(), loinc_code="2708-6")],
                glasgow_coma_score=[VitalSign(value=15.0, unit="", timestamp=datetime.now(), loinc_code="9269-2")],
                blood_pressure=[
                    BloodPressure(
                        systolic=VitalSign(value=120.0, unit="mmHg", timestamp=datetime.now(), loinc_code="8480-6"),
                        diastolic=VitalSign(value=80.0, unit="mmHg", timestamp=datetime.now(), loinc_code="8462-4")
                    )
                ]
            ),
            total_entries=6,
            date_range=None
        )
        
        mock_fhir_client_dependency.get_vitals.return_value = expected_vitals_data
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/vitals")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_entries"] == 6
        
        # Verify all vital sign types are present
        vital_signs = data["vital_signs"]
        assert len(vital_signs["heart_rate"]) == 1
        assert len(vital_signs["respiratory_rate"]) == 1
        assert len(vital_signs["body_temperature"]) == 1
        assert len(vital_signs["oxygen_saturation"]) == 1
        assert len(vital_signs["glasgow_coma_score"]) == 1
        assert len(vital_signs["blood_pressure"]) == 1


class TestLatestVitalsEndpoint:
    """Test latest vitals endpoint."""

    def test_get_latest_vitals_success(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test successful latest vitals retrieval."""
        # Arrange
        expected_latest_vitals = VitalSignsLatestResponse(
            patient_id=sample_patient_id,
            vital_signs=VitalSignsData(
                heart_rate=VitalSign(
                    value=75.0,
                    unit="beats/min",
                    timestamp=datetime(2023, 1, 1, 12, 0, 0),
                    loinc_code="8867-4",
                    display_name="Heart rate"
                ),
                blood_pressure=BloodPressure(
                    systolic=VitalSign(
                        value=125.0,
                        unit="mmHg",
                        timestamp=datetime(2023, 1, 1, 12, 0, 0),
                        loinc_code="8480-6",
                        display_name="Systolic blood pressure"
                    ),
                    diastolic=VitalSign(
                        value=82.0,
                        unit="mmHg",
                        timestamp=datetime(2023, 1, 1, 12, 0, 0),
                        loinc_code="8462-4",
                        display_name="Diastolic blood pressure"
                    )
                )
            ),
            last_updated=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        mock_fhir_client_dependency.get_latest_vitals.return_value = expected_latest_vitals
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/vitals/latest")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["vital_signs"]["heart_rate"]["value"] == 75.0
        assert data["vital_signs"]["blood_pressure"]["systolic"]["value"] == 125.0
        assert data["vital_signs"]["blood_pressure"]["diastolic"]["value"] == 82.0
        
        mock_fhir_client_dependency.get_latest_vitals.assert_called_once_with(sample_patient_id)

    def test_get_latest_vitals_partial_data(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test latest vitals retrieval with partial data (some vitals missing)."""
        # Arrange
        expected_latest_vitals = VitalSignsLatestResponse(
            patient_id=sample_patient_id,
            vital_signs=VitalSignsData(
                heart_rate=VitalSign(
                    value=80.0,
                    unit="beats/min",
                    timestamp=datetime(2023, 1, 1, 12, 0, 0),
                    loinc_code="8867-4"
                ),
                # Other vitals are None/missing
                blood_pressure=None,
                body_temperature=None,
                respiratory_rate=None,
                oxygen_saturation=None,
                glasgow_coma_score=None
            ),
            last_updated=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        mock_fhir_client_dependency.get_latest_vitals.return_value = expected_latest_vitals
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/vitals/latest")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["vital_signs"]["heart_rate"]["value"] == 80.0
        assert data["vital_signs"]["blood_pressure"] is None
        assert data["vital_signs"]["body_temperature"] is None

    def test_get_latest_vitals_no_data(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test latest vitals retrieval with no vital signs data."""
        # Arrange
        expected_latest_vitals = VitalSignsLatestResponse(
            patient_id=sample_patient_id,
            vital_signs=VitalSignsData(),  # All vitals are None
            last_updated=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        mock_fhir_client_dependency.get_latest_vitals.return_value = expected_latest_vitals
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/vitals/latest")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["vital_signs"]["heart_rate"] is None
        assert data["vital_signs"]["blood_pressure"] is None

    def test_get_latest_vitals_patient_not_found(self, test_client, mock_fhir_client_dependency):
        """Test latest vitals retrieval for non-existent patient."""
        # Arrange
        patient_id = "nonexistent-patient"
        mock_fhir_client_dependency.get_latest_vitals.side_effect = FHIRException(404, "Patient not found")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{patient_id}/vitals/latest")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "Patient not found" in data["message"]

    def test_get_latest_vitals_server_error(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test latest vitals retrieval with server error."""
        # Arrange
        mock_fhir_client_dependency.get_latest_vitals.side_effect = FHIRException(500, "FHIR server unavailable")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/vitals/latest")
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "FHIR server unavailable" in data["message"]

    def test_get_latest_vitals_complete_data(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test latest vitals retrieval with complete vital signs data."""
        # Arrange
        expected_latest_vitals = VitalSignsLatestResponse(
            patient_id=sample_patient_id,
            vital_signs=VitalSignsData(
                heart_rate=VitalSign(value=72.0, unit="beats/min", timestamp=datetime.now(), loinc_code="8867-4"),
                respiratory_rate=VitalSign(value=16.0, unit="breaths/min", timestamp=datetime.now(), loinc_code="9279-1"),
                body_temperature=VitalSign(value=98.6, unit="°F", timestamp=datetime.now(), loinc_code="8310-5"),
                oxygen_saturation=VitalSign(value=98.0, unit="%", timestamp=datetime.now(), loinc_code="2708-6"),
                glasgow_coma_score=VitalSign(value=15.0, unit="", timestamp=datetime.now(), loinc_code="9269-2"),
                blood_pressure=BloodPressure(
                    systolic=VitalSign(value=120.0, unit="mmHg", timestamp=datetime.now(), loinc_code="8480-6"),
                    diastolic=VitalSign(value=80.0, unit="mmHg", timestamp=datetime.now(), loinc_code="8462-4")
                )
            ),
            last_updated=datetime.now()
        )
        
        mock_fhir_client_dependency.get_latest_vitals.return_value = expected_latest_vitals
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/vitals/latest")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify all vital signs are present
        vital_signs = data["vital_signs"]
        assert vital_signs["heart_rate"]["value"] == 72.0
        assert vital_signs["respiratory_rate"]["value"] == 16.0
        assert vital_signs["body_temperature"]["value"] == 98.6
        assert vital_signs["oxygen_saturation"]["value"] == 98.0
        assert vital_signs["glasgow_coma_score"]["value"] == 15.0
        assert vital_signs["blood_pressure"]["systolic"]["value"] == 120.0
        assert vital_signs["blood_pressure"]["diastolic"]["value"] == 80.0