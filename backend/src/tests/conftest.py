"""
Test configuration and shared fixtures for Sepsis AI Alert System tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.services.fhir_client import FHIRClient
from app.core.dependencies import get_fhir_client
from app.core.exceptions import FHIRException


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_fhir_client():
    """Create a mock FHIR client with configurable responses."""
    client = Mock(spec=FHIRClient)
    
    # Make all methods async mocks
    client.get_patient = AsyncMock()
    client.match_patient = AsyncMock()
    client.get_vitals = AsyncMock()
    client.get_latest_vitals = AsyncMock()
    client.get_labs = AsyncMock()
    client.get_critical_labs = AsyncMock()
    client.get_encounter = AsyncMock()
    client.get_conditions = AsyncMock()
    client.get_medications = AsyncMock()
    client.get_fluid_balance = AsyncMock()
    client._make_request = AsyncMock()
    
    return client


@pytest.fixture
def mock_fhir_client_dependency(mock_fhir_client):
    """Override the FHIR client dependency with a mock."""
    def _get_mock_fhir_client():
        return mock_fhir_client
    
    app.dependency_overrides[get_fhir_client] = _get_mock_fhir_client
    yield mock_fhir_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def async_client(mock_fhir_client_dependency):
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_patient_id():
    """Sample patient ID for testing."""
    return "test-patient-123"


@pytest.fixture
def sample_fhir_response_success():
    """Sample successful FHIR response."""
    return {
        "resourceType": "Bundle",
        "id": "test-bundle",
        "type": "searchset",
        "total": 1,
        "entry": [
            {
                "fullUrl": "https://fhir.server/Patient/test-patient-123",
                "resource": {
                    "resourceType": "Patient",
                    "id": "test-patient-123",
                    "active": True,
                    "name": [
                        {
                            "use": "official",
                            "family": "Doe",
                            "given": ["John"]
                        }
                    ],
                    "gender": "male",
                    "birthDate": "1980-01-01"
                }
            }
        ]
    }


@pytest.fixture
def sample_fhir_error_response():
    """Sample FHIR error response."""
    return {
        "resourceType": "OperationOutcome",
        "issue": [
            {
                "severity": "error",
                "code": "forbidden",
                "diagnostics": "Access denied to patient data"
            }
        ]
    }


@pytest.fixture
def mock_requests_session():
    """Mock requests session for FHIR client testing."""
    with patch('app.services.fhir_client.requests.Session') as mock_session:
        session_instance = Mock()
        mock_session.return_value = session_instance
        yield session_instance


@pytest.fixture
def mock_auth_client():
    """Mock authentication client."""
    with patch('app.services.fhir_client.EpicAuthClient') as mock_auth:
        auth_instance = Mock()
        auth_instance.get_auth_headers.return_value = {
            "Authorization": "Bearer test-token",
            "Accept": "application/fhir+json"
        }
        auth_instance.fetch_token = Mock()
        mock_auth.return_value = auth_instance
        yield auth_instance


class MockResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, status_code: int, json_data: Optional[Dict[str, Any]] = None, 
                 text: str = "", ok: bool = None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.ok = ok if ok is not None else (200 <= status_code < 300)
    
    def json(self):
        if self._json_data:
            return self._json_data
        raise ValueError("No JSON data")


@pytest.fixture
def create_mock_response():
    """Factory for creating mock HTTP responses."""
    return MockResponse


@pytest.fixture
def fhir_client_with_mocks(mock_requests_session, mock_auth_client):
    """Create a real FHIR client with mocked dependencies."""
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.fhir_api_base = "https://test-fhir.example.com/api/FHIR/R4"
        mock_settings.fhir_timeout = 30
        
        client = FHIRClient()
        client.session = mock_requests_session
        client.auth_client = mock_auth_client
        
        return client


@pytest.fixture
def sample_datetime():
    """Sample datetime for testing."""
    return datetime(2023, 1, 1, 12, 0, 0)


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    """Automatically reset dependency overrides after each test."""
    yield
    app.dependency_overrides.clear()