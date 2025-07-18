# Sepsis AI Alert System - API Documentation

## Overview

This document provides comprehensive API documentation for the Sepsis AI Alert System endpoints, which integrate with Epic FHIR R4 to retrieve patient data for sepsis detection and clinical decision support.

## Base URL

```
http://localhost:8000/api/v1/sepsis-alert
```

## Authentication

All endpoints require OAuth2 JWT authentication with Epic FHIR:

```
Authorization: Bearer <token>
Accept: application/fhir+json
```

---

## Patient Endpoints

### Get Patient Demographics

**Purpose:** Retrieve patient demographics and basic information from Epic FHIR R4.

**HTTP Method & URL:** `GET /patients/{patient_id}`

**Path Parameters:**
- `patient_id` (string, required) - FHIR Patient resource ID (not MRN)

**Query Parameters:** None

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Accept: application/fhir+json` (required)

**Request Body:** None

**Response:**
- **Success:** 200 OK
- **Body Schema:** PatientResponse model with computed fields
  ```json
  {
    "id": "string",
    "name": {
      "given": ["string"],
      "family": "string"
    },
    "gender": "string",
    "birth_date": "YYYY-MM-DD",
    "age": 45,
    "height": 175.0,
    "weight": 70.0,
    "bmi": 22.9,
    "primary_contact": {
      "name": "string",
      "relationship": "string",
      "phone": "string"
    },
    "address": {
      "line": ["string"],
      "city": "string",
      "state": "string",
      "postal_code": "string"
    }
  }
  ```

**Error Responses:**
- **400 Bad Request:** Invalid patient ID format
- **401 Unauthorized:** Invalid or expired token
- **404 Not Found:** Patient not found
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** FHIR service error

**Example:**
```bash
curl -X GET \
  "http://localhost:8000/api/v1/sepsis-alert/patients/e74Q2ey-kqeOCXXuE5Q4nQB" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..." \
  -H "Accept: application/fhir+json"
```

**Notes:**
- Age is calculated from birth_date
- BMI is computed from height/weight observations
- Primary contact is extracted from Patient.contact array

---

### Match Patient by Demographics

**Purpose:** Match patient using demographic information to find FHIR Patient ID.

**HTTP Method & URL:** `POST /patients/match`

**Path Parameters:** None

**Query Parameters:** None

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Accept: application/fhir+json` (required)
- `Content-Type: application/json` (required)

**Request Body:**
```json
{
  "given": "string",
  "family": "string",
  "birthDate": "YYYY-MM-DD",
  "phone": "string (optional)",
  "address": {
    "line": ["string"],
    "city": "string",
    "state": "string",
    "postalCode": "string",
    "country": "string",
    "use": "string"
  }
}
```

**Response:**
- **Success:** 200 OK
- **Body Schema:** PatientMatchResponse model
  ```json
  {
    "resourceType": "Bundle",
    "total": 1,
    "entry": [
      {
        "resource": {
          "id": "string",
          "name": [
            {
              "family": "string",
              "given": ["string"],
              "use": "official"
            }
          ],
          "birthDate": "YYYY-MM-DD",
          "gender": "string",
          "telecom": [
            {
              "system": "phone",
              "value": "string",
              "use": "home"
            }
          ],
          "address": [
            {
              "line": ["string"],
              "city": "string",
              "state": "string",
              "postalCode": "string",
              "country": "string",
              "use": "home"
            }
          ],
          "age": 77,
          "primary_name": "string",
          "primary_phone": "string",
          "primary_address": "string"
        },
        "search": {
          "mode": "match",
          "score": 1.0,
          "extension": [
            {
              "valueCode": "certain",
              "url": "http://hl7.org/fhir/StructureDefinition/match-grade"
            }
          ]
        }
      }
    ]
  }
  ```

**Error Responses:**
- **400 Bad Request:** Invalid request body or missing required fields
- **401 Unauthorized:** Invalid or expired token
- **422 Unprocessable Entity:** Validation error
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** FHIR service error

**Example:**
```bash
curl -X POST \
  "http://localhost:8000/api/v1/sepsis-alert/patients/match" \
  -H "Content-Type: application/json" \
  -d '{
    "given": "Theodore",
    "family": "Mychart",
    "birthDate": "1948-07-07",
    "phone": "+1 608-213-5806",
    "address": {
      "line": ["134 Elmstreet"],
      "city": "Madison",
      "state": "WI",
      "postalCode": null,
      "country": "US",
      "use": "home"
    }
  }'
```

**Notes:**
- Uses FHIR Patient.$match operation with `onlyCertainMatches: true`
- Returns Bundle with matched Patient resources and confidence scores
- Match score ranges from 0.0 to 1.0 (1.0 = perfect match)
- Match grade extension indicates certainty level ("certain", "probable", "possible")
- Supports patient matching based on name, birth date, phone, and address

---

## Vital Signs Endpoints

### Get Patient Vital Signs

**Purpose:** Retrieve patient vital signs within date range with optional filtering by vital type.

**HTTP Method & URL:** `GET /patients/{patient_id}/vitals`

**Path Parameters:**
- `patient_id` (string, required) - FHIR Patient resource ID

**Query Parameters:**
- `start_date` (datetime, optional) - Start date for vital signs (ISO format: YYYY-MM-DDTHH:MM:SS)
- `end_date` (datetime, optional) - End date for vital signs (ISO format: YYYY-MM-DDTHH:MM:SS)
- `vital_type` (string, optional) - Specific vital sign type:
  - `HR`: Heart Rate (LOINC: 8867-4)
  - `BP`: Blood Pressure (LOINC: 85354-9, 8480-6, 8462-4)
  - `TEMP`: Temperature (LOINC: 8310-5)
  - `RR`: Respiratory Rate (LOINC: 9279-1)
  - `SPO2`: Oxygen Saturation (LOINC: 2708-6, 59408-5)
  - `GCS`: Glasgow Coma Score (LOINC: 9269-2)

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Accept: application/fhir+json` (required)

**Request Body:** None

**Response:**
- **Success:** 200 OK
- **Body Schema:** VitalSignsResponse model
  ```json
  {
    "patient_id": "string",
    "date_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-02T00:00:00Z"
    },
    "vital_signs": {
      "heart_rate": [
        {
          "timestamp": "2024-01-01T12:00:00Z",
          "value": 80,
          "unit": "beats/min",
          "interpretation": "normal",
          "sepsis_score": 0
        }
      ],
      "blood_pressure": [
        {
          "timestamp": "2024-01-01T12:00:00Z",
          "systolic": 120,
          "diastolic": 80,
          "mean_arterial_pressure": 93.3,
          "pulse_pressure": 40,
          "unit": "mmHg",
          "interpretation": "normal",
          "sepsis_score": 0
        }
      ],
      "temperature": [
        {
          "timestamp": "2024-01-01T12:00:00Z",
          "value": 36.5,
          "unit": "°C",
          "interpretation": "normal",
          "fever_detected": false,
          "sepsis_score": 0
        }
      ],
      "respiratory_rate": [
        {
          "timestamp": "2024-01-01T12:00:00Z",
          "value": 16,
          "unit": "breaths/min",
          "interpretation": "normal",
          "sepsis_score": 0
        }
      ],
      "oxygen_saturation": [
        {
          "timestamp": "2024-01-01T12:00:00Z",
          "value": 98,
          "unit": "%",
          "interpretation": "normal",
          "hypoxia_detected": false,
          "sepsis_score": 0
        }
      ],
      "glasgow_coma_score": [
        {
          "timestamp": "2024-01-01T12:00:00Z",
          "value": 15,
          "interpretation": "normal",
          "severity": "none",
          "sepsis_score": 0
        }
      ]
    }
  }
  ```

**Error Responses:**
- **400 Bad Request:** Invalid patient ID or date format
- **401 Unauthorized:** Invalid or expired token
- **404 Not Found:** Patient not found
- **422 Unprocessable Entity:** Invalid vital_type parameter
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** FHIR service error

**Example:**
```bash
curl -X GET \
  "http://localhost:8000/api/v1/sepsis-alert/patients/e74Q2ey-kqeOCXXuE5Q4nQB/vitals?start_date=2024-01-01T00:00:00Z&end_date=2024-01-02T00:00:00Z&vital_type=HR" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..." \
  -H "Accept: application/fhir+json"
```

**Notes:**
- If no vital_type is specified, all vital signs are fetched concurrently
- Supports time-series data with clinical interpretation
- Includes sepsis scoring for each vital sign
- Uses FHIR Observation.Search with date range filtering

---

### Get Latest Vital Signs

**Purpose:** Retrieve most recent vital signs for patient (latest value for each vital sign type).

**HTTP Method & URL:** `GET /patients/{patient_id}/vitals/latest`

**Path Parameters:**
- `patient_id` (string, required) - FHIR Patient resource ID

**Query Parameters:** None

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Accept: application/fhir+json` (required)

**Request Body:** None

**Response:**
- **Success:** 200 OK
- **Body Schema:** VitalSignsLatestResponse model
  ```json
  {
    "patient_id": "string",
    "latest_vitals": {
      "heart_rate": {
        "timestamp": "2024-01-01T12:00:00Z",
        "value": 80,
        "unit": "beats/min",
        "interpretation": "normal",
        "sepsis_score": 0
      },
      "blood_pressure": {
        "timestamp": "2024-01-01T12:00:00Z",
        "systolic": 120,
        "diastolic": 80,
        "mean_arterial_pressure": 93.3,
        "pulse_pressure": 40,
        "unit": "mmHg",
        "interpretation": "normal",
        "sepsis_score": 0
      },
      "temperature": {
        "timestamp": "2024-01-01T12:00:00Z",
        "value": 36.5,
        "unit": "°C",
        "interpretation": "normal",
        "fever_detected": false,
        "sepsis_score": 0
      },
      "respiratory_rate": {
        "timestamp": "2024-01-01T12:00:00Z",
        "value": 16,
        "unit": "breaths/min",
        "interpretation": "normal",
        "sepsis_score": 0
      },
      "oxygen_saturation": {
        "timestamp": "2024-01-01T12:00:00Z",
        "value": 98,
        "unit": "%",
        "interpretation": "normal",
        "hypoxia_detected": false,
        "sepsis_score": 0
      },
      "glasgow_coma_score": {
        "timestamp": "2024-01-01T12:00:00Z",
        "value": 15,
        "interpretation": "normal",
        "severity": "none",
        "sepsis_score": 0
      }
    }
  }
  ```

**Error Responses:**
- **400 Bad Request:** Invalid patient ID format
- **401 Unauthorized:** Invalid or expired token
- **404 Not Found:** Patient not found
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** FHIR service error

**Example:**
```bash
curl -X GET \
  "http://localhost:8000/api/v1/sepsis-alert/patients/e74Q2ey-kqeOCXXuE5Q4nQB/vitals/latest" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..." \
  -H "Accept: application/fhir+json"
```

**Notes:**
- Uses concurrent FHIR calls with `_count=1` parameter
- Returns null for vital signs with no available data
- Optimized for real-time clinical dashboards

---

## Laboratory Results Endpoints

### Get Patient Laboratory Results

**Purpose:** Retrieve patient laboratory results within date range with optional category filtering.

**HTTP Method & URL:** `GET /patients/{patient_id}/labs`

**Path Parameters:**
- `patient_id` (string, required) - FHIR Patient resource ID

**Query Parameters:**
- `start_date` (datetime, optional) - Start date for lab results (ISO format: YYYY-MM-DDTHH:MM:SS)
- `end_date` (datetime, optional) - End date for lab results (ISO format: YYYY-MM-DDTHH:MM:SS)
- `lab_category` (string, optional) - Lab category filter:
  - `CBC`: WBC Count (LOINC: 6690-2), Platelet Count (LOINC: 777-3)
  - `METABOLIC`: Creatinine (LOINC: 2160-0), BUN (LOINC: 3094-0), Glucose (LOINC: 2345-7)
  - `LIVER`: Bilirubin (LOINC: 1975-2), Albumin (LOINC: 1742-6), LDH (LOINC: 14804-9)
  - `INFLAMMATORY`: CRP (LOINC: 1988-5), Procalcitonin (LOINC: 75241-0)
  - `BLOOD_GAS`: Lactate (LOINC: 2019-8), pH (LOINC: 2744-1), PaO2/FiO2 (LOINC: 50984-4)
  - `COAGULATION`: PT/INR (LOINC: 5902-2), PTT (LOINC: 3173-2)

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Accept: application/fhir+json` (required)

**Request Body:** None

**Response:**
- **Success:** 200 OK
- **Body Schema:** LabResultsResponse model
  ```json
  {
    "patient_id": "string",
    "date_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-02T00:00:00Z"
    },
    "lab_results": {
      "cbc": {
        "wbc_count": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 8.5,
            "unit": "10^9/L",
            "reference_range": "4.0-11.0",
            "interpretation": "normal",
            "infection_indicator": false,
            "sepsis_score": 0
          }
        ],
        "platelet_count": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 250,
            "unit": "10^9/L",
            "reference_range": "150-450",
            "interpretation": "normal",
            "sepsis_score": 0
          }
        ]
      },
      "metabolic": {
        "creatinine": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 1.0,
            "unit": "mg/dL",
            "reference_range": "0.7-1.3",
            "interpretation": "normal",
            "kidney_dysfunction": false,
            "sepsis_score": 0
          }
        ],
        "bun": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 15,
            "unit": "mg/dL",
            "reference_range": "7-20",
            "interpretation": "normal",
            "sepsis_score": 0
          }
        ],
        "glucose": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 90,
            "unit": "mg/dL",
            "reference_range": "70-100",
            "interpretation": "normal",
            "sepsis_score": 0
          }
        ]
      },
      "liver": {
        "bilirubin": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 1.0,
            "unit": "mg/dL",
            "reference_range": "0.3-1.2",
            "interpretation": "normal",
            "liver_dysfunction": false,
            "sepsis_score": 0
          }
        ],
        "albumin": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 4.0,
            "unit": "g/dL",
            "reference_range": "3.5-5.0",
            "interpretation": "normal",
            "sepsis_score": 0
          }
        ]
      },
      "inflammatory": {
        "crp": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 2.0,
            "unit": "mg/L",
            "reference_range": "<3.0",
            "interpretation": "normal",
            "sepsis_likelihood": "low",
            "sepsis_score": 0
          }
        ],
        "procalcitonin": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 0.1,
            "unit": "ng/mL",
            "reference_range": "<0.25",
            "interpretation": "normal",
            "sepsis_likelihood": "low",
            "sepsis_score": 0
          }
        ]
      },
      "blood_gas": {
        "lactate": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 1.5,
            "unit": "mmol/L",
            "reference_range": "0.5-2.2",
            "interpretation": "normal",
            "hyperlactatemia": false,
            "sepsis_score": 0
          }
        ],
        "ph": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 7.40,
            "unit": "pH",
            "reference_range": "7.35-7.45",
            "interpretation": "normal",
            "acidosis": false,
            "sepsis_score": 0
          }
        ]
      },
      "coagulation": {
        "pt_inr": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 1.0,
            "unit": "INR",
            "reference_range": "0.8-1.2",
            "interpretation": "normal",
            "coagulopathy": false,
            "sepsis_score": 0
          }
        ],
        "ptt": [
          {
            "timestamp": "2024-01-01T12:00:00Z",
            "value": 30,
            "unit": "sec",
            "reference_range": "25-35",
            "interpretation": "normal",
            "sepsis_score": 0
          }
        ]
      }
    }
  }
  ```

**Error Responses:**
- **400 Bad Request:** Invalid patient ID or date format
- **401 Unauthorized:** Invalid or expired token
- **404 Not Found:** Patient not found
- **422 Unprocessable Entity:** Invalid lab_category parameter
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** FHIR service error

**Example:**
```bash
curl -X GET \
  "http://localhost:8000/api/v1/sepsis-alert/patients/e74Q2ey-kqeOCXXuE5Q4nQB/labs?start_date=2024-01-01T00:00:00Z&end_date=2024-01-02T00:00:00Z&lab_category=CBC" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..." \
  -H "Accept: application/fhir+json"
```

**Notes:**
- If no lab_category is specified, all categories are fetched concurrently
- Includes organ dysfunction assessment for each lab category
- Uses FHIR Observation.Search and DiagnosticReport.Search
- Supports both individual lab values and panel results

---

### Get Critical Laboratory Values

**Purpose:** Retrieve critical/abnormal lab values for patient with interpretation flags.

**HTTP Method & URL:** `GET /patients/{patient_id}/labs/critical`

**Path Parameters:**
- `patient_id` (string, required) - FHIR Patient resource ID

**Query Parameters:** None

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Accept: application/fhir+json` (required)

**Request Body:** None

**Response:**
- **Success:** 200 OK
- **Body Schema:** CriticalLabsResponse model
  ```json
  {
    "patient_id": "string",
    "critical_labs": [
      {
        "timestamp": "2024-01-01T12:00:00Z",
        "lab_name": "White Blood Cell Count",
        "loinc_code": "6690-2",
        "value": 15.5,
        "unit": "10^9/L",
        "reference_range": "4.0-11.0",
        "interpretation": "H",
        "interpretation_text": "High",
        "clinical_significance": "Possible infection or inflammation",
        "sepsis_score": 1
      },
      {
        "timestamp": "2024-01-01T12:00:00Z",
        "lab_name": "Lactate",
        "loinc_code": "2019-8",
        "value": 4.2,
        "unit": "mmol/L",
        "reference_range": "0.5-2.2",
        "interpretation": "HH",
        "interpretation_text": "Critical High",
        "clinical_significance": "Hyperlactatemia - possible sepsis",
        "sepsis_score": 2
      }
    ]
  }
  ```

**Error Responses:**
- **400 Bad Request:** Invalid patient ID format
- **401 Unauthorized:** Invalid or expired token
- **404 Not Found:** Patient not found
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** FHIR service error

**Example:**
```bash
curl -X GET \
  "http://localhost:8000/api/v1/sepsis-alert/patients/e74Q2ey-kqeOCXXuE5Q4nQB/labs/critical" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..." \
  -H "Accept: application/fhir+json"
```

**Notes:**
- Returns only abnormal values with interpretation flags: H, HH, L, LL, A, AA
- Includes clinical significance and sepsis scoring
- Optimized for clinical alerts and decision support

---

## Clinical Context Endpoints

### Get Patient Encounter

**Purpose:** Retrieve current patient encounter information including ICU status and length of stay.

**HTTP Method & URL:** `GET /patients/{patient_id}/encounter`

**Path Parameters:**
- `patient_id` (string, required) - FHIR Patient resource ID

**Query Parameters:** None

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Accept: application/fhir+json` (required)

**Request Body:** None

**Response:**
- **Success:** 200 OK
- **Body Schema:** EncounterResponse model
  ```json
  {
    "patient_id": "string",
    "encounter": {
      "encounter_id": "string",
      "status": "in-progress",
      "class": "inpatient",
      "admission_date": "2024-01-01T08:00:00Z",
      "discharge_date": null,
      "length_of_stay_hours": 36,
      "icu_status": true,
      "admission_type": "emergency",
      "location": {
        "name": "ICU - Bed 3",
        "type": "ICU"
      },
      "diagnosis": [
        {
          "code": "A41.9",
          "display": "Sepsis, unspecified",
          "system": "ICD-10-CM"
        }
      ]
    }
  }
  ```

**Error Responses:**
- **400 Bad Request:** Invalid patient ID format
- **401 Unauthorized:** Invalid or expired token
- **404 Not Found:** Patient or encounter not found
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** FHIR service error

**Example:**
```bash
curl -X GET \
  "http://localhost:8000/api/v1/sepsis-alert/patients/e74Q2ey-kqeOCXXuE5Q4nQB/encounter" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..." \
  -H "Accept: application/fhir+json"
```

**Notes:**
- Returns current active encounter only
- ICU status is determined from location information
- Length of stay is calculated from admission date

---

### Get Patient Conditions

**Purpose:** Retrieve patient conditions and diagnoses, particularly infection-related conditions.

**HTTP Method & URL:** `GET /patients/{patient_id}/conditions`

**Path Parameters:**
- `patient_id` (string, required) - FHIR Patient resource ID

**Query Parameters:** None

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Accept: application/fhir+json` (required)

**Request Body:** None

**Response:**
- **Success:** 200 OK
- **Body Schema:** ConditionsResponse model
  ```json
  {
    "patient_id": "string",
    "conditions": [
      {
        "condition_id": "string",
        "code": "A41.9",
        "display": "Sepsis, unspecified",
        "system": "ICD-10-CM",
        "clinical_status": "active",
        "verification_status": "confirmed",
        "onset_date": "2024-01-01",
        "category": "infection",
        "severity": "severe",
        "infection_related": true,
        "sepsis_related": true
      }
    ]
  }
  ```

**Error Responses:**
- **400 Bad Request:** Invalid patient ID format
- **401 Unauthorized:** Invalid or expired token
- **404 Not Found:** Patient not found
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** FHIR service error

**Example:**
```bash
curl -X GET \
  "http://localhost:8000/api/v1/sepsis-alert/patients/e74Q2ey-kqeOCXXuE5Q4nQB/conditions" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..." \
  -H "Accept: application/fhir+json"
```

**Notes:**
- Returns only active conditions
- Flags infection-related and sepsis-related conditions
- Uses FHIR Condition.Search with clinical-status filter

---

### Get Patient Medications

**Purpose:** Retrieve patient medications with optional filtering for antibiotics and vasopressors.

**HTTP Method & URL:** `GET /patients/{patient_id}/medications`

**Path Parameters:**
- `patient_id` (string, required) - FHIR Patient resource ID

**Query Parameters:**
- `medication_type` (string, optional) - Filter medications by type:
  - `ANTIBIOTICS`: Antibiotic medications only
  - `VASOPRESSORS`: Vasopressor medications only
  - `ALL`: All medications (default)

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Accept: application/fhir+json` (required)

**Request Body:** None

**Response:**
- **Success:** 200 OK
- **Body Schema:** MedicationsResponse model
  ```json
  {
    "patient_id": "string",
    "medications": {
      "antibiotics": [
        {
          "medication_id": "string",
          "name": "Vancomycin",
          "generic_name": "vancomycin",
          "dosage": "1000 mg",
          "frequency": "every 12 hours",
          "route": "IV",
          "start_date": "2024-01-01T08:00:00Z",
          "end_date": null,
          "status": "active",
          "indication": "Gram-positive infection",
          "antibiotic_class": "Glycopeptide"
        }
      ],
      "vasopressors": [
        {
          "medication_id": "string",
          "name": "Norepinephrine",
          "generic_name": "norepinephrine",
          "dosage": "0.1 mcg/kg/min",
          "frequency": "continuous",
          "route": "IV",
          "start_date": "2024-01-01T10:00:00Z",
          "end_date": null,
          "status": "active",
          "indication": "Septic shock",
          "vasopressor_type": "Catecholamine"
        }
      ],
      "other_medications": [
        {
          "medication_id": "string",
          "name": "Acetaminophen",
          "generic_name": "acetaminophen",
          "dosage": "650 mg",
          "frequency": "every 6 hours",
          "route": "PO",
          "start_date": "2024-01-01T06:00:00Z",
          "end_date": null,
          "status": "active",
          "indication": "Fever"
        }
      ]
    }
  }
  ```

**Error Responses:**
- **400 Bad Request:** Invalid patient ID format
- **401 Unauthorized:** Invalid or expired token
- **404 Not Found:** Patient not found
- **422 Unprocessable Entity:** Invalid medication_type parameter
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** FHIR service error

**Example:**
```bash
curl -X GET \
  "http://localhost:8000/api/v1/sepsis-alert/patients/e74Q2ey-kqeOCXXuE5Q4nQB/medications?medication_type=ANTIBIOTICS" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..." \
  -H "Accept: application/fhir+json"
```

**Notes:**
- Categorizes medications by clinical relevance to sepsis
- Includes dosage, frequency, and administration details
- Uses FHIR MedicationRequest.Search with status filter

---

### Get Patient Fluid Balance

**Purpose:** Retrieve patient fluid intake and urine output for fluid balance assessment.

**HTTP Method & URL:** `GET /patients/{patient_id}/fluid-balance`

**Path Parameters:**
- `patient_id` (string, required) - FHIR Patient resource ID

**Query Parameters:**
- `start_date` (datetime, optional) - Start date for fluid balance (ISO format: YYYY-MM-DDTHH:MM:SS)
- `end_date` (datetime, optional) - End date for fluid balance (ISO format: YYYY-MM-DDTHH:MM:SS)

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Accept: application/fhir+json` (required)

**Request Body:** None

**Response:**
- **Success:** 200 OK
- **Body Schema:** FluidBalanceResponse model
  ```json
  {
    "patient_id": "string",
    "date_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-02T00:00:00Z"
    },
    "fluid_balance": {
      "total_intake": 2500,
      "total_output": 1800,
      "net_balance": 700,
      "unit": "mL",
      "intake_details": [
        {
          "timestamp": "2024-01-01T08:00:00Z",
          "type": "IV fluid",
          "amount": 1000,
          "unit": "mL",
          "description": "Normal saline"
        },
        {
          "timestamp": "2024-01-01T12:00:00Z",
          "type": "Oral intake",
          "amount": 500,
          "unit": "mL",
          "description": "Water"
        }
      ],
      "output_details": [
        {
          "timestamp": "2024-01-01T08:00:00Z",
          "type": "Urine",
          "amount": 300,
          "unit": "mL",
          "hourly_rate": 37.5,
          "oliguria_detected": false
        },
        {
          "timestamp": "2024-01-01T12:00:00Z",
          "type": "Urine",
          "amount": 200,
          "unit": "mL",
          "hourly_rate": 25.0,
          "oliguria_detected": true
        }
      ]
    }
  }
  ```

**Error Responses:**
- **400 Bad Request:** Invalid patient ID or date format
- **401 Unauthorized:** Invalid or expired token
- **404 Not Found:** Patient not found
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** FHIR service error

**Example:**
```bash
curl -X GET \
  "http://localhost:8000/api/v1/sepsis-alert/patients/e74Q2ey-kqeOCXXuE5Q4nQB/fluid-balance?start_date=2024-01-01T00:00:00Z&end_date=2024-01-02T00:00:00Z" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJRUzI1NiJ9..." \
  -H "Accept: application/fhir+json"
```

**Notes:**
- Calculates net fluid balance automatically
- Detects oliguria (urine output <0.5 mL/kg/hr)
- Uses FHIR Observation.Search for fluid intake/output measurements

---

## Error Handling

All endpoints return standardized error responses:

```json
{
  "error": {
    "code": "FHIR_ERROR",
    "message": "Failed to retrieve patient data",
    "details": "Patient not found in FHIR server",
    "request_id": "uuid-string"
  }
}
```

Common error codes:
- `VALIDATION_ERROR`: Request validation failed
- `AUTHENTICATION_ERROR`: Invalid or expired token
- `FHIR_ERROR`: FHIR server error
- `RATE_LIMIT_ERROR`: Too many requests
- `INTERNAL_ERROR`: Internal server error

## Rate Limiting

- 1000 requests per minute per client
- 429 status code returned when limit exceeded
- Retry-After header indicates when to retry

## Caching

- Patient demographics: 15 minutes
- Vital signs: 5 minutes
- Lab results: 10 minutes
- Clinical data: 5 minutes

## Pagination

FHIR Bundle pagination is handled automatically by the service. Large result sets are automatically paginated using FHIR's `link` elements.