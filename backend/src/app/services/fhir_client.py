import requests
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.exceptions import FHIRException, PaginationException
from app.services.auth_client import EpicAuthClient
from app.models.patient import PatientResponse, PatientMatchRequest, PatientMatchResponse
from app.models.vitals import VitalSignsResponse, VitalSignsLatestResponse
from app.models.labs import LabResultsResponse, CriticalLabsResponse
from app.models.clinical import EncounterResponse, ConditionsResponse, MedicationsResponse, FluidBalanceResponse

logger = logging.getLogger(__name__)

class FHIRClient:
    def __init__(self):
        self.base_url = settings.fhir_api_base
        self.auth_client = EpicAuthClient()
        self.session = requests.Session()
        
        if not self.base_url:
            raise FHIRException(500, "FHIR API base URL not configured")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, FHIRException))
    )
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self.auth_client.get_auth_headers()
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=settings.fhir_timeout
            )
            
            if response.status_code == 401:
                logger.warning("Authentication failed, attempting token refresh")
                self.auth_client.fetch_token()
                headers = self.auth_client.get_auth_headers()
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data,
                    timeout=settings.fhir_timeout
                )
            
            if not response.ok:
                error_msg = f"FHIR request failed: {response.status_code}"
                try:
                    error_detail = response.json()
                    if 'issue' in error_detail:
                        error_msg += f" - {error_detail['issue']}"
                except:
                    error_msg += f" - {response.text}"
                
                raise FHIRException(response.status_code, error_msg)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FHIR request error: {str(e)}")
            raise FHIRException(500, f"Network error: {str(e)}")

    def _get_bundle_entries(self, bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
        if bundle.get("resourceType") != "Bundle":
            raise FHIRException(500, "Expected Bundle resource type")
        
        return [entry.get("resource", {}) for entry in bundle.get("entry", [])]

    def _handle_pagination(self, bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
        all_entries = self._get_bundle_entries(bundle)
        
        while True:
            next_link = None
            for link in bundle.get("link", []):
                if link.get("relation") == "next":
                    next_link = link.get("url")
                    break
            
            if not next_link:
                break
                
            try:
                next_bundle = self._make_request("GET", next_link)
                all_entries.extend(self._get_bundle_entries(next_bundle))
                bundle = next_bundle
            except Exception as e:
                logger.warning(f"Failed to fetch next page: {str(e)}")
                break
        
        return all_entries

    async def get_patient(self, patient_id: str) -> PatientResponse:
        data = self._make_request("GET", f"Patient/{patient_id}")
        return PatientResponse(**data)

    async def match_patient(self, match_request: PatientMatchRequest) -> PatientMatchResponse:
        patient_resource = {
            "resourceType": "Patient",
            "name": [{"family": match_request.family, "given": [match_request.given]}],
            "birthDate": match_request.birth_date,
        }
        
        if match_request.phone:
            patient_resource["telecom"] = [{"system": "phone", "value": match_request.phone}]
        
        if match_request.address:
            patient_resource["address"] = [match_request.address.dict()]

        parameters = {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "resource", "resource": patient_resource},
                {"name": "OnlyCertainMatches", "valueBoolean": True}
            ]
        }

        data = self._make_request("POST", "Patient/$match", data=parameters)
        return PatientMatchResponse(**data)

    async def get_vitals(self, patient_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> VitalSignsResponse:
        params = {
            "patient": patient_id,
            "category": "vital-signs",
            "_sort": "-date"
        }
        
        if start_date:
            params["date"] = f"ge{start_date.isoformat()}"
        if end_date:
            params["date"] = f"le{end_date.isoformat()}"

        bundle = self._make_request("GET", "Observation", params=params)
        entries = self._handle_pagination(bundle)
        
        return VitalSignsResponse(
            patient_id=patient_id,
            vital_signs=self._process_vitals(entries),
            total_entries=len(entries)
        )

    async def get_latest_vitals(self, patient_id: str) -> VitalSignsLatestResponse:
        params = {
            "patient": patient_id,
            "category": "vital-signs",
            "_sort": "-date",
            "_count": "1"
        }

        bundle = self._make_request("GET", "Observation", params=params)
        entries = self._get_bundle_entries(bundle)
        
        return VitalSignsLatestResponse(
            patient_id=patient_id,
            vital_signs=self._process_latest_vitals(entries)
        )

    async def get_labs(self, patient_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> LabResultsResponse:
        params = {
            "patient": patient_id,
            "category": "laboratory",
            "_sort": "-date"
        }
        
        if start_date:
            params["date"] = f"ge{start_date.isoformat()}"
        if end_date:
            params["date"] = f"le{end_date.isoformat()}"

        bundle = self._make_request("GET", "Observation", params=params)
        entries = self._handle_pagination(bundle)
        
        return LabResultsResponse(
            patient_id=patient_id,
            lab_results=self._process_labs(entries),
            total_entries=len(entries)
        )

    async def get_critical_labs(self, patient_id: str) -> CriticalLabsResponse:
        params = {
            "patient": patient_id,
            "category": "laboratory",
            "interpretation": "H,HH,L,LL,A,AA",
            "_sort": "-date"
        }

        bundle = self._make_request("GET", "Observation", params=params)
        entries = self._handle_pagination(bundle)
        
        return CriticalLabsResponse(
            patient_id=patient_id,
            critical_values=self._process_critical_labs(entries)
        )

    async def get_encounter(self, patient_id: str) -> EncounterResponse:
        params = {
            "patient": patient_id,
            "status": "in-progress,arrived",
            "_sort": "-date",
            "_count": "1"
        }

        bundle = self._make_request("GET", "Encounter", params=params)
        entries = self._get_bundle_entries(bundle)
        
        return EncounterResponse(
            patient_id=patient_id,
            current_encounter=self._process_encounter(entries[0]) if entries else None
        )

    async def get_conditions(self, patient_id: str) -> ConditionsResponse:
        params = {
            "patient": patient_id,
            "clinical-status": "active,recurrence,relapse"
        }

        bundle = self._make_request("GET", "Condition", params=params)
        entries = self._handle_pagination(bundle)
        
        return ConditionsResponse(
            patient_id=patient_id,
            active_conditions=self._process_conditions(entries),
            total_conditions=len(entries)
        )

    async def get_medications(self, patient_id: str, antibiotics_only: bool = False, vasopressors_only: bool = False) -> MedicationsResponse:
        params = {
            "patient": patient_id,
            "status": "active",
            "_include": "MedicationRequest:medication"
        }

        if antibiotics_only:
            params["medication.code:text"] = "antibiotic,antimicrobial"
        elif vasopressors_only:
            params["medication.code:text"] = "norepinephrine,epinephrine,vasopressin,dopamine"

        bundle = self._make_request("GET", "MedicationRequest", params=params)
        entries = self._handle_pagination(bundle)
        
        return MedicationsResponse(
            patient_id=patient_id,
            active_medications=self._process_medications(entries),
            total_medications=len(entries)
        )

    async def get_fluid_balance(self, patient_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> FluidBalanceResponse:
        params = {
            "patient": patient_id,
            "code": "9192-6,9187-6,9188-4",
            "_sort": "-date"
        }
        
        if start_date:
            params["date"] = f"ge{start_date.isoformat()}"
        if end_date:
            params["date"] = f"le{end_date.isoformat()}"

        bundle = self._make_request("GET", "Observation", params=params)
        entries = self._handle_pagination(bundle)
        
        return FluidBalanceResponse(
            patient_id=patient_id,
            **self._process_fluid_balance(entries)
        )

    def _process_vitals(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        pass

    def _process_latest_vitals(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        pass

    def _process_labs(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        pass

    def _process_critical_labs(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass

    def _process_encounter(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def _process_conditions(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass

    def _process_medications(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass

    def _process_fluid_balance(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        pass