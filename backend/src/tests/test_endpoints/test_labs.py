"""
Integration tests for labs endpoints.
"""

import pytest
from fastapi import status
from datetime import datetime
from unittest.mock import AsyncMock

from app.models.labs import LabResultsResponse, CriticalLabsResponse, LabResultsData, LabValue, CBCResults, MetabolicPanel
from app.core.exceptions import FHIRException


class TestLabsEndpoints:
    """Test labs-related API endpoints."""

    def test_get_labs_success(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test successful labs retrieval."""
        # Arrange
        expected_labs_data = LabResultsResponse(
            patient_id=sample_patient_id,
            lab_results=LabResultsData(
                cbc=CBCResults(
                    white_blood_cell_count=LabValue(
                        value=8.5,
                        unit="10*3/uL",
                        timestamp=datetime(2023, 1, 1, 12, 0, 0),
                        loinc_code="6690-2",
                        display_name="Leukocytes [#/volume] in Blood"
                    ),
                    platelet_count=LabValue(
                        value=250.0,
                        unit="10*3/uL",
                        timestamp=datetime(2023, 1, 1, 12, 0, 0),
                        loinc_code="777-3",
                        display_name="Platelets [#/volume] in Blood"
                    )
                ),
                metabolic_panel=MetabolicPanel(
                    creatinine=LabValue(
                        value=1.0,
                        unit="mg/dL",
                        timestamp=datetime(2023, 1, 1, 12, 0, 0),
                        loinc_code="2160-0",
                        display_name="Creatinine [Mass/volume] in Serum"
                    )
                )
            ),
            total_entries=3,
            date_range=None
        )
        
        mock_fhir_client_dependency.get_labs.return_value = expected_labs_data
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["total_entries"] == 3
        assert "lab_results" in data
        assert data["lab_results"]["cbc"]["white_blood_cell_count"]["value"] == 8.5
        assert data["lab_results"]["cbc"]["platelet_count"]["value"] == 250.0
        
        mock_fhir_client_dependency.get_labs.assert_called_once_with(
            sample_patient_id, None, None, None
        )

    def test_get_labs_with_date_range(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test labs retrieval with date range parameters."""
        # Arrange
        start_date = "2023-01-01T00:00:00"
        end_date = "2023-01-02T23:59:59"
        
        expected_labs_data = LabResultsResponse(
            patient_id=sample_patient_id,
            lab_results=LabResultsData(),
            total_entries=0,
            date_range={"start": datetime(2023, 1, 1), "end": datetime(2023, 1, 2, 23, 59, 59)}
        )
        
        mock_fhir_client_dependency.get_labs.return_value = expected_labs_data
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs",
            params={"start_date": start_date, "end_date": end_date}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["date_range"] is not None
        
        # Verify the FHIR client was called with parsed datetime objects
        call_args = mock_fhir_client_dependency.get_labs.call_args[0]
        assert isinstance(call_args[1], datetime)  # start_date
        assert isinstance(call_args[2], datetime)  # end_date

    def test_get_labs_with_category_filter(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test labs retrieval with specific category filter."""
        # Arrange
        lab_category = "CBC"
        
        expected_labs_data = LabResultsResponse(
            patient_id=sample_patient_id,
            lab_results=LabResultsData(
                cbc=CBCResults(
                    white_blood_cell_count=LabValue(
                        value=9.2,
                        unit="10*3/uL",
                        timestamp=datetime(2023, 1, 1, 12, 0, 0),
                        loinc_code="6690-2"
                    )
                )
            ),
            total_entries=1,
            date_range=None
        )
        
        mock_fhir_client_dependency.get_labs.return_value = expected_labs_data
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs",
            params={"lab_category": lab_category}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert data["total_entries"] == 1
        assert data["lab_results"]["cbc"]["white_blood_cell_count"]["value"] == 9.2
        
        mock_fhir_client_dependency.get_labs.assert_called_once_with(
            sample_patient_id, None, None, lab_category
        )

    def test_get_labs_all_categories(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test labs retrieval for all lab categories."""
        # Arrange
        expected_labs_data = LabResultsResponse(
            patient_id=sample_patient_id,
            lab_results=LabResultsData(
                cbc=CBCResults(
                    white_blood_cell_count=LabValue(value=8.5, unit="10*3/uL", timestamp=datetime.now(), loinc_code="6690-2"),
                    platelet_count=LabValue(value=250.0, unit="10*3/uL", timestamp=datetime.now(), loinc_code="777-3")
                ),
                metabolic_panel=MetabolicPanel(
                    creatinine=LabValue(value=1.0, unit="mg/dL", timestamp=datetime.now(), loinc_code="2160-0"),
                    glucose=LabValue(value=95.0, unit="mg/dL", timestamp=datetime.now(), loinc_code="2345-7")
                )
            ),
            total_entries=4,
            date_range=None
        )
        
        mock_fhir_client_dependency.get_labs.return_value = expected_labs_data
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_entries"] == 4
        
        # Verify multiple categories are present
        lab_results = data["lab_results"]
        assert lab_results["cbc"]["white_blood_cell_count"]["value"] == 8.5
        assert lab_results["cbc"]["platelet_count"]["value"] == 250.0
        assert lab_results["metabolic_panel"]["creatinine"]["value"] == 1.0
        assert lab_results["metabolic_panel"]["glucose"]["value"] == 95.0

    def test_get_labs_patient_not_found(self, test_client, mock_fhir_client_dependency):
        """Test labs retrieval for non-existent patient."""
        # Arrange
        patient_id = "nonexistent-patient"
        mock_fhir_client_dependency.get_labs.side_effect = FHIRException(404, "Patient not found")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{patient_id}/labs")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "Patient not found" in data["message"]

    def test_get_labs_access_denied(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test labs retrieval with access denied."""
        # Arrange
        mock_fhir_client_dependency.get_labs.side_effect = FHIRException(403, "Access denied to patient labs")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs")
        
        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "Access denied" in data["message"]

    def test_get_labs_server_error(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test labs retrieval with server error."""
        # Arrange
        mock_fhir_client_dependency.get_labs.side_effect = FHIRException(500, "FHIR server unavailable")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs")
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "FHIR server unavailable" in data["message"]

    def test_get_labs_invalid_date_format(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test labs retrieval with invalid date format."""
        # Arrange
        invalid_start_date = "invalid-date"
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs",
            params={"start_date": invalid_start_date}
        )
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    def test_get_labs_invalid_category(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test labs retrieval with invalid category."""
        # Arrange
        invalid_category = "INVALID_CATEGORY"
        
        expected_labs_data = LabResultsResponse(
            patient_id=sample_patient_id,
            lab_results=LabResultsData(),  # Empty since invalid category
            total_entries=0,
            date_range=None
        )
        
        mock_fhir_client_dependency.get_labs.return_value = expected_labs_data
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs",
            params={"lab_category": invalid_category}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_entries"] == 0
        
        # The FHIR client should still be called (it handles invalid categories)
        mock_fhir_client_dependency.get_labs.assert_called_once_with(
            sample_patient_id, None, None, invalid_category
        )

    def test_get_labs_with_all_parameters(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test labs retrieval with all query parameters."""
        # Arrange
        start_date = "2023-01-01T00:00:00"
        end_date = "2023-01-02T23:59:59"
        lab_category = "METABOLIC"
        
        expected_labs_data = LabResultsResponse(
            patient_id=sample_patient_id,
            lab_results=LabResultsData(),
            total_entries=0,
            date_range={"start": datetime(2023, 1, 1), "end": datetime(2023, 1, 2, 23, 59, 59)}
        )
        
        mock_fhir_client_dependency.get_labs.return_value = expected_labs_data
        
        # Act
        response = test_client.get(
            f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs",
            params={
                "start_date": start_date,
                "end_date": end_date,
                "lab_category": lab_category
            }
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        # Verify all parameters were passed correctly
        call_args = mock_fhir_client_dependency.get_labs.call_args[0]
        assert call_args[0] == sample_patient_id
        assert isinstance(call_args[1], datetime)  # start_date
        assert isinstance(call_args[2], datetime)  # end_date
        assert call_args[3] == lab_category


class TestCriticalLabsEndpoint:
    """Test critical labs endpoint."""

    def test_get_critical_labs_success(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test successful critical labs retrieval."""
        # Arrange
        expected_critical_labs = CriticalLabsResponse(
            patient_id=sample_patient_id,
            critical_values=[
                LabValue(
                    value=15.2,
                    unit="10*3/uL",
                    timestamp=datetime(2023, 1, 1, 12, 0, 0),
                    loinc_code="6690-2",
                    display_name="Leukocytes [#/volume] in Blood",
                    interpretation=["HH"]  # Critical High
                )
            ],
            abnormal_values=[
                LabValue(
                    value=180.0,
                    unit="mg/dL",
                    timestamp=datetime(2023, 1, 1, 12, 0, 0),
                    loinc_code="2345-7",
                    display_name="Glucose [Mass/volume] in Serum",
                    interpretation=["H"]  # High
                )
            ],
            last_updated=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        mock_fhir_client_dependency.get_critical_labs.return_value = expected_critical_labs
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs/critical")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert len(data["critical_values"]) == 1
        assert len(data["abnormal_values"]) == 1
        
        # Verify critical value details
        critical_value = data["critical_values"][0]
        assert critical_value["value"] == 15.2
        assert critical_value["loinc_code"] == "6690-2"
        assert critical_value["interpretation"] == ["HH"]
        
        # Verify abnormal value details
        abnormal_value = data["abnormal_values"][0]
        assert abnormal_value["value"] == 180.0
        assert abnormal_value["loinc_code"] == "2345-7"
        
        mock_fhir_client_dependency.get_critical_labs.assert_called_once_with(sample_patient_id)

    def test_get_critical_labs_no_critical_values(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test critical labs retrieval with no critical values."""
        # Arrange
        expected_critical_labs = CriticalLabsResponse(
            patient_id=sample_patient_id,
            critical_values=[],
            abnormal_values=[],
            last_updated=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        mock_fhir_client_dependency.get_critical_labs.return_value = expected_critical_labs
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs/critical")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["patient_id"] == sample_patient_id
        assert len(data["critical_values"]) == 0
        assert len(data["abnormal_values"]) == 0

    def test_get_critical_labs_multiple_values(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test critical labs retrieval with multiple critical and abnormal values."""
        # Arrange
        expected_critical_labs = CriticalLabsResponse(
            patient_id=sample_patient_id,
            critical_values=[
                LabValue(
                    value=2.5,
                    unit="mg/dL",
                    timestamp=datetime(2023, 1, 1, 12, 0, 0),
                    loinc_code="2160-0",
                    display_name="Creatinine",
                    interpretation=["HH"]  # Critical High
                ),
                LabValue(
                    value=50.0,
                    unit="10*3/uL",
                    timestamp=datetime(2023, 1, 1, 12, 0, 0),
                    loinc_code="777-3",
                    display_name="Platelets",
                    interpretation=["LL"]  # Critical Low
                )
            ],
            abnormal_values=[
                LabValue(
                    value=12.5,
                    unit="10*3/uL",
                    timestamp=datetime(2023, 1, 1, 12, 0, 0),
                    loinc_code="6690-2",
                    display_name="WBC",
                    interpretation=["H"]  # High
                )
            ],
            last_updated=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        mock_fhir_client_dependency.get_critical_labs.return_value = expected_critical_labs
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs/critical")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["critical_values"]) == 2
        assert len(data["abnormal_values"]) == 1
        
        # Verify critical values
        critical_values = data["critical_values"]
        assert critical_values[0]["interpretation"] == ["HH"]
        assert critical_values[1]["interpretation"] == ["LL"]

    def test_get_critical_labs_patient_not_found(self, test_client, mock_fhir_client_dependency):
        """Test critical labs retrieval for non-existent patient."""
        # Arrange
        patient_id = "nonexistent-patient"
        mock_fhir_client_dependency.get_critical_labs.side_effect = FHIRException(404, "Patient not found")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{patient_id}/labs/critical")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "Patient not found" in data["message"]

    def test_get_critical_labs_access_denied(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test critical labs retrieval with access denied."""
        # Arrange
        mock_fhir_client_dependency.get_critical_labs.side_effect = FHIRException(403, "Access denied to critical labs")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs/critical")
        
        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "Access denied" in data["message"]

    def test_get_critical_labs_server_error(self, test_client, mock_fhir_client_dependency, sample_patient_id):
        """Test critical labs retrieval with server error."""
        # Arrange
        mock_fhir_client_dependency.get_critical_labs.side_effect = FHIRException(500, "FHIR server error")
        
        # Act
        response = test_client.get(f"/api/v1/sepsis-alert/patients/{sample_patient_id}/labs/critical")
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error"] == "FHIR_ERROR"
        assert "FHIR server error" in data["message"]