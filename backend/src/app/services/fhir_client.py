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
        import time
        
        start_time = time.time()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        if params:
            # Log parameters without patient ID for privacy
            safe_params = {k: v for k, v in params.items() if k != 'patient'}
            if 'patient' in params:
                safe_params['patient'] = '[REDACTED]'
            logger.debug(f"Query parameters: {safe_params}")
        
        try:
            headers = self.auth_client.get_auth_headers()
            
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=settings.fhir_timeout
            )
            
            response_time = time.time() - start_time
            logger.info(f"FHIR Response: {response.status_code} ({response_time:.2f}s)")
            
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
                response_time = time.time() - start_time
                logger.info(f"FHIR Response after token refresh: {response.status_code} ({response_time:.2f}s)")
            
            if not response.ok:
                error_msg = f"FHIR request failed: {response.status_code}"
                try:
                    error_detail = response.json()
                    # Log error details without PHI
                    if 'resourceType' in error_detail and error_detail['resourceType'] == 'OperationOutcome':
                        issues = error_detail.get('issue', [])
                        if issues:
                            issue = issues[0]
                            severity = issue.get('severity', 'unknown')
                            code = issue.get('code', 'unknown')
                            diagnostics = issue.get('diagnostics', 'No diagnostics')
                            logger.error(f"FHIR OperationOutcome: severity={severity}, code={code}, diagnostics={diagnostics}")
                            error_msg += f" - {diagnostics}"
                    elif 'issue' in error_detail:
                        error_msg += f" - {error_detail['issue']}"
                except Exception as parse_error:
                    logger.error(f"Failed to parse error response: {parse_error}")
                    error_msg += f" - HTTP {response.status_code}"
                
                raise FHIRException(response.status_code, error_msg)
            
            response_data = response.json()
            
            # Log response summary without PHI
            if isinstance(response_data, dict):
                if 'resourceType' in response_data:
                    logger.info(f"Resource type: {response_data['resourceType']}")
                if 'total' in response_data:
                    logger.info(f"Total results: {response_data['total']}")
                if 'entry' in response_data:
                    logger.info(f"Entries count: {len(response_data['entry'])}")
            
            return response_data
            
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
        """
        Match patient using FHIR Patient.$match operation with proper Parameters structure
        """
        patient_resource = {
            "resourceType": "Patient",
            "name": [{"family": match_request.family, "given": [match_request.given]}],
            "birthDate": match_request.birth_date,
        }
        
        if match_request.phone:
            patient_resource["telecom"] = [{"system": "phone", "value": match_request.phone, "use": "home"}]
        
        if match_request.address:
            address_dict = match_request.address.dict()
            # Convert postalCode to match FHIR format
            if "postal_code" in address_dict:
                address_dict["postalCode"] = address_dict.pop("postal_code")
            patient_resource["address"] = [address_dict]

        parameters = {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "resource", "resource": patient_resource},
                {"name": "onlyCertainMatches", "valueBoolean": True}
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

    async def get_labs(self, patient_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, lab_category: Optional[str] = None) -> LabResultsResponse:
        """
        Get patient laboratory results with category-based grouping
        """
        import time
        
        start_time = time.time()
        
        try:
            logger.info(f"Getting labs for patient [REDACTED], category: {lab_category}")
            
            # Validate input parameters
            if not patient_id or not patient_id.strip():
                raise FHIRException(400, "Patient ID is required")
            
            # Define lab categories and their LOINC codes
            lab_categories = {
                "CBC": ["6690-2", "777-3"],  # WBC, Platelets
                "METABOLIC": ["2160-0", "3094-0", "2345-7"],  # Creatinine, BUN, Glucose
                "LIVER": ["1975-2", "1742-6", "14804-9"],  # Bilirubin, Albumin, LDH
                "INFLAMMATORY": ["1988-5", "75241-0"],  # CRP, Procalcitonin
                "BLOOD_GAS": ["2019-8", "2744-1", "50984-4"],  # Lactate, pH, PaO2/FiO2
                "COAGULATION": ["5902-2", "3173-2"]  # PT/INR, PTT
            }
            
            # Determine which categories to fetch
            if lab_category and lab_category.upper() in lab_categories:
                categories_to_fetch = {lab_category.upper(): lab_categories[lab_category.upper()]}
                logger.info(f"Fetching single category: {lab_category.upper()}")
            else:
                categories_to_fetch = lab_categories
                logger.info(f"Fetching all categories: {list(lab_categories.keys())}")
            
            # Create concurrent tasks for each lab category
            tasks = []
            for category_name, codes in categories_to_fetch.items():
                task = self._fetch_lab_observations(patient_id, codes, start_date, end_date, category_name)
                tasks.append(task)
            
            # Execute all tasks concurrently
            lab_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful_results = []
            failed_results = []
            
            for result in lab_results:
                if isinstance(result, Exception):
                    failed_results.append(str(result))
                    logger.error(f"Lab category failed: {str(result)}")
                elif result.get('success', False):
                    successful_results.append(result)
                else:
                    failed_results.append(result.get('error', 'Unknown error'))
                    logger.warning(f"Lab category failed: {result.get('lab_category', 'Unknown')}")
            
            # Process successful results
            lab_data = self._process_lab_results(lab_results)
            total_entries = self._count_total_lab_entries(lab_data)
            
            processing_time = time.time() - start_time
            logger.info(f"Labs processed: {len(successful_results)}/{len(lab_results)} categories successful, {total_entries} total entries ({processing_time:.2f}s)")
            
            return LabResultsResponse(
                patient_id=patient_id,
                lab_results=lab_data,
                total_entries=total_entries,
                date_range={"start": start_date, "end": end_date} if start_date or end_date else None
            )
            
        except FHIRException:
            # Re-raise FHIR exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Error getting labs: {str(e)}")
            raise FHIRException(500, f"Failed to retrieve laboratory results: {str(e)}")

    async def get_critical_labs(self, patient_id: str) -> CriticalLabsResponse:
        """
        Get critical/abnormal laboratory values with interpretation filtering
        """
        try:
            # Define lab categories and their LOINC codes (same as regular labs)
            lab_categories = {
                "CBC": ["6690-2", "777-3"],  # WBC, Platelets
                "METABOLIC": ["2160-0", "3094-0", "2345-7"],  # Creatinine, BUN, Glucose
                "LIVER": ["1975-2", "1742-6", "14804-9"],  # Bilirubin, Albumin, LDH
                "INFLAMMATORY": ["1988-5", "75241-0"],  # CRP, Procalcitonin
                "BLOOD_GAS": ["2019-8", "2744-1", "50984-4"],  # Lactate, pH, PaO2/FiO2
                "COAGULATION": ["5902-2", "3173-2"]  # PT/INR, PTT
            }
            
            # Create concurrent tasks for each lab category with interpretation filter
            tasks = []
            for category_name, codes in lab_categories.items():
                task = self._fetch_lab_observations(patient_id, codes, None, None, category_name, interpretation="H,HH,L,LL,A,AA")
                tasks.append(task)
            
            # Execute all tasks concurrently
            lab_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results to get critical values
            critical_values, abnormal_values = self._process_critical_lab_results(lab_results)
            
            return CriticalLabsResponse(
                patient_id=patient_id,
                critical_values=critical_values,
                abnormal_values=abnormal_values,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error getting critical labs for patient {patient_id}: {str(e)}")
            raise FHIRException(500, f"Failed to retrieve critical laboratory values: {str(e)}")

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
            "clinical-status": "active,recurrence,relapse,resolved,remission"
        }

        bundle = await self._make_request("GET", "Condition", params=params)
        entries = await self._handle_pagination(bundle)
        
        # Process all conditions
        all_conditions = self._process_conditions(entries)
        
        # Separate active and resolved conditions
        active_conditions = [cond for cond in all_conditions if cond.is_active]
        resolved_conditions = [cond for cond in all_conditions if cond.is_resolved]
        
        return ConditionsResponse(
            patient_id=patient_id,
            active_conditions=active_conditions,
            resolved_conditions=resolved_conditions,
            total_conditions=len(all_conditions)
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
        
        # Process all medications
        all_medications = self._process_medications(entries)
        
        # Categorize medications
        antibiotics = [med for med in all_medications if med.is_antibiotic]
        vasopressors = [med for med in all_medications if med.is_vasopressor]
        
        return MedicationsResponse(
            patient_id=patient_id,
            active_medications=all_medications,
            antibiotics=antibiotics,
            vasopressors=vasopressors,
            total_medications=len(all_medications)
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

    async def _fetch_lab_observations(self, patient_id: str, codes: List[str], start_date: Optional[datetime], end_date: Optional[datetime], lab_category: str, interpretation: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch laboratory observations for specific LOINC codes
        """
        try:
            logger.debug(f"Fetching {lab_category} observations with {len(codes)} LOINC codes")
            
            params = {
                "patient": patient_id,
                "category": "laboratory",
                "code": ",".join(codes),
                "_sort": "-date"
            }
            
            if start_date:
                date_str = start_date.strftime("%Y-%m-%d")
                params["date"] = f"ge{date_str}"
            
            if end_date:
                date_str = end_date.strftime("%Y-%m-%d")
                date_param = params.get("date", "")
                if date_param:
                    params["date"] = f"{date_param}&date=le{date_str}"
                else:
                    params["date"] = f"le{date_str}"
            
            # Add interpretation filter for critical labs
            if interpretation:
                params["interpretation"] = interpretation
            
            bundle = await self._make_request("GET", "Observation", params=params)
            
            if not isinstance(bundle, dict):
                logger.error(f"Expected dict bundle for {lab_category}, got {type(bundle)}")
                return {
                    "lab_category": lab_category,
                    "codes": codes,
                    "entries": [],
                    "success": False,
                    "error": f"Invalid bundle type: {type(bundle)}"
                }
            
            entries = await self._handle_pagination(bundle)
            
            return {
                "lab_category": lab_category,
                "codes": codes,
                "entries": entries,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error fetching {lab_category} observations: {str(e)}")
            return {
                "lab_category": lab_category,
                "codes": codes,
                "entries": [],
                "success": False,
                "error": str(e)
            }

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

    def _process_lab_results(self, lab_results: List[Dict[str, Any]]) -> "LabResultsData":
        """
        Process concurrent lab results into LabResultsData
        """
        from app.models.labs import LabResultsData, CBCResults, MetabolicPanel, LiverFunction, InflammatoryMarkers, BloodGas, Coagulation, CardiacMarkers, LabValue
        
        # Initialize lab data structure
        lab_data = LabResultsData()
        
        for result in lab_results:
            if isinstance(result, Exception):
                logger.error(f"Error in lab results fetch: {str(result)}")
                continue
            
            if not result.get("success", False):
                logger.warning(f"Failed to fetch {result.get('lab_category')}: {result.get('error')}")
                continue
            
            lab_category = result.get("lab_category")
            entries = result.get("entries", [])
            
            if lab_category == "CBC":
                lab_data.cbc = self._process_cbc_results(entries)
            elif lab_category == "METABOLIC":
                lab_data.metabolic_panel = self._process_metabolic_results(entries)
            elif lab_category == "LIVER":
                lab_data.liver_function = self._process_liver_results(entries)
            elif lab_category == "INFLAMMATORY":
                lab_data.inflammatory_markers = self._process_inflammatory_results(entries)
            elif lab_category == "BLOOD_GAS":
                lab_data.blood_gas = self._process_blood_gas_results(entries)
            elif lab_category == "COAGULATION":
                lab_data.coagulation = self._process_coagulation_results(entries)
        
        return lab_data
    
    def _process_critical_lab_results(self, lab_results: List[Dict[str, Any]]) -> tuple[List["LabValue"], List["LabValue"]]:
        """
        Process critical lab results to separate critical and abnormal values
        """
        from app.models.labs import LabValue
        
        critical_values = []
        abnormal_values = []
        
        for result in lab_results:
            if isinstance(result, Exception):
                logger.error(f"Error in critical lab results fetch: {str(result)}")
                continue
            
            if not result.get("success", False):
                logger.warning(f"Failed to fetch {result.get('lab_category')}: {result.get('error')}")
                continue
            
            entries = result.get("entries", [])
            
            # Process each entry and extract lab values
            for entry in entries:
                lab_value = self._extract_lab_value(entry)
                if lab_value:
                    if lab_value.is_critical:
                        critical_values.append(lab_value)
                    elif lab_value.is_abnormal:
                        abnormal_values.append(lab_value)
        
        return critical_values, abnormal_values
    
    def _count_total_lab_entries(self, lab_data: "LabResultsData") -> int:
        """
        Count total number of lab entries
        """
        total = 0
        
        # Count non-None lab values in each category
        for category in [lab_data.cbc, lab_data.metabolic_panel, lab_data.liver_function, 
                        lab_data.inflammatory_markers, lab_data.blood_gas, lab_data.coagulation]:
            if category:
                # Count non-None attributes in each category
                for attr_name in category.__dict__:
                    attr_value = getattr(category, attr_name)
                    if attr_value is not None and hasattr(attr_value, 'value') and attr_value.value is not None:
                        total += 1
        
        return total

    def _extract_lab_value(self, entry: Dict[str, Any]) -> Optional["LabValue"]:
        """
        Extract lab value from FHIR observation entry
        """
        from app.models.labs import LabValue
        from app.utils.fhir_utils import extract_observation_value
        
        observation = extract_observation_value(entry)
        if not observation or observation.get("value") is None:
            return None
        
        # Extract LOINC code
        loinc_code = None
        display_name = None
        if entry.get("code", {}).get("coding"):
            for coding in entry["code"]["coding"]:
                if coding.get("system") == "http://loinc.org":
                    loinc_code = coding.get("code")
                    display_name = coding.get("display")
                    break
        
        return LabValue(
            value=observation.get("value"),
            unit=observation.get("unit"),
            timestamp=observation.get("timestamp"),
            status=observation.get("status"),
            interpretation=observation.get("interpretation"),
            referenceRange=observation.get("reference_range"),
            loinc_code=loinc_code,
            display_name=display_name
        )
    
    def _process_cbc_results(self, entries: List[Dict[str, Any]]) -> "CBCResults":
        """
        Process CBC lab results (WBC, Platelets)
        """
        from app.models.labs import CBCResults
        from app.utils.fhir_utils import extract_observations_by_loinc, get_most_recent_observation
        
        cbc_results = CBCResults()
        
        # WBC Count (6690-2)
        wbc_observations = extract_observations_by_loinc(entries, ["6690-2"])
        if wbc_observations:
            most_recent_wbc = get_most_recent_observation(wbc_observations)
            if most_recent_wbc:
                cbc_results.white_blood_cell_count = self._create_lab_value(most_recent_wbc, "6690-2")
        
        # Platelet Count (777-3)
        platelet_observations = extract_observations_by_loinc(entries, ["777-3"])
        if platelet_observations:
            most_recent_platelet = get_most_recent_observation(platelet_observations)
            if most_recent_platelet:
                cbc_results.platelet_count = self._create_lab_value(most_recent_platelet, "777-3")
        
        return cbc_results
    
    def _process_metabolic_results(self, entries: List[Dict[str, Any]]) -> "MetabolicPanel":
        """
        Process metabolic panel results (Creatinine, BUN, Glucose)
        """
        from app.models.labs import MetabolicPanel
        from app.utils.fhir_utils import extract_observations_by_loinc, get_most_recent_observation
        
        metabolic_panel = MetabolicPanel()
        
        # Creatinine (2160-0)
        creatinine_observations = extract_observations_by_loinc(entries, ["2160-0"])
        if creatinine_observations:
            most_recent_creatinine = get_most_recent_observation(creatinine_observations)
            if most_recent_creatinine:
                metabolic_panel.creatinine = self._create_lab_value(most_recent_creatinine, "2160-0")
        
        # BUN (3094-0)
        bun_observations = extract_observations_by_loinc(entries, ["3094-0"])
        if bun_observations:
            most_recent_bun = get_most_recent_observation(bun_observations)
            if most_recent_bun:
                metabolic_panel.blood_urea_nitrogen = self._create_lab_value(most_recent_bun, "3094-0")
        
        # Glucose (2345-7)
        glucose_observations = extract_observations_by_loinc(entries, ["2345-7"])
        if glucose_observations:
            most_recent_glucose = get_most_recent_observation(glucose_observations)
            if most_recent_glucose:
                metabolic_panel.glucose = self._create_lab_value(most_recent_glucose, "2345-7")
        
        return metabolic_panel
    
    def _process_liver_results(self, entries: List[Dict[str, Any]]) -> "LiverFunction":
        """
        Process liver function results (Bilirubin, Albumin, LDH)
        """
        from app.models.labs import LiverFunction
        from app.utils.fhir_utils import extract_observations_by_loinc, get_most_recent_observation
        
        liver_function = LiverFunction()
        
        # Bilirubin (1975-2)
        bilirubin_observations = extract_observations_by_loinc(entries, ["1975-2"])
        if bilirubin_observations:
            most_recent_bilirubin = get_most_recent_observation(bilirubin_observations)
            if most_recent_bilirubin:
                liver_function.bilirubin_total = self._create_lab_value(most_recent_bilirubin, "1975-2")
        
        # Albumin (1742-6)
        albumin_observations = extract_observations_by_loinc(entries, ["1742-6"])
        if albumin_observations:
            most_recent_albumin = get_most_recent_observation(albumin_observations)
            if most_recent_albumin:
                liver_function.albumin = self._create_lab_value(most_recent_albumin, "1742-6")
        
        # LDH (14804-9)
        ldh_observations = extract_observations_by_loinc(entries, ["14804-9"])
        if ldh_observations:
            most_recent_ldh = get_most_recent_observation(ldh_observations)
            if most_recent_ldh:
                liver_function.lactate_dehydrogenase = self._create_lab_value(most_recent_ldh, "14804-9")
        
        return liver_function
    
    def _process_inflammatory_results(self, entries: List[Dict[str, Any]]) -> "InflammatoryMarkers":
        """
        Process inflammatory markers (CRP, Procalcitonin)
        """
        from app.models.labs import InflammatoryMarkers
        from app.utils.fhir_utils import extract_observations_by_loinc, get_most_recent_observation
        
        inflammatory_markers = InflammatoryMarkers()
        
        # CRP (1988-5)
        crp_observations = extract_observations_by_loinc(entries, ["1988-5"])
        if crp_observations:
            most_recent_crp = get_most_recent_observation(crp_observations)
            if most_recent_crp:
                inflammatory_markers.c_reactive_protein = self._create_lab_value(most_recent_crp, "1988-5")
        
        # Procalcitonin (75241-0)
        procalcitonin_observations = extract_observations_by_loinc(entries, ["75241-0"])
        if procalcitonin_observations:
            most_recent_procalcitonin = get_most_recent_observation(procalcitonin_observations)
            if most_recent_procalcitonin:
                inflammatory_markers.procalcitonin = self._create_lab_value(most_recent_procalcitonin, "75241-0")
        
        return inflammatory_markers
    
    def _process_blood_gas_results(self, entries: List[Dict[str, Any]]) -> "BloodGas":
        """
        Process blood gas results (Lactate, pH, PaO2/FiO2)
        """
        from app.models.labs import BloodGas
        from app.utils.fhir_utils import extract_observations_by_loinc, get_most_recent_observation
        
        blood_gas = BloodGas()
        
        # Lactate (2019-8)
        lactate_observations = extract_observations_by_loinc(entries, ["2019-8"])
        if lactate_observations:
            most_recent_lactate = get_most_recent_observation(lactate_observations)
            if most_recent_lactate:
                blood_gas.lactate = self._create_lab_value(most_recent_lactate, "2019-8")
        
        # pH (2744-1)
        ph_observations = extract_observations_by_loinc(entries, ["2744-1"])
        if ph_observations:
            most_recent_ph = get_most_recent_observation(ph_observations)
            if most_recent_ph:
                blood_gas.ph = self._create_lab_value(most_recent_ph, "2744-1")
        
        # PaO2/FiO2 (50984-4)
        pao2_fio2_observations = extract_observations_by_loinc(entries, ["50984-4"])
        if pao2_fio2_observations:
            most_recent_pao2_fio2 = get_most_recent_observation(pao2_fio2_observations)
            if most_recent_pao2_fio2:
                blood_gas.pao2_fio2_ratio = self._create_lab_value(most_recent_pao2_fio2, "50984-4")
        
        return blood_gas
    
    def _process_coagulation_results(self, entries: List[Dict[str, Any]]) -> "Coagulation":
        """
        Process coagulation results (PT/INR, PTT)
        """
        from app.models.labs import Coagulation
        from app.utils.fhir_utils import extract_observations_by_loinc, get_most_recent_observation
        
        coagulation = Coagulation()
        
        # PT/INR (5902-2)
        inr_observations = extract_observations_by_loinc(entries, ["5902-2"])
        if inr_observations:
            most_recent_inr = get_most_recent_observation(inr_observations)
            if most_recent_inr:
                coagulation.inr = self._create_lab_value(most_recent_inr, "5902-2")
        
        # PTT (3173-2)
        ptt_observations = extract_observations_by_loinc(entries, ["3173-2"])
        if ptt_observations:
            most_recent_ptt = get_most_recent_observation(ptt_observations)
            if most_recent_ptt:
                coagulation.partial_thromboplastin_time = self._create_lab_value(most_recent_ptt, "3173-2")
        
        return coagulation
    
    def _create_lab_value(self, observation: Dict[str, Any], loinc_code: str) -> "LabValue":
        """
        Create LabValue from observation data
        """
        from app.models.labs import LabValue
        
        return LabValue(
            value=observation.get("value"),
            unit=observation.get("unit"),
            timestamp=observation.get("timestamp"),
            status=observation.get("status"),
            interpretation=observation.get("interpretation"),
            referenceRange=observation.get("reference_range"),
            loinc_code=loinc_code,
            display_name=observation.get("display_name")
        )

    def _process_encounter(self, entry: Dict[str, Any]) -> "Encounter":
        """
        Process FHIR encounter entry into Encounter model
        """
        from app.models.clinical import Encounter, Location, Period
        from app.utils.date_utils import parse_fhir_datetime
        
        encounter = Encounter(id=entry.get("id", ""))
        
        # Set basic encounter information
        encounter.status = entry.get("status")
        encounter.class_ = entry.get("class")
        
        # Process encounter type
        encounter.type = []
        if entry.get("type"):
            for type_item in entry["type"]:
                encounter.type.append(self._process_codeable_concept(type_item))
        
        # Process period
        if entry.get("period"):
            period_data = entry["period"]
            encounter.period = Period(
                start=parse_fhir_datetime(period_data.get("start")) if period_data.get("start") else None,
                end=parse_fhir_datetime(period_data.get("end")) if period_data.get("end") else None
            )
        
        # Process hospitalization
        if entry.get("hospitalization"):
            hospitalization = entry["hospitalization"]
            encounter.hospitalization = hospitalization
            
            # Extract admission source
            if hospitalization.get("admitSource"):
                admit_source = hospitalization["admitSource"]
                if admit_source.get("coding") and len(admit_source["coding"]) > 0:
                    encounter.admission_source = admit_source["coding"][0].get("display", "Unknown")
            
            # Extract discharge disposition
            if hospitalization.get("dischargeDisposition"):
                discharge_disp = hospitalization["dischargeDisposition"]
                if discharge_disp.get("coding") and len(discharge_disp["coding"]) > 0:
                    encounter.discharge_disposition = discharge_disp["coding"][0].get("display", "Unknown")
        
        # Process location
        encounter.location = []
        if entry.get("location"):
            for loc_item in entry["location"]:
                location = Location()
                
                if loc_item.get("location", {}).get("display"):
                    location.location = loc_item["location"]["display"]
                
                location.status = loc_item.get("status")
                
                if loc_item.get("period"):
                    period_data = loc_item["period"]
                    location.period = Period(
                        start=parse_fhir_datetime(period_data.get("start")) if period_data.get("start") else None,
                        end=parse_fhir_datetime(period_data.get("end")) if period_data.get("end") else None
                    )
                
                encounter.location.append(location)
        
        return encounter

    def _process_codeable_concept(self, concept: Dict[str, Any]) -> "CodeableConcept":
        """
        Process FHIR CodeableConcept into CodeableConcept model
        """
        from app.models.clinical import CodeableConcept, Coding
        
        codeable_concept = CodeableConcept()
        codeable_concept.text = concept.get("text")
        
        if concept.get("coding"):
            for coding_item in concept["coding"]:
                coding = Coding(
                    system=coding_item.get("system"),
                    code=coding_item.get("code"),
                    display=coding_item.get("display")
                )
                codeable_concept.coding.append(coding)
        
        return codeable_concept

    def _process_conditions(self, entries: List[Dict[str, Any]]) -> List["Condition"]:
        """
        Process FHIR condition entries into Condition models
        """
        from app.models.clinical import Condition
        from app.utils.date_utils import parse_fhir_datetime
        
        conditions = []
        
        for entry in entries:
            condition = Condition(id=entry.get("id", ""))
            
            # Set clinical status
            clinical_status = entry.get("clinicalStatus", {})
            if clinical_status.get("coding"):
                condition.clinical_status = clinical_status["coding"][0].get("code")
            
            # Set verification status
            verification_status = entry.get("verificationStatus", {})
            if verification_status.get("coding"):
                condition.verification_status = verification_status["coding"][0].get("code")
            
            # Set category
            condition.category = []
            if entry.get("category"):
                for category_item in entry["category"]:
                    if category_item.get("coding"):
                        for coding in category_item["coding"]:
                            condition.category.append(coding.get("code", ""))
            
            # Set severity
            if entry.get("severity"):
                severity = entry["severity"]
                if severity.get("coding"):
                    condition.severity = severity["coding"][0].get("code")
            
            # Set code
            if entry.get("code"):
                code_concept = entry["code"]
                if code_concept.get("coding"):
                    for coding in code_concept["coding"]:
                        if coding.get("system") == "http://hl7.org/fhir/sid/icd-10-cm":
                            condition.code = coding.get("code")
                            break
                    if not condition.code and code_concept["coding"]:
                        condition.code = code_concept["coding"][0].get("code")
                
                condition.code_text = code_concept.get("text")
            
            # Set subject
            if entry.get("subject", {}).get("reference"):
                condition.subject = entry["subject"]["reference"]
            
            # Set onset date
            if entry.get("onsetDateTime"):
                condition.onset_date_time = parse_fhir_datetime(entry["onsetDateTime"])
            
            # Set recorded date
            if entry.get("recordedDate"):
                condition.recorded_date = parse_fhir_datetime(entry["recordedDate"])
            
            # Set abatement date
            if entry.get("abatementDateTime"):
                condition.abatement_date_time = parse_fhir_datetime(entry["abatementDateTime"])
            
            conditions.append(condition)
        
        return conditions

    def _process_medications(self, entries: List[Dict[str, Any]]) -> List["Medication"]:
        """
        Process FHIR medication entries into Medication models
        """
        from app.models.clinical import Medication, Dosage
        from app.utils.date_utils import parse_fhir_datetime
        
        medications = []
        
        for entry in entries:
            # Skip non-MedicationRequest entries (like included Medication resources)
            if entry.get("resourceType") != "MedicationRequest":
                continue
            
            medication = Medication(id=entry.get("id", ""))
            
            # Set status
            medication.status = entry.get("status")
            
            # Set intent
            medication.intent = entry.get("intent")
            
            # Set authored date
            if entry.get("authoredOn"):
                medication.authored_on = parse_fhir_datetime(entry["authoredOn"])
            
            # Extract medication name
            medication_name = None
            if entry.get("medicationCodeableConcept"):
                med_concept = entry["medicationCodeableConcept"]
                if med_concept.get("coding"):
                    medication_name = med_concept["coding"][0].get("display")
                elif med_concept.get("text"):
                    medication_name = med_concept["text"]
            elif entry.get("medicationReference", {}).get("display"):
                medication_name = entry["medicationReference"]["display"]
            
            medication.medication_name = medication_name
            
            # Process dosage instructions
            medication.dosage_instruction = []
            if entry.get("dosageInstruction"):
                for dosage_item in entry["dosageInstruction"]:
                    dosage = Dosage()
                    dosage.text = dosage_item.get("text")
                    dosage.timing = dosage_item.get("timing")
                    dosage.dose_and_rate = dosage_item.get("doseAndRate")
                    
                    # Extract route
                    if dosage_item.get("route"):
                        route_concept = dosage_item["route"]
                        if route_concept.get("coding"):
                            dosage.route = route_concept["coding"][0].get("display")
                        elif route_concept.get("text"):
                            dosage.route = route_concept["text"]
                    
                    medication.dosage_instruction.append(dosage)
            
            # Classify medication type
            medication.is_antibiotic = self._is_antibiotic_medication(medication_name)
            medication.is_vasopressor = self._is_vasopressor_medication(medication_name)
            
            medications.append(medication)
        
        return medications

    def _is_antibiotic_medication(self, medication_name: Optional[str]) -> bool:
        """
        Check if medication is an antibiotic based on name
        """
        if not medication_name:
            return False
        
        medication_name = medication_name.lower()
        antibiotic_keywords = [
            "antibiotic", "antimicrobial", "penicillin", "amoxicillin", "cephalexin",
            "ciprofloxacin", "levofloxacin", "azithromycin", "clindamycin", "vancomycin",
            "metronidazole", "doxycycline", "tetracycline", "erythromycin", "clarithromycin",
            "ceftriaxone", "cefuroxime", "cephalosporin", "quinolone", "macrolide",
            "lincomycin", "sulfonamide", "trimethoprim", "sulfamethoxazole", "cefazolin",
            "ampicillin", "piperacillin", "tazobactam", "meropenem", "imipenem",
            "gentamicin", "tobramycin", "streptomycin", "neomycin", "rifampin"
        ]
        
        return any(keyword in medication_name for keyword in antibiotic_keywords)

    def _is_vasopressor_medication(self, medication_name: Optional[str]) -> bool:
        """
        Check if medication is a vasopressor based on name
        """
        if not medication_name:
            return False
        
        medication_name = medication_name.lower()
        vasopressor_keywords = [
            "norepinephrine", "epinephrine", "dopamine", "dobutamine", "vasopressin",
            "phenylephrine", "ephedrine", "midodrine", "methoxamine", "levophed",
            "adrenaline", "noradrenaline", "pitressin", "neo-synephrine"
        ]
        
        return any(keyword in medication_name for keyword in vasopressor_keywords)

    def _process_fluid_balance(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process FHIR fluid balance observations into FluidBalanceResponse data
        """
        from app.models.clinical import FluidObservation
        from app.utils.fhir_utils import extract_observations_by_loinc
        
        fluid_intake = []
        urine_output = []
        
        # Process observations by LOINC code
        observations = extract_observations_by_loinc(entries, ["9192-6", "9187-6", "9188-4"])
        
        for obs in observations:
            fluid_obs = FluidObservation(
                value=obs.get("value"),
                unit=obs.get("unit"),
                timestamp=obs.get("timestamp"),
                category=self._categorize_fluid_observation(obs.get("loinc_code"))
            )
            
            loinc_code = obs.get("loinc_code")
            if loinc_code == "9192-6":  # Fluid intake
                fluid_intake.append(fluid_obs)
            elif loinc_code in ["9187-6", "9188-4"]:  # Urine output
                urine_output.append(fluid_obs)
        
        # Calculate fluid balance
        fluid_balance = self._calculate_fluid_balance(fluid_intake, urine_output)
        
        return {
            "fluid_intake": fluid_intake,
            "urine_output": urine_output,
            "fluid_balance": fluid_balance
        }

    def _categorize_fluid_observation(self, loinc_code: Optional[str]) -> str:
        """
        Categorize fluid observation based on LOINC code
        """
        if loinc_code == "9192-6":
            return "intake"
        elif loinc_code == "9187-6":
            return "urine_output"
        elif loinc_code == "9188-4":
            return "urine_output_catheter"
        else:
            return "unknown"

    def _calculate_fluid_balance(self, fluid_intake: List["FluidObservation"], urine_output: List["FluidObservation"]) -> Optional[float]:
        """
        Calculate net fluid balance
        """
        total_intake = sum(obs.value for obs in fluid_intake if obs.value is not None)
        total_output = sum(obs.value for obs in urine_output if obs.value is not None)
        
        if total_intake > 0 or total_output > 0:
            return total_intake - total_output
        
        return None