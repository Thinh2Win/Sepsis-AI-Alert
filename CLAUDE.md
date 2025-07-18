# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Sepsis AI EHR Alert System - an AI-powered Clinical Decision Support (CDS) tool that integrates with Electronic Health Records (EHRs) using FHIR interoperability standards to proactively detect sepsis in hospitalized patients.

## Claude Rules
1. First think through the problem, read the codebase for relevant files, and formulate a plan.
2. The plan should have a list of todo items that you can check off as you complete them
3. Before you begin working, check in with me and I will verify the plan.
4. Then, begin working on the todo items, marking them as complete as you go.
5. For every step along the way give me a high level explanation of what changes you made
6. Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
7. Finally, add a review section to the docs directory with a summary of the changes you made and any other relevant information.

### Python Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Recommended: Automated server startup (handles venv activation and directory navigation)
python start_server.py

# Alternative: Manual server startup
# First activate virtual environment:
# Windows: venv\Scripts\activate
# Unix/macOS: source venv/bin/activate
# Then run the FastAPI development server (new modular structure)
cd backend/src
python main.py
# or
uvicorn main:app --reload

# Run individual scripts for testing (legacy)
python backend/src/fetch_patient.py
```

### Virtual Environment

The project uses a Python virtual environment located in the `venv/` directory. The `start_server.py` script automatically handles virtual environment activation when starting the server.

For manual activation (if needed):
- Windows: `venv\Scripts\activate`
- Unix/macOS: `source venv/bin/activate`

## Architecture

### Current Backend Structure (`backend/src/`)

#### Application Entry Point
- **main.py**: Application entry point that imports from new modular structure

#### New Modular Structure (`backend/src/app/`)

##### Core (`app/core/`)
- **main.py**: FastAPI application with middleware, exception handlers, and router registration
- **config.py**: Pydantic-based settings management with environment validation
- **dependencies.py**: Dependency injection for shared services
- **exceptions.py**: Custom exception classes (FHIRException, AuthenticationException)
- **middleware.py**: Request logging middleware with unique request IDs
- **loinc_codes.py**: Comprehensive LOINC code mappings organized by clinical category

##### Models (`app/models/`)
- **patient.py**: Patient demographics with computed fields (age, BMI, primary contacts)
- **vitals.py**: Vital signs with clinical interpretation and sepsis scoring
- **labs.py**: Laboratory results organized by category with organ dysfunction assessment
- **clinical.py**: Clinical context (encounters, conditions, medications, fluid balance)

##### Routers (`app/routers/`)
- **patients.py**: Patient demographics and matching endpoints
- **vitals.py**: Vital signs endpoints with time-series and latest data
- **labs.py**: Laboratory results endpoints with critical value filtering
- **clinical.py**: Clinical context endpoints (encounters, conditions, medications, fluid balance)

##### Services (`app/services/`)
- **auth_client.py**: Enhanced OAuth2 JWT authentication with proper error handling
- **fhir_client.py**: Comprehensive FHIR R4 client with retry logic, pagination, and data processing

##### Utils (`app/utils/`)
- **calculations.py**: Clinical calculation utilities (age, BMI, blood pressure, fever detection)
- **date_utils.py**: FHIR datetime parsing, validation, and time-based calculations
- **fhir_utils.py**: FHIR bundle processing, observation extraction, and data transformation

### Key Dependencies

- **FastAPI**: Web framework for the REST API
- **pydantic**: Data validation and settings management with computed fields
- **pydantic-settings**: Environment-based configuration management
- **python-jose**: JWT token handling for Epic authentication
- **uvicorn**: ASGI server for FastAPI
- **tenacity**: Retry logic for API calls with exponential backoff
- **requests**: HTTP client for FHIR API calls
- **python-dotenv**: Environment variable management

### Enhanced FHIR Integration

The system integrates with Epic FHIR R4 APIs to retrieve comprehensive clinical data:

#### Patient Demographics
- Age calculation from birth date
- BMI calculation from height/weight observations
- Primary contact information extraction

#### Vital Signs (Time-Series)
- Heart rate with tachycardia/bradycardia detection
- Blood pressure with MAP and pulse pressure calculations
- Temperature with fever detection
- Respiratory rate with tachypnea assessment
- Oxygen saturation with hypoxia detection
- Glasgow Coma Score with severity interpretation

#### Laboratory Results (Organized by Category)
- **CBC**: WBC count, platelet count, hemoglobin with infection indicators
- **Metabolic Panel**: Glucose, creatinine, electrolytes with kidney function assessment
- **Liver Function**: Bilirubin, albumin, liver enzymes with dysfunction detection
- **Inflammatory Markers**: CRP, procalcitonin with sepsis likelihood assessment
- **Blood Gas**: pH, lactate, PaO2/FiO2 with acidosis and hyperlactatemia detection
- **Coagulation**: PT/INR, PTT with coagulopathy assessment

#### Clinical Context
- **Encounters**: ICU status, length of stay, admission type
- **Conditions**: Active infections, sepsis-related diagnoses
- **Medications**: Antibiotic and vasopressor identification
- **Fluid Balance**: Intake/output calculations, oliguria detection

### Authentication & Security

- **OAuth2 JWT**: Enhanced Epic FHIR authentication with automatic token refresh
- **Error Handling**: Comprehensive exception handling with secure error responses
- **Request Validation**: Pydantic model validation for all inputs
- **Environment Security**: Sensitive data managed via environment variables
- **Request Logging**: Detailed request tracking with unique IDs

### Configuration

Environment variables are stored in `backend/src/.env` and include:
- **CLIENT_ID**: Epic app client identifier
- **TOKEN_URL**: OAuth2 token endpoint
- **PRIVATE_KEY_PATH**: Path to RSA private key for JWT signing
- **FHIR_API_BASE**: Base URL for FHIR API endpoints

### Production Features

- **Retry Logic**: Exponential backoff for failed requests with tenacity
- **Pagination**: Automatic FHIR Bundle pagination handling
- **Error Handling**: Custom exceptions with proper HTTP status codes
- **Request Middleware**: Comprehensive request logging and tracking
- **Health Checks**: Application health monitoring endpoints
- **API Documentation**: Automatic OpenAPI/Swagger documentation

### Data Requirements for Sepsis Prediction Models
Based on the research, sepsis prediction models typically require the following key data elements:
1. Vital Signs (Time-Series Data)

Heart Rate (HR) - including heart rate variability and entropy measures
Blood Pressure - both systolic and diastolic, including variability metrics
Temperature/Body Temperature
Respiratory Rate
Oxygen Saturation (SpO2)
Mental Status/Glasgow Coma Score

2. Laboratory Results
Complete Blood Count (CBC):
White Blood Cell count (WBC)
Platelet count

Metabolic Panel:
Creatinine
Blood Urea Nitrogen (BUN)
Glucose levels

Liver Function Tests:
Bilirubin (total)
Albumin
Lactate Dehydrogenase (LDH)

Inflammatory Markers:
C-reactive protein (CRP)
Procalcitonin (if available)

Blood Gas Analysis:
Lactate levels
pH
PaO2/FiO2 ratio

Coagulation Studies:
INR/PT
PTT

3. Patient Demographics

Age
Sex/Gender
Weight
Height/BMI

4. Clinical Context

Admission source (ICU, Emergency Department, etc.)
Time since admission
Presence of infection indicators
Medical history
Current medications (especially antibiotics, vasopressors)
Fluid balance
Urine output

## Current Implementation Status

### ✅ Completed Components

#### Core Infrastructure
- [x] **FastAPI Application Structure**: Modular design with routers, services, and models
- [x] **Authentication Service**: OAuth2 JWT authentication with Epic FHIR
- [x] **FHIR Client**: Comprehensive client with retry logic and pagination
- [x] **Error Handling**: Custom exceptions and middleware
- [x] **Configuration Management**: Environment-based settings with validation

#### Data Models & Validation
- [x] **Patient Models**: Demographics with computed fields (age, BMI, contacts)
- [x] **Vital Signs Models**: Time-series data with clinical interpretation and sepsis scoring
- [x] **Laboratory Models**: Organized by category with organ dysfunction assessment
- [x] **Clinical Models**: Encounters, conditions, medications, fluid balance

#### Utility Functions
- [x] **Clinical Calculations**: Age, BMI, blood pressure, fever detection
- [x] **Date Utilities**: FHIR datetime parsing, validation, time calculations
- [x] **FHIR Utilities**: Bundle processing, observation extraction, data transformation
- [x] **LOINC Code Mappings**: Comprehensive mapping for all clinical categories

#### API Endpoints (Structure Ready)
- [x] **Patient Demographics**: `/api/v1/sepsis-alert/patients/{patient_id}`
- [x] **Patient Matching**: `/api/v1/sepsis-alert/patients/match`
- [x] **Vital Signs**: `/api/v1/sepsis-alert/patients/{patient_id}/vitals`
- [x] **Laboratory Results**: `/api/v1/sepsis-alert/patients/{patient_id}/labs`
- [x] **Clinical Context**: `/api/v1/sepsis-alert/patients/{patient_id}/encounter`

### 🔄 In Progress

#### FHIR Client Implementation
- [ ] **Data Processing Methods**: Complete implementation of FHIR bundle processing
- [ ] **Observation Extraction**: Implement LOINC-based observation extraction
- [ ] **Clinical Scoring**: Implement sepsis scoring algorithms

### 📋 Next Steps

1. **Complete FHIR Client Data Processing**
   - Implement `_process_vitals()` method
   - Implement `_process_labs()` method
   - Implement `_process_clinical()` methods

2. **Testing & Validation**
   - Test with Epic FHIR R4 sandbox
   - Validate data processing accuracy
   - Test authentication and retry logic

3. **Clinical Scoring Implementation**
   - Implement SIRS, qSOFA, SOFA scoring
   - Add alerting logic
   - Create clinical summary endpoints

### Epic FHIR Endpoints/FastAPI to EPIC FHIR R4 Endpoint Mapping (Reference)
1. Patient Demographics Endpoints
FastAPI: GET /api/v1/sepsis-alert/patients/{patient_id}
FHIR Operations:

Patient.Read (R4)

Endpoint: GET [base]/Patient/{id}
Input: id = Patient FHIR ID (not MRN)
Returns: Single Patient resource


Observation.Search (R4) - For Height/Weight/BMI

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=8302-2,29463-7,39156-5 (height, weight, BMI)
_sort=-date
_count=1 (most recent only)


Returns: Bundle of Observation resources




1.1. Patient Matching Endpoints
FastAPI: POST /api/v1/sepsis-alert/patients/match

Request Body (PatientMatchRequest):
```json
{
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
}
```

FHIR Operations:

Patient.$match (R4)

Endpoint: POST [base]/Patient/$match
Internal Parameters Structure (sent by FastAPI):
```json
{
  "resourceType": "Parameters",
  "parameter": [
    {
      "name": "resource",
      "resource": {
        "resourceType": "Patient",
        "name": [{"family": "Mychart", "given": ["Theodore"]}],
        "birthDate": "1948-07-07",
        "telecom": [{"system": "phone", "value": "+1 608-213-5806", "use": "home"}],
        "address": [{"line": ["134 Elmstreet"], "city": "Madison", "state": "WI", "postalCode": null, "country": "US", "use": "home"}]
      }
    },
    {
      "name": "onlyCertainMatches",
      "valueBoolean": true
    }
  ]
}
```

Returns: Bundle with matched Patient resources and match scores

Response (PatientMatchResponse):
```json
{
  "resourceType": "Bundle",
  "total": 1,
  "entry": [
    {
      "resource": {
        "id": "e63wRTbPfr1p8UW81d8Seiw3",
        "name": [{"family": "Mychart", "given": ["Theodore"]}],
        "birthDate": "1948-07-07",
        "gender": "male",
        "age": 77,
        "primary_name": "Theodore Mychart",
        "primary_phone": "+1 608-213-5806"
      },
      "search": {
        "mode": "match",
        "score": 1,
        "extension": [{"valueCode": "certain", "url": "http://hl7.org/fhir/StructureDefinition/match-grade"}]
      }
    }
  ]
}
```

2. Vital Signs Endpoints
FastAPI: GET /api/v1/sepsis-alert/patients/{patient_id}/vitals
FHIR Operations - All use Observation.Search (R4):

Heart Rate

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=8867-4
date=ge{start_date}
date=le{end_date}
_sort=-date




Blood Pressure

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=85354-9,8480-6,8462-4
date=ge{start_date}
date=le{end_date}
_sort=-date




Temperature

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=8310-5
date=ge{start_date}
date=le{end_date}
_sort=-date




Respiratory Rate

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=9279-1
date=ge{start_date}
date=le{end_date}
_sort=-date




Oxygen Saturation

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=2708-6,59408-5
date=ge{start_date}
date=le{end_date}
_sort=-date




Glasgow Coma Score

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=9269-2
date=ge{start_date}
date=le{end_date}
_sort=-date





FastAPI: GET /api/v1/sepsis-alert/patients/{patient_id}/vitals/latest

Same FHIR operations as above but with _count=1 parameter


3. Laboratory Results Endpoints
FastAPI: GET /api/v1/sepsis-alert/patients/{patient_id}/labs
FHIR Operations - Using Observation.Search (R4) and DiagnosticReport.Search (R4):

CBC Panel - DiagnosticReport.Search (R4)

Endpoint: GET [base]/DiagnosticReport
Parameters:

patient={patient_id}
code=58410-2 (CBC panel)
date=ge{start_date}
date=le{end_date}
_include=DiagnosticReport:result


Note: This returns the report with included Observation resources


Individual CBC Components - Observation.Search (R4)

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=6690-2,777-3 (WBC, Platelets)
date=ge{start_date}
date=le{end_date}
_sort=-date




Metabolic Panel - DiagnosticReport.Search (R4)

Endpoint: GET [base]/DiagnosticReport
Parameters:

patient={patient_id}
code=24323-8 (Comprehensive metabolic panel)
date=ge{start_date}
date=le{end_date}
_include=DiagnosticReport:result




Individual Metabolic Components - Observation.Search (R4)

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=2160-0,3094-0,2345-7 (Creatinine, BUN, Glucose)
date=ge{start_date}
date=le{end_date}
_sort=-date




Liver Function - Observation.Search (R4)

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=1975-2,1742-6,14804-9 (Bilirubin, Albumin, LDH)
date=ge{start_date}
date=le{end_date}
_sort=-date




Inflammatory Markers - Observation.Search (R4)

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=1988-5,75241-0 (CRP, Procalcitonin)
date=ge{start_date}
date=le{end_date}
_sort=-date




Blood Gas - Observation.Search (R4)

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=2019-8,2744-1,50984-4 (Lactate, pH, PaO2/FiO2)
date=ge{start_date}
date=le{end_date}
_sort=-date




Coagulation - Observation.Search (R4)

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=5902-2,3173-2 (PT/INR, PTT)
date=ge{start_date}
date=le{end_date}
_sort=-date





FastAPI: GET /api/v1/sepsis-alert/patients/{patient_id}/labs/critical

Same operations but add parameter: interpretation=H,HH,L,LL,A,AA (High, Very High, Low, Very Low, Abnormal, Critical)


4. Clinical Context Endpoints
FastAPI: GET /api/v1/sepsis-alert/patients/{patient_id}/encounter
FHIR Operations:

Encounter.Search (R4)

Endpoint: GET [base]/Encounter
Parameters:

patient={patient_id}
status=in-progress,arrived
_sort=-date
_count=1


Returns: Bundle with current encounter


Encounter.Read (R4)

Endpoint: GET [base]/Encounter/{encounter_id}
Input: encounter_id obtained from search above
Returns: Single Encounter resource with full details



FastAPI: GET /api/v1/sepsis-alert/patients/{patient_id}/conditions
FHIR Operations:

Condition.Search (R4)

Endpoint: GET [base]/Condition
Parameters:

patient={patient_id}
clinical-status=active,recurrence,relapse


Returns: Bundle of Condition resources


Condition.Read (R4) (if specific condition details needed)

Endpoint: GET [base]/Condition/{condition_id}
Input: condition_id from search results
Returns: Single Condition resource



FastAPI: GET /api/v1/sepsis-alert/patients/{patient_id}/medications
FHIR Operations:

MedicationRequest.Search (R4)

Endpoint: GET [base]/MedicationRequest
Parameters:

patient={patient_id}
status=active
_include=MedicationRequest:medication


For antibiotics add: medication.code:text=antibiotic,antimicrobial
For vasopressors add: medication.code:text=norepinephrine,epinephrine,vasopressin,dopamine


MedicationAdministration.Search (R4) (for actual administration times)

Endpoint: GET [base]/MedicationAdministration
Parameters:

patient={patient_id}
status=in-progress,completed
effective-time=ge{start_date}
effective-time=le{end_date}

5. Fluid Balance & Urine Output Endpoints
FastAPI: GET /api/v1/sepsis-alert/patients/{patient_id}/fluid-balance
FHIR Operations - Observation.Search (R4):

Fluid Intake

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=9192-6
date=ge{start_date}
date=le{end_date}
_sort=-date

Urine Output

Endpoint: GET [base]/Observation
Parameters:

patient={patient_id}
code=9187-6,9188-4
date=ge{start_date}
date=le{end_date}
_sort=-date

6. Important Notes on FHIR R4 Operations
Search Operations Return Bundles:
json{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 10,
  "entry": [
    {
      "fullUrl": "https://epic-sandbox/api/FHIR/R4/Observation/12345",
      "resource": {
        "resourceType": "Observation",
        "id": "12345",
        // ... observation data
      }
    }
  ]
}
Read Operations Return Single Resources:
json{
  "resourceType": "Observation",
  "id": "12345",
  // ... resource data
}
Key Input Considerations:

Patient ID: Always use FHIR resource ID, not MRN
Date formats: ISO 8601 (YYYY-MM-DD or YYYY-MM-DDThh:mm:ss)
Multiple codes: Comma-separated without spaces
Status values: Must match FHIR ValueSet definitions
_include parameters: Follow reference paths exactly