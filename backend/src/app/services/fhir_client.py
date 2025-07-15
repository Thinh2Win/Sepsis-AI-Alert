import requests
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.exceptions import FHIRException, PaginationException
from app.services.auth_client import EpicAuthClient
from app.models.patient import PatientResponse, PatientMatchRequest, PatientMatchResponse, PatientDemographics
from app.models.vitals import VitalSignsResponse, VitalSignsLatestResponse, VitalSignsTimeSeries, VitalSignsData, VitalSign, BloodPressure
from app.models.labs import LabResultsResponse, CriticalLabsResponse
from app.models.clinical import EncounterResponse, ConditionsResponse, MedicationsResponse, FluidBalanceResponse
from app.utils.fhir_utils import extract_observation_value, extract_patient_demographics, extract_observations_by_loinc
from app.utils.calculations import convert_height_to_cm, convert_weight_to_kg, calculate_bmi
from app.core.loinc_codes import LOINCCodes

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
    async def _make_request(
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

    async def _handle_pagination(self, bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
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
                next_bundle = await self._make_request("GET", next_link)
                all_entries.extend(self._get_bundle_entries(next_bundle))
                bundle = next_bundle
            except Exception as e:
                logger.warning(f"Failed to fetch next page: {str(e)}")
                break
        
        return all_entries

    async def get_patient(self, patient_id: str) -> PatientResponse:
        """
        Get patient demographics using Patient.Read and Observation.Search for height/weight/BMI
        """
        try:
            # 1. Get patient demographics
            patient_data = await self._make_request("GET", f"Patient/{patient_id}")
            
            # 2. Get height/weight/BMI observations
            demographics_params = {
                "patient": patient_id,
                "code": "8302-2,29463-7,39156-5",  # height, weight, BMI
                "_sort": "-date",
                "_count": "3"  # Get latest of each type
            }
            demographics_bundle = await self._make_request("GET", "Observation", params=demographics_params)
            
            # 3. Process patient demographics
            demographics = extract_patient_demographics(patient_data)
            
            # 4. Process demographic observations
            patient_demographics = self._process_demographics_observations(demographics_bundle)
            
            # 5. Create patient response
            patient_response = PatientResponse(
                id=patient_data.get("id"),
                active=patient_data.get("active"),
                name=demographics.get("names", []),
                telecom=demographics.get("telecoms", []),
                gender=demographics.get("gender"),
                birth_date=demographics.get("birth_date"),
                address=demographics.get("addresses", []),
                identifier=demographics.get("identifiers", []),
                marital_status=patient_data.get("maritalStatus"),
                demographics=patient_demographics
            )
            
            return patient_response
            
        except Exception as e:
            logger.error(f"Error getting patient {patient_id}: {str(e)}")
            raise FHIRException(500, f"Failed to retrieve patient data: {str(e)}")

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

        data = await self._make_request("POST", "Patient/$match", data=parameters)
        return PatientMatchResponse(**data)

    async def get_vitals(self, patient_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, vital_type: Optional[str] = None) -> VitalSignsResponse:
        """
        Get patient vital signs using specific LOINC codes with concurrent FHIR calls
        """
        try:
            # Define vital sign types and their LOINC codes
            vital_types = {
                "HR": ["8867-4"],  # Heart Rate
                "BP": ["85354-9", "8480-6", "8462-4"],  # Blood Pressure Panel, Systolic, Diastolic
                "TEMP": ["8310-5"],  # Temperature
                "RR": ["9279-1"],  # Respiratory Rate
                "SPO2": ["2708-6", "59408-5"],  # Oxygen Saturation
                "GCS": ["9269-2"]  # Glasgow Coma Score
            }
            
            # Determine which vital signs to fetch
            if vital_type and vital_type.upper() in vital_types:
                types_to_fetch = {vital_type.upper(): vital_types[vital_type.upper()]}
            else:
                types_to_fetch = vital_types
            
            # Create concurrent tasks for each vital sign type
            tasks = []
            for vtype, codes in types_to_fetch.items():
                task = self._fetch_vital_observations(patient_id, codes, start_date, end_date, vtype)
                tasks.append(task)
            
            # Execute all tasks concurrently
            vital_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            vital_signs = self._process_vitals_results(vital_results)
            
            return VitalSignsResponse(
                patient_id=patient_id,
                vital_signs=vital_signs,
                total_entries=sum(len(getattr(vital_signs, attr)) for attr in ["heart_rate", "respiratory_rate", "body_temperature", "oxygen_saturation", "glasgow_coma_score"] if isinstance(getattr(vital_signs, attr), list)) + len(vital_signs.blood_pressure),
                date_range={"start": start_date, "end": end_date} if start_date or end_date else None
            )
            
        except Exception as e:
            logger.error(f"Error getting vitals for patient {patient_id}: {str(e)}")
            raise FHIRException(500, f"Failed to retrieve vital signs: {str(e)}")

    async def get_latest_vitals(self, patient_id: str) -> VitalSignsLatestResponse:
        """
        Get latest vital signs using specific LOINC codes with _count=1 parameter
        """
        try:
            # Define vital sign types and their LOINC codes
            vital_types = {
                "HR": ["8867-4"],  # Heart Rate
                "BP": ["85354-9", "8480-6", "8462-4"],  # Blood Pressure Panel, Systolic, Diastolic
                "TEMP": ["8310-5"],  # Temperature
                "RR": ["9279-1"],  # Respiratory Rate
                "SPO2": ["2708-6", "59408-5"],  # Oxygen Saturation
                "GCS": ["9269-2"]  # Glasgow Coma Score
            }
            
            # Create concurrent tasks for each vital sign type (with _count=1)
            tasks = []
            for vtype, codes in vital_types.items():
                task = self._fetch_vital_observations(patient_id, codes, None, None, vtype, count=1)
                tasks.append(task)
            
            # Execute all tasks concurrently
            vital_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results to get latest values
            vital_signs = self._process_latest_vitals_results(vital_results)
            
            return VitalSignsLatestResponse(
                patient_id=patient_id,
                vital_signs=vital_signs,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error getting latest vitals for patient {patient_id}: {str(e)}")
            raise FHIRException(500, f"Failed to retrieve latest vital signs: {str(e)}")

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

        bundle = await self._make_request("GET", "Observation", params=params)
        entries = await self._handle_pagination(bundle)
        
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

        bundle = await self._make_request("GET", "Observation", params=params)
        entries = await self._handle_pagination(bundle)
        
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

        bundle = await self._make_request("GET", "Encounter", params=params)
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

        bundle = await self._make_request("GET", "Condition", params=params)
        entries = await self._handle_pagination(bundle)
        
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

        bundle = await self._make_request("GET", "MedicationRequest", params=params)
        entries = await self._handle_pagination(bundle)
        
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

        bundle = await self._make_request("GET", "Observation", params=params)
        entries = await self._handle_pagination(bundle)
        
        return FluidBalanceResponse(
            patient_id=patient_id,
            **self._process_fluid_balance(entries)
        )

    async def _fetch_vital_observations(self, patient_id: str, codes: List[str], start_date: Optional[datetime], end_date: Optional[datetime], vital_type: str, count: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch vital observations for specific LOINC codes
        """
        try:
            params = {
                "patient": patient_id,
                "code": ",".join(codes),
                "_sort": "-date"
            }
            
            if start_date:
                params["date"] = f"ge{start_date.isoformat()}"
            if end_date:
                date_param = params.get("date", "")
                if date_param:
                    params["date"] = f"{date_param}&date=le{end_date.isoformat()}"
                else:
                    params["date"] = f"le{end_date.isoformat()}"
            
            if count:
                params["_count"] = str(count)
            
            bundle = await self._make_request("GET", "Observation", params=params)
            entries = self._get_bundle_entries(bundle) if count else await self._handle_pagination(bundle)
            
            return {
                "vital_type": vital_type,
                "codes": codes,
                "entries": entries,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error fetching {vital_type} observations: {str(e)}")
            return {
                "vital_type": vital_type,
                "codes": codes,
                "entries": [],
                "success": False,
                "error": str(e)
            }

    def _process_demographics_observations(self, bundle: Dict[str, Any]) -> PatientDemographics:
        """
        Process demographic observations (height, weight, BMI)
        """
        observations = extract_observations_by_loinc(bundle, ["8302-2", "29463-7", "39156-5"])
        
        height_cm = None
        weight_kg = None
        bmi = None
        
        for obs in observations:
            loinc_code = obs.get("loinc_code")
            value = obs.get("value")
            unit = obs.get("unit", "")
            
            if loinc_code == "8302-2" and value:  # Height
                height_cm = convert_height_to_cm(value, unit)
            elif loinc_code == "29463-7" and value:  # Weight
                weight_kg = convert_weight_to_kg(value, unit)
            elif loinc_code == "39156-5" and value:  # BMI
                bmi = value
        
        # Calculate BMI if not provided but height and weight are available
        if not bmi and height_cm and weight_kg:
            bmi = calculate_bmi(height_cm, weight_kg)
        
        return PatientDemographics(
            height_cm=height_cm,
            weight_kg=weight_kg,
            bmi=bmi
        )

    def _process_vitals_results(self, vital_results: List[Dict[str, Any]]) -> VitalSignsTimeSeries:
        """
        Process concurrent vital signs results into VitalSignsTimeSeries
        """
        vital_signs = VitalSignsTimeSeries()
        
        for result in vital_results:
            if isinstance(result, Exception):
                logger.error(f"Error in vital signs fetch: {str(result)}")
                continue
            
            if not result.get("success", False):
                logger.warning(f"Failed to fetch {result.get('vital_type')}: {result.get('error')}")
                continue
            
            vital_type = result.get("vital_type")
            entries = result.get("entries", [])
            
            if vital_type == "HR":
                vital_signs.heart_rate = self._process_heart_rate(entries)
            elif vital_type == "BP":
                vital_signs.blood_pressure = self._process_blood_pressure(entries)
            elif vital_type == "TEMP":
                vital_signs.body_temperature = self._process_temperature(entries)
            elif vital_type == "RR":
                vital_signs.respiratory_rate = self._process_respiratory_rate(entries)
            elif vital_type == "SPO2":
                vital_signs.oxygen_saturation = self._process_oxygen_saturation(entries)
            elif vital_type == "GCS":
                vital_signs.glasgow_coma_score = self._process_glasgow_coma_score(entries)
        
        return vital_signs

    def _process_latest_vitals_results(self, vital_results: List[Dict[str, Any]]) -> VitalSignsData:
        """
        Process concurrent vital signs results into VitalSignsData (latest values)
        """
        vital_signs = VitalSignsData()
        
        for result in vital_results:
            if isinstance(result, Exception):
                logger.error(f"Error in vital signs fetch: {str(result)}")
                continue
            
            if not result.get("success", False):
                logger.warning(f"Failed to fetch {result.get('vital_type')}: {result.get('error')}")
                continue
            
            vital_type = result.get("vital_type")
            entries = result.get("entries", [])
            
            if not entries:
                continue
            
            if vital_type == "HR":
                hr_list = self._process_heart_rate(entries)
                vital_signs.heart_rate = hr_list[0] if hr_list else None
            elif vital_type == "BP":
                bp_list = self._process_blood_pressure(entries)
                vital_signs.blood_pressure = bp_list[0] if bp_list else None
            elif vital_type == "TEMP":
                temp_list = self._process_temperature(entries)
                vital_signs.body_temperature = temp_list[0] if temp_list else None
            elif vital_type == "RR":
                rr_list = self._process_respiratory_rate(entries)
                vital_signs.respiratory_rate = rr_list[0] if rr_list else None
            elif vital_type == "SPO2":
                spo2_list = self._process_oxygen_saturation(entries)
                vital_signs.oxygen_saturation = spo2_list[0] if spo2_list else None
            elif vital_type == "GCS":
                gcs_list = self._process_glasgow_coma_score(entries)
                vital_signs.glasgow_coma_score = gcs_list[0] if gcs_list else None
        
        return vital_signs

    def _process_heart_rate(self, entries: List[Dict[str, Any]]) -> List[VitalSign]:
        """Process heart rate observations"""
        heart_rates = []
        observations = extract_observations_by_loinc(entries, ["8867-4"])
        
        for obs in observations:
            if obs.get("value") is not None:
                heart_rates.append(VitalSign(
                    value=obs.get("value"),
                    unit=obs.get("unit"),
                    timestamp=obs.get("timestamp"),
                    status=obs.get("status"),
                    interpretation=obs.get("interpretation"),
                    reference_range=obs.get("reference_range"),
                    loinc_code=obs.get("loinc_code"),
                    display_name=obs.get("display_name")
                ))
        
        return heart_rates

    def _process_blood_pressure(self, entries: List[Dict[str, Any]]) -> List[BloodPressure]:
        """Process blood pressure observations"""
        blood_pressures = []
        
        # Group observations by timestamp to pair systolic/diastolic
        timestamp_groups = {}
        observations = extract_observations_by_loinc(entries, ["85354-9", "8480-6", "8462-4"])
        
        for obs in observations:
            if obs.get("value") is not None:
                timestamp = obs.get("timestamp")
                if timestamp not in timestamp_groups:
                    timestamp_groups[timestamp] = {"systolic": None, "diastolic": None}
                
                loinc_code = obs.get("loinc_code")
                vital_sign = VitalSign(
                    value=obs.get("value"),
                    unit=obs.get("unit"),
                    timestamp=timestamp,
                    status=obs.get("status"),
                    interpretation=obs.get("interpretation"),
                    reference_range=obs.get("reference_range"),
                    loinc_code=loinc_code,
                    display_name=obs.get("display_name")
                )
                
                if loinc_code == "8480-6":  # Systolic
                    timestamp_groups[timestamp]["systolic"] = vital_sign
                elif loinc_code == "8462-4":  # Diastolic
                    timestamp_groups[timestamp]["diastolic"] = vital_sign
        
        # Create BloodPressure objects
        for timestamp, bp_data in timestamp_groups.items():
            if bp_data["systolic"] or bp_data["diastolic"]:
                blood_pressures.append(BloodPressure(
                    systolic=bp_data["systolic"],
                    diastolic=bp_data["diastolic"]
                ))
        
        return blood_pressures

    def _process_temperature(self, entries: List[Dict[str, Any]]) -> List[VitalSign]:
        """Process temperature observations"""
        temperatures = []
        observations = extract_observations_by_loinc(entries, ["8310-5"])
        
        for obs in observations:
            if obs.get("value") is not None:
                temperatures.append(VitalSign(
                    value=obs.get("value"),
                    unit=obs.get("unit"),
                    timestamp=obs.get("timestamp"),
                    status=obs.get("status"),
                    interpretation=obs.get("interpretation"),
                    reference_range=obs.get("reference_range"),
                    loinc_code=obs.get("loinc_code"),
                    display_name=obs.get("display_name")
                ))
        
        return temperatures

    def _process_respiratory_rate(self, entries: List[Dict[str, Any]]) -> List[VitalSign]:
        """Process respiratory rate observations"""
        respiratory_rates = []
        observations = extract_observations_by_loinc(entries, ["9279-1"])
        
        for obs in observations:
            if obs.get("value") is not None:
                respiratory_rates.append(VitalSign(
                    value=obs.get("value"),
                    unit=obs.get("unit"),
                    timestamp=obs.get("timestamp"),
                    status=obs.get("status"),
                    interpretation=obs.get("interpretation"),
                    reference_range=obs.get("reference_range"),
                    loinc_code=obs.get("loinc_code"),
                    display_name=obs.get("display_name")
                ))
        
        return respiratory_rates

    def _process_oxygen_saturation(self, entries: List[Dict[str, Any]]) -> List[VitalSign]:
        """Process oxygen saturation observations"""
        oxygen_saturations = []
        observations = extract_observations_by_loinc(entries, ["2708-6", "59408-5"])
        
        for obs in observations:
            if obs.get("value") is not None:
                oxygen_saturations.append(VitalSign(
                    value=obs.get("value"),
                    unit=obs.get("unit"),
                    timestamp=obs.get("timestamp"),
                    status=obs.get("status"),
                    interpretation=obs.get("interpretation"),
                    reference_range=obs.get("reference_range"),
                    loinc_code=obs.get("loinc_code"),
                    display_name=obs.get("display_name")
                ))
        
        return oxygen_saturations

    def _process_glasgow_coma_score(self, entries: List[Dict[str, Any]]) -> List[VitalSign]:
        """Process Glasgow Coma Score observations"""
        glasgow_scores = []
        observations = extract_observations_by_loinc(entries, ["9269-2"])
        
        for obs in observations:
            if obs.get("value") is not None:
                glasgow_scores.append(VitalSign(
                    value=obs.get("value"),
                    unit=obs.get("unit"),
                    timestamp=obs.get("timestamp"),
                    status=obs.get("status"),
                    interpretation=obs.get("interpretation"),
                    reference_range=obs.get("reference_range"),
                    loinc_code=obs.get("loinc_code"),
                    display_name=obs.get("display_name")
                ))
        
        return glasgow_scores

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