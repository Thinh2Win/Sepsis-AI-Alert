"""
FHIR response fixtures for testing.
"""

from typing import Dict, Any, List
from datetime import datetime


def patient_response(patient_id: str = "test-patient-123") -> Dict[str, Any]:
    """Sample FHIR Patient resource response."""
    return {
        "resourceType": "Patient",
        "id": patient_id,
        "active": True,
        "name": [
            {
                "use": "official",
                "family": "Doe",
                "given": ["John"],
                "text": "John Doe"
            }
        ],
        "telecom": [
            {
                "system": "phone",
                "value": "+1-555-123-4567",
                "use": "home"
            },
            {
                "system": "email", 
                "value": "john.doe@example.com"
            }
        ],
        "gender": "male",
        "birthDate": "1980-01-01",
        "address": [
            {
                "use": "home",
                "line": ["123 Main St"],
                "city": "Anytown",
                "state": "CA",
                "postalCode": "12345",
                "country": "US"
            }
        ],
        "identifier": [
            {
                "use": "usual",
                "type": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "MR",
                            "display": "Medical Record Number"
                        }
                    ]
                },
                "system": "http://hospital.example.org",
                "value": "MRN123456"
            }
        ],
        "maritalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                    "code": "M",
                    "display": "Married"
                }
            ]
        }
    }


def observation_response(loinc_code: str, value: float, unit: str, 
                        timestamp: str = "2023-01-01T12:00:00Z",
                        patient_id: str = "test-patient-123") -> Dict[str, Any]:
    """Sample FHIR Observation resource response."""
    return {
        "resourceType": "Observation",
        "id": f"obs-{loinc_code}-{int(datetime.now().timestamp())}",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": loinc_code,
                    "display": get_loinc_display(loinc_code)
                }
            ]
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": timestamp,
        "valueQuantity": {
            "value": value,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit
        },
        "interpretation": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "N",
                        "display": "Normal"
                    }
                ]
            }
        ]
    }


def bundle_response(entries: List[Dict[str, Any]], total: int = None) -> Dict[str, Any]:
    """Sample FHIR Bundle response."""
    if total is None:
        total = len(entries)
    
    return {
        "resourceType": "Bundle",
        "id": f"bundle-{int(datetime.now().timestamp())}",
        "type": "searchset",
        "total": total,
        "entry": [
            {
                "fullUrl": f"https://fhir.server/{entry['resourceType']}/{entry['id']}",
                "resource": entry
            }
            for entry in entries
        ]
    }


def vitals_bundle_response(patient_id: str = "test-patient-123") -> Dict[str, Any]:
    """Sample FHIR Bundle with vital signs observations."""
    observations = [
        observation_response("8867-4", 72, "beats/min", "2023-01-01T12:00:00Z", patient_id),  # Heart Rate
        observation_response("8480-6", 120, "mmHg", "2023-01-01T12:00:00Z", patient_id),     # Systolic BP
        observation_response("8462-4", 80, "mmHg", "2023-01-01T12:00:00Z", patient_id),      # Diastolic BP
        observation_response("8310-5", 98.6, "°F", "2023-01-01T12:00:00Z", patient_id),     # Temperature
        observation_response("9279-1", 16, "breaths/min", "2023-01-01T12:00:00Z", patient_id), # Respiratory Rate
        observation_response("2708-6", 98, "%", "2023-01-01T12:00:00Z", patient_id),         # Oxygen Saturation
    ]
    return bundle_response(observations)


def labs_bundle_response(patient_id: str = "test-patient-123") -> Dict[str, Any]:
    """Sample FHIR Bundle with lab observations."""
    observations = [
        observation_response("6690-2", 8.5, "10*3/uL", "2023-01-01T12:00:00Z", patient_id),  # WBC
        observation_response("777-3", 250, "10*3/uL", "2023-01-01T12:00:00Z", patient_id),   # Platelets
        observation_response("2160-0", 1.0, "mg/dL", "2023-01-01T12:00:00Z", patient_id),    # Creatinine
        observation_response("2345-7", 95, "mg/dL", "2023-01-01T12:00:00Z", patient_id),     # Glucose
        observation_response("1988-5", 2.5, "mg/L", "2023-01-01T12:00:00Z", patient_id),     # CRP
    ]
    return bundle_response(observations)


def encounter_response(patient_id: str = "test-patient-123") -> Dict[str, Any]:
    """Sample FHIR Encounter resource response."""
    return {
        "resourceType": "Encounter",
        "id": "encounter-123",
        "status": "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "IMP",
            "display": "inpatient encounter"
        },
        "type": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "32485007",
                        "display": "Hospital admission"
                    }
                ]
            }
        ],
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "period": {
            "start": "2023-01-01T08:00:00Z"
        },
        "location": [
            {
                "location": {
                    "display": "ICU Room 101"
                },
                "status": "active",
                "period": {
                    "start": "2023-01-01T08:00:00Z"
                }
            }
        ],
        "hospitalization": {
            "admitSource": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/admit-source",
                        "code": "emd",
                        "display": "Emergency Department"
                    }
                ]
            }
        }
    }


def condition_response(patient_id: str = "test-patient-123") -> Dict[str, Any]:
    """Sample FHIR Condition resource response."""
    return {
        "resourceType": "Condition",
        "id": "condition-sepsis-123",
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active"
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed"
                }
            ]
        },
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                        "code": "encounter-diagnosis"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "A41.9",
                    "display": "Sepsis, unspecified organism"
                }
            ],
            "text": "Sepsis"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "onsetDateTime": "2023-01-01T10:00:00Z",
        "recordedDate": "2023-01-01T10:00:00Z"
    }


def operation_outcome_error(severity: str = "error", code: str = "forbidden", 
                           diagnostics: str = "Access denied") -> Dict[str, Any]:
    """Sample FHIR OperationOutcome for error responses."""
    return {
        "resourceType": "OperationOutcome",
        "issue": [
            {
                "severity": severity,
                "code": code,
                "diagnostics": diagnostics
            }
        ]
    }


def get_loinc_display(loinc_code: str) -> str:
    """Get display name for LOINC code."""
    loinc_displays = {
        "8867-4": "Heart rate",
        "8480-6": "Systolic blood pressure",
        "8462-4": "Diastolic blood pressure",
        "8310-5": "Body temperature",
        "9279-1": "Respiratory rate",
        "2708-6": "Oxygen saturation in Arterial blood",
        "9269-2": "Glasgow coma score total",
        "6690-2": "Leukocytes [#/volume] in Blood by Automated count",
        "777-3": "Platelets [#/volume] in Blood by Automated count",
        "2160-0": "Creatinine [Mass/volume] in Serum or Plasma",
        "2345-7": "Glucose [Mass/volume] in Serum or Plasma",
        "1988-5": "C reactive protein [Mass/volume] in Serum or Plasma",
        "3094-0": "Urea nitrogen [Mass/volume] in Serum or Plasma",
        "1975-2": "Bilirubin.total [Mass/volume] in Serum or Plasma",
        "1742-6": "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma",
        "2019-8": "Lactate [Mass/volume] in Venous blood",
        "2744-1": "pH of Arterial blood",
        "5902-2": "Prothrombin time (PT)",
        "3173-2": "Partial thromboplastin time (PTT)",
    }
    return loinc_displays.get(loinc_code, f"LOINC {loinc_code}")