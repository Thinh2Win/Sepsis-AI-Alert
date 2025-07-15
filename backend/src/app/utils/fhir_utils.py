from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from app.core.loinc_codes import LOINCCodes
from app.utils.date_utils import parse_fhir_datetime

def extract_observation_value(observation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract value from FHIR Observation resource
    
    Args:
        observation: FHIR Observation resource
    
    Returns:
        Dictionary with value, unit, and other metadata
    """
    if not observation or observation.get("resourceType") != "Observation":
        return None
    
    result = {
        "value": None,
        "unit": None,
        "timestamp": None,
        "status": observation.get("status"),
        "interpretation": None,
        "reference_range": None
    }
    
    # Extract timestamp
    effective_datetime = observation.get("effectiveDateTime") or observation.get("issued")
    if effective_datetime:
        result["timestamp"] = parse_fhir_datetime(effective_datetime)
    
    # Extract value based on type
    if "valueQuantity" in observation:
        qty = observation["valueQuantity"]
        result["value"] = qty.get("value")
        result["unit"] = qty.get("unit") or qty.get("code")
    elif "valueString" in observation:
        result["value"] = observation["valueString"]
    elif "valueBoolean" in observation:
        result["value"] = observation["valueBoolean"]
    elif "valueInteger" in observation:
        result["value"] = observation["valueInteger"]
    elif "valueCodeableConcept" in observation:
        concept = observation["valueCodeableConcept"]
        result["value"] = concept.get("text")
        if not result["value"] and concept.get("coding"):
            result["value"] = concept["coding"][0].get("display")
    
    # Extract interpretation
    if "interpretation" in observation:
        interpretations = observation["interpretation"]
        if isinstance(interpretations, list) and interpretations:
            interp = interpretations[0]
            if "coding" in interp and interp["coding"]:
                result["interpretation"] = interp["coding"][0].get("code")
            elif "text" in interp:
                result["interpretation"] = interp["text"]
    
    # Extract reference range
    if "referenceRange" in observation:
        ref_ranges = observation["referenceRange"]
        if isinstance(ref_ranges, list) and ref_ranges:
            ref_range = ref_ranges[0]
            low = ref_range.get("low", {}).get("value")
            high = ref_range.get("high", {}).get("value")
            if low is not None and high is not None:
                result["reference_range"] = f"{low}-{high}"
            elif low is not None:
                result["reference_range"] = f"≥{low}"
            elif high is not None:
                result["reference_range"] = f"≤{high}"
    
    return result

def extract_observations_by_loinc(bundle: Dict[str, Any], loinc_codes: Union[str, List[str]]) -> List[Dict[str, Any]]:
    """
    Extract observations from FHIR Bundle by LOINC codes
    
    Args:
        bundle: FHIR Bundle resource
        loinc_codes: Single LOINC code or list of codes
    
    Returns:
        List of extracted observations
    """
    if isinstance(loinc_codes, str):
        loinc_codes = [loinc_codes]
    
    observations = []
    
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "Observation":
            continue
        
        # Check if observation has matching LOINC code
        code = resource.get("code", {})
        for coding in code.get("coding", []):
            if coding.get("system") == "http://loinc.org" and coding.get("code") in loinc_codes:
                extracted = extract_observation_value(resource)
                if extracted and extracted["value"] is not None:
                    extracted["loinc_code"] = coding.get("code")
                    extracted["display_name"] = coding.get("display")
                    observations.append(extracted)
                break
    
    return observations

def get_most_recent_observation(observations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Get the most recent observation from a list
    
    Args:
        observations: List of observations
    
    Returns:
        Most recent observation or None
    """
    if not observations:
        return None
    
    # Filter out observations without timestamps
    valid_observations = [obs for obs in observations if obs.get("timestamp")]
    
    if not valid_observations:
        return observations[0]  # Return first if no timestamps
    
    return max(valid_observations, key=lambda x: x["timestamp"])

def group_observations_by_loinc(observations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group observations by LOINC code
    
    Args:
        observations: List of observations
    
    Returns:
        Dictionary grouped by LOINC code
    """
    grouped = {}
    
    for obs in observations:
        loinc_code = obs.get("loinc_code")
        if loinc_code:
            if loinc_code not in grouped:
                grouped[loinc_code] = []
            grouped[loinc_code].append(obs)
    
    return grouped

def extract_patient_demographics(patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract demographics from FHIR Patient resource
    
    Args:
        patient: FHIR Patient resource
    
    Returns:
        Dictionary with demographic information
    """
    demographics = {
        "id": patient.get("id"),
        "active": patient.get("active"),
        "gender": patient.get("gender"),
        "birth_date": None,
        "names": [],
        "addresses": [],
        "telecoms": [],
        "identifiers": []
    }
    
    # Extract birth date
    if "birthDate" in patient:
        birth_date_str = patient["birthDate"]
        demographics["birth_date"] = parse_fhir_datetime(birth_date_str + "T00:00:00") if birth_date_str else None
    
    # Extract names
    for name in patient.get("name", []):
        name_info = {
            "family": name.get("family"),
            "given": name.get("given", []),
            "use": name.get("use"),
            "text": name.get("text")
        }
        demographics["names"].append(name_info)
    
    # Extract addresses
    for address in patient.get("address", []):
        addr_info = {
            "line": address.get("line", []),
            "city": address.get("city"),
            "state": address.get("state"),
            "postal_code": address.get("postalCode"),
            "country": address.get("country"),
            "use": address.get("use")
        }
        demographics["addresses"].append(addr_info)
    
    # Extract telecoms
    for telecom in patient.get("telecom", []):
        telecom_info = {
            "system": telecom.get("system"),
            "value": telecom.get("value"),
            "use": telecom.get("use")
        }
        demographics["telecoms"].append(telecom_info)
    
    # Extract identifiers
    for identifier in patient.get("identifier", []):
        id_info = {
            "use": identifier.get("use"),
            "type": identifier.get("type"),
            "system": identifier.get("system"),
            "value": identifier.get("value")
        }
        demographics["identifiers"].append(id_info)
    
    return demographics

def is_abnormal_observation(observation: Dict[str, Any]) -> bool:
    """
    Check if observation is abnormal based on interpretation codes
    
    Args:
        observation: Observation dictionary
    
    Returns:
        True if abnormal
    """
    interpretation = observation.get("interpretation", "").upper()
    abnormal_codes = ["H", "HH", "L", "LL", "A", "AA", "CRITICAL", "PANIC"]
    return interpretation in abnormal_codes

def is_critical_observation(observation: Dict[str, Any]) -> bool:
    """
    Check if observation is critical based on interpretation codes
    
    Args:
        observation: Observation dictionary
    
    Returns:
        True if critical
    """
    interpretation = observation.get("interpretation", "").upper()
    critical_codes = ["HH", "LL", "AA", "CRITICAL", "PANIC"]
    return interpretation in critical_codes

def extract_encounter_info(encounter: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract encounter information from FHIR Encounter resource
    
    Args:
        encounter: FHIR Encounter resource
    
    Returns:
        Dictionary with encounter information
    """
    encounter_info = {
        "id": encounter.get("id"),
        "status": encounter.get("status"),
        "class": None,
        "type": [],
        "period": None,
        "hospitalization": encounter.get("hospitalization"),
        "locations": []
    }
    
    # Extract class
    if "class" in encounter:
        encounter_info["class"] = encounter["class"].get("display") or encounter["class"].get("code")
    
    # Extract types
    for enc_type in encounter.get("type", []):
        type_info = enc_type.get("text")
        if not type_info and enc_type.get("coding"):
            type_info = enc_type["coding"][0].get("display")
        if type_info:
            encounter_info["type"].append(type_info)
    
    # Extract period
    if "period" in encounter:
        period = encounter["period"]
        encounter_info["period"] = {
            "start": parse_fhir_datetime(period.get("start")) if period.get("start") else None,
            "end": parse_fhir_datetime(period.get("end")) if period.get("end") else None
        }
    
    # Extract locations
    for location in encounter.get("location", []):
        loc_info = {
            "location": location.get("location", {}).get("display"),
            "status": location.get("status"),
            "period": None
        }
        if "period" in location:
            period = location["period"]
            loc_info["period"] = {
                "start": parse_fhir_datetime(period.get("start")) if period.get("start") else None,
                "end": parse_fhir_datetime(period.get("end")) if period.get("end") else None
            }
        encounter_info["locations"].append(loc_info)
    
    return encounter_info

def build_observation_query_params(
    patient_id: str,
    loinc_codes: List[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category: Optional[str] = None,
    sort: str = "-date",
    count: Optional[int] = None
) -> Dict[str, str]:
    """
    Build query parameters for FHIR Observation search
    
    Args:
        patient_id: Patient ID
        loinc_codes: List of LOINC codes
        start_date: Start date for observations
        end_date: End date for observations
        category: Observation category
        sort: Sort parameter
        count: Maximum number of results
    
    Returns:
        Dictionary of query parameters
    """
    params = {
        "patient": patient_id,
        "code": ",".join(loinc_codes),
        "_sort": sort
    }
    
    if category:
        params["category"] = category
    
    if start_date:
        params["date"] = f"ge{start_date.strftime('%Y-%m-%dT%H:%M:%S')}"
    
    if end_date:
        date_param = params.get("date", "")
        if date_param:
            params["date"] = f"{date_param}&date=le{end_date.strftime('%Y-%m-%dT%H:%M:%S')}"
        else:
            params["date"] = f"le{end_date.strftime('%Y-%m-%dT%H:%M:%S')}"
    
    if count:
        params["_count"] = str(count)
    
    return params