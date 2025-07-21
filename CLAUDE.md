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
- **sofa.py**: SOFA scoring models with comprehensive organ dysfunction assessment
- **qsofa.py**: qSOFA scoring models with rapid bedside sepsis screening

##### Routers (`app/routers/`)
- **patients.py**: Patient demographics and matching endpoints
- **vitals.py**: Vital signs endpoints with time-series and latest data
- **labs.py**: Laboratory results endpoints with critical value filtering
- **clinical.py**: Clinical context endpoints (encounters, conditions, medications, fluid balance)
- **sepsis_scoring.py**: SOFA and qSOFA sepsis scoring endpoints with risk assessment and batch processing

##### Services (`app/services/`)
- **auth_client.py**: Enhanced OAuth2 JWT authentication with proper error handling
- **fhir_client.py**: Comprehensive FHIR R4 client with retry logic, pagination, and data processing
- **sepsis_scoring_service.py**: Business logic for SOFA and qSOFA scoring calculations and risk assessment
- **sepsis_response_builder.py**: Centralized response building for sepsis assessments

##### Utils (`app/utils/`)
- **calculations.py**: Clinical calculation utilities (age, BMI, blood pressure, fever detection)
- **date_utils.py**: FHIR datetime parsing, validation, and time-based calculations
- **fhir_utils.py**: FHIR bundle processing, observation extraction, and data transformation
- **sofa_scoring.py**: SOFA score calculation algorithms and clinical assessment logic
- **qsofa_scoring.py**: qSOFA score calculation algorithms for rapid sepsis screening
- **scoring_utils.py**: Shared scoring utilities implementing DRY/KISS principles
- **error_handling.py**: Standardized error handling decorators and validation utilities

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
- [x] **Patient Models**: Simplified demographics with flattened address and demographic fields
- [x] **Vital Signs Models**: Time-series data with clinical interpretation and sepsis scoring
- [x] **Laboratory Models**: Organized by category with organ dysfunction assessment
- [x] **Clinical Models**: Encounters, conditions, medications, fluid balance
- [x] **SOFA Models**: Comprehensive organ dysfunction assessment with 6-system scoring
- [x] **qSOFA Models**: Rapid bedside sepsis screening with 3-parameter assessment
- [x] **NEWS2 Models**: National Early Warning Score with 7-parameter clinical deterioration assessment

#### Utility Functions
- [x] **Clinical Calculations**: Age, BMI, blood pressure, fever detection
- [x] **Date Utilities**: FHIR datetime parsing, validation, time calculations
- [x] **FHIR Utilities**: Bundle processing, observation extraction, data transformation
- [x] **LOINC Code Mappings**: Comprehensive mapping for all clinical categories
- [x] **SOFA Scoring**: Complete 6-organ system assessment algorithms
- [x] **qSOFA Scoring**: Rapid 3-parameter sepsis screening algorithms
- [x] **NEWS2 Scoring**: 7-parameter clinical deterioration assessment with data reuse optimization
- [x] **Shared Scoring Utilities**: DRY/KISS compliant common functions for all scoring systems

#### API Endpoints (Structure Ready)
- [x] **Patient Demographics**: `/api/v1/sepsis-alert/patients/{patient_id}`
- [x] **Patient Matching**: `/api/v1/sepsis-alert/patients/match`
- [x] **Vital Signs**: `/api/v1/sepsis-alert/patients/{patient_id}/vitals`
- [x] **Laboratory Results**: `/api/v1/sepsis-alert/patients/{patient_id}/labs`
- [x] **Clinical Context**: `/api/v1/sepsis-alert/patients/{patient_id}/encounter`
- [x] **SOFA, qSOFA & NEWS2 Sepsis Scoring**: `/api/v1/sepsis-alert/patients/{patient_id}/sepsis-score`
- [x] **Batch Sepsis Scoring**: `/api/v1/sepsis-alert/patients/batch-sepsis-scores`

#### Sepsis Scoring Implementation
- [x] **SOFA Score Calculation**: Complete 6-organ system assessment (respiratory, coagulation, liver, cardiovascular, CNS, renal)
- [x] **qSOFA Score Calculation**: Rapid 3-parameter assessment (respiratory rate, systolic BP, GCS)
- [x] **NEWS2 Score Calculation**: 7-parameter clinical deterioration assessment (respiratory rate, SpO2, supplemental O2, temperature, systolic BP, heart rate, consciousness)
- [x] **Combined Risk Stratification**: Triple scoring system with mortality risk assessment and clinical recommendations
- [x] **Data Quality Tracking**: Missing parameter detection and reliability scoring for all systems
- [x] **Clinical Alerts**: Severity-based alerting with organ dysfunction and deterioration detection
- [x] **Batch Processing**: Multi-patient scoring with error handling for SOFA, qSOFA, and NEWS2
- [x] **Configuration Management**: Centralized constants and thresholds for all scoring systems
- [x] **DRY/KISS Refactoring**: Shared utilities to eliminate code duplication between scoring systems
- [x] **Data Reuse Optimization**: NEWS2 reuses SOFA/qSOFA parameters to minimize FHIR API calls (~85% reduction)

### 🔄 In Progress

#### Enhanced Features
- [ ] **Trend Analysis**: Historical SOFA, qSOFA, and NEWS2 score tracking and deterioration detection
- [x] **qSOFA Integration**: Quick SOFA implementation for non-ICU screening
- [x] **NEWS2 Integration**: National Early Warning Score implementation with data reuse optimization

### 📋 Next Steps

1. **Complete FHIR Client Data Processing**
   - [x] Implement `_process_vitals()` method
   - [x] Implement `_process_labs()` method
   - [x] Implement `_process_clinical()` methods

2. **Testing & Validation**
   - [ ] Test with Epic FHIR R4 sandbox
   - [ ] Validate data processing accuracy
   - [ ] Test authentication and retry logic

3. **Clinical Scoring Implementation**
   - [x] Implement qSOFA and SOFA scoring
   - [x] Add alerting logic
   - [x] Create clinical summary endpoints

4. **Enhanced Scoring Features**
   - [x] Implement NEWS2 scoring system
   - [ ] Add trend analysis for historical scoring
   - [ ] Create real-time alerting dashboard

## qSOFA Implementation Details

### qSOFA Scoring System Overview
The qSOFA (Quick SOFA) scoring system has been implemented as a complementary rapid sepsis screening tool alongside the comprehensive SOFA scoring system.

#### Clinical Purpose
- **Primary Use**: Rapid bedside sepsis screening for non-ICU settings
- **Target Population**: Patients outside of ICU who may be at risk for sepsis
- **Speed**: 4-hour data window for rapid assessment vs 24-hour for SOFA
- **Simplicity**: Only 3 parameters vs 24 parameters for SOFA

#### Scoring Parameters
1. **Respiratory Rate** ≥22 breaths/min (1 point)
2. **Systolic Blood Pressure** ≤100 mmHg (1 point)  
3. **Glasgow Coma Scale** <15 (altered mental status) (1 point)

#### Risk Interpretation
- **Score 0-1**: Low risk for poor outcomes
- **Score ≥2**: High risk - 10-fold increased risk of in-hospital mortality
- **Clinical Action**: Score ≥2 triggers sepsis evaluation recommendations

#### Implementation Architecture
- **Models**: `app/models/qsofa.py` - Complete qSOFA data models
- **Scoring Logic**: `app/utils/qsofa_scoring.py` - Calculation algorithms
- **Constants**: `app/core/qsofa_constants.py` - Configuration and thresholds
- **Shared Utilities**: `app/utils/scoring_utils.py` - DRY/KISS compliant common functions
- **Service Integration**: Both SOFA and qSOFA calculated by default

#### Key Features
- **Rapid Assessment**: 4-hour lookback window for quick clinical decisions
- **Fallback Handling**: Robust error handling with default values (RR: 16, SBP: 120, GCS: 15)
- **Data Quality**: Reliability scoring and missing parameter tracking
- **Clinical Alerts**: Automated high-risk identification for scores ≥2
- **Batch Processing**: Multi-patient scoring for population monitoring
- **DRY/KISS Compliance**: Shared utilities eliminate code duplication with SOFA

## NEWS2 Implementation Details

### NEWS2 Scoring System Overview
The NEWS2 (National Early Warning Score 2) scoring system has been implemented as a comprehensive clinical deterioration detection tool that complements the existing sepsis-specific scores (SOFA/qSOFA).

#### Clinical Purpose
- **Primary Use**: Early detection of clinical deterioration for all adult patients (16+ years)
- **Target Population**: Any hospitalized patient at risk of clinical deterioration
- **Speed**: 4-hour data window for rapid assessment
- **Universality**: Works for ANY acute illness (not disease-specific like SOFA)

#### Scoring Parameters (7 total)
1. **Respiratory Rate** (breaths/min) - Often first sign of deterioration
2. **Oxygen Saturation** (%) - Includes Scale 2 for COPD patients (88-92% target)
3. **Supplemental Oxygen** (Yes/No) - Indicates respiratory compromise
4. **Temperature** (°C) - Detects infection, fever, or hypothermia
5. **Systolic Blood Pressure** (mmHg) - Cardiovascular status indicator
6. **Heart Rate** (bpm) - Cardiovascular response assessment
7. **Level of Consciousness** (AVPU/GCS) - Neurological function

#### Risk Interpretation & Clinical Response
- **Score 0-4 (LOW)**: Routine monitoring (4-12 hourly)
- **Score 5-6 (MEDIUM)** OR any single parameter = 3: Urgent review within 1 hour
- **Score ≥7 (HIGH)**: Emergency assessment and continuous monitoring

#### Implementation Architecture
- **Models**: `app/models/news2.py` - Complete NEWS2 data models with computed fields
- **Scoring Logic**: `app/utils/news2_scoring.py` - Calculation algorithms with data reuse optimization
- **Constants**: `app/core/news2_constants.py` - Configuration, thresholds, and LOINC mappings
- **Shared Utilities**: `app/utils/scoring_utils.py` - DRY/KISS compliant common functions
- **Service Integration**: Integrated with SOFA and qSOFA in unified endpoint

#### Key Features & Optimizations
- **Data Reuse Optimization**: Reuses 6 of 7 parameters from existing SOFA/qSOFA data (~85% API call reduction)
- **Rapid Assessment**: 4-hour lookback window for quick clinical decisions
- **Robust Error Handling**: Graceful degradation with default values and reliability scoring
- **Clinical Decision Support**: Automated risk stratification with specific monitoring recommendations
- **COPD Support**: Specialized Scale 2 for hypercapnic respiratory failure patients
- **Combined Risk Assessment**: Intelligent combination with SOFA/qSOFA for comprehensive evaluation
- **DRY/KISS Compliance**: Shared utilities eliminate code duplication across scoring systems

#### Performance Benefits
- **Reduced FHIR Calls**: Only fetches supplemental oxygen data (new parameter not in SOFA/qSOFA)
- **Faster Response Times**: Parameter reuse eliminates redundant API calls
- **Consistent Timestamps**: All parameters use aligned time windows
- **Reliable Scoring**: Fallback mechanisms ensure scoring always possible

### Epic FHIR Endpoints/FastAPI to EPIC FHIR R4 Endpoint Mapping (Reference)
1. Patient Demographics Endpoints
FastAPI: GET /api/v1/sepsis-alert/patients/{patient_id}
FHIR Operations:

Patient.Read (R4)

Endpoint: GET [base]/Patient/{id}
Input: id = Patient FHIR ID (not MRN)
Returns: Simplified Patient resource with flattened fields


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
        "gender": "male",
        "birth_date": "1948-07-07",
        "age": 77,
        "primary_address": "134 Elmstreet",
        "city": "Madison",
        "state": "WI",
        "postal_code": "53706",
        "height_cm": 175.0,
        "weight_kg": 70.0,
        "bmi": 22.9,
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