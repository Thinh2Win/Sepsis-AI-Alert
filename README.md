# 🩺 Sepsis AI EHR Alert System

An AI-powered Clinical Decision Support (CDS) tool integrated with Electronic Health Records (EHRs) leveraging FHIR R4 interoperability standards to proactively detect sepsis in hospitalized patients.

---

## 📖 Project Overview

**Sepsis** is a life-threatening medical condition triggered by the body's extreme response to an infection. Each hour that treatment is delayed increases mortality by approximately **8%**. Timely identification and intervention are critical to patient survival and outcome improvement.

This project showcases a practical application of Artificial Intelligence (AI) and interoperability in healthcare. Using Fast Healthcare Interoperability Resources (FHIR R4), this clinical decision support system:

* Ingests real-time patient data from Epic FHIR R4 sandbox
* Analyzes comprehensive clinical data including vital signs, laboratory results, and clinical context
* Provides automated sepsis risk assessment with intelligent scoring algorithms
* Delivers actionable insights to clinicians through a modern REST API

---

## 🎯 Objectives

* **Clinical Objective:**
  * Rapidly detect and predict sepsis using clinically validated scoring systems (SOFA, qSOFA scores)
  * Early detection of clinical deterioration using NEWS2 (National Early Warning Score 2) with data reuse optimization
  * Alert clinicians proactively with severity indicators and recommended interventions
  * Provide comprehensive triple scoring system (SOFA + qSOFA + NEWS2) for complete clinical assessment
  * Deliver 85% reduction in FHIR API calls through intelligent parameter reuse

* **Technical Objective:**
  * Leverage FHIR R4 resources to ingest, normalize, and extract features from clinical data
  * Implement robust OAuth2 JWT authentication with Epic FHIR sandbox
  * Provide production-ready FastAPI application with proper error handling and retry logic
  * Demonstrate secure, HIPAA-compliant architecture principles

---

## 📊 Clinical Indicators & Comprehensive Data Analysis

The system analyzes comprehensive clinical indicators from standardized FHIR R4 resources:

### Patient Demographics & Vital Signs
| FHIR Resource | Clinical Indicators | LOINC Codes |
|---------------|-------------------|-------------|
| **Patient** | Age, Gender, Height, Weight, BMI | 8302-2, 29463-7, 39156-5 |
| **Observation (Vital Signs)** | Heart Rate, Blood Pressure, Temperature, Respiratory Rate, Oxygen Saturation, Glasgow Coma Score | 8867-4, 8480-6, 8462-4, 8310-5, 9279-1, 2708-6, 9269-2 |

### Laboratory Results (Organized by Category)
| Category | Parameters | LOINC Codes |
|----------|------------|-------------|
| **CBC** | WBC Count, Platelet Count, Hemoglobin, Hematocrit | 6690-2, 777-3, 718-7, 4544-3 |
| **Metabolic Panel** | Glucose, Creatinine, BUN, Electrolytes | 2345-7, 2160-0, 3094-0, 2951-2 |
| **Liver Function** | Total Bilirubin, Albumin, ALT, AST, LDH | 1975-2, 1751-7, 1742-6, 1920-8, 14804-9 |
| **Inflammatory Markers** | CRP, Procalcitonin, ESR | 1988-5, 75241-0, 30341-2 |
| **Blood Gas** | pH, Lactate, PaO2/FiO2 Ratio | 2744-1, 2524-7, 50984-4 |
| **Coagulation** | PT/INR, PTT, Fibrinogen | 5902-2, 6301-6, 14979-9 |

### Clinical Context
| Resource | Information | Purpose |
|----------|-------------|---------|
| **Encounter** | Admission Type, ICU Status, Length of Stay | Risk stratification |
| **Condition** | Active Infections, Sepsis Diagnoses | Clinical context |
| **Medication** | Antibiotics, Vasopressors | Treatment assessment |
| **Fluid Balance** | Intake/Output, Oliguria Detection | Organ dysfunction |

### Sepsis Scoring Systems

#### SOFA (Sequential Organ Failure Assessment)
* **Purpose:** Comprehensive organ dysfunction assessment for ICU patients
* **Score Range:** 0-24 points across 6 organ systems
* **Organ Systems:** Respiratory, Coagulation, Liver, Cardiovascular, CNS, Renal
* **Data Window:** 24-hour lookback for comprehensive assessment
* **Mortality Risk:** 0-6 points (<10%), 13-14 points (>50%), >15 points (>80%)

#### qSOFA (Quick SOFA)
* **Purpose:** Rapid bedside sepsis screening for non-ICU settings
* **Score Range:** 0-3 points based on 3 simple criteria
* **Parameters:** 
  - Respiratory rate ≥22 breaths/min (1 point)
  - Systolic blood pressure ≤100 mmHg (1 point)
  - Glasgow Coma Scale <15 (altered mental status) (1 point)
* **Data Window:** 4-hour lookback for rapid assessment
* **High Risk Threshold:** ≥2 points indicates 10-fold increased risk of in-hospital mortality

#### NEWS2 (National Early Warning Score 2)
* **Purpose:** Early detection of clinical deterioration for all adult patients
* **Score Range:** 0-20 points across 7 vital sign parameters
* **Parameters:**
  - Respiratory rate (0-3 points)
  - Oxygen saturation with Scale 2 for COPD (0-3 points)
  - Supplemental oxygen therapy (0 or 2 points)
  - Temperature (0-3 points)
  - Systolic blood pressure (0-3 points)
  - Heart rate (0-3 points)
  - Level of consciousness/AVPU (0 or 3 points)
* **Data Window:** 4-hour lookback for rapid assessment
* **Risk Levels:** 0-4 (LOW/routine monitoring), 5-6 (MEDIUM/urgent review), ≥7 (HIGH/emergency assessment)
* **Data Reuse Optimization:** Reuses 6/7 parameters from SOFA/qSOFA (~85% API call reduction)

### Combined Risk Assessment Levels
The system intelligently combines SOFA, qSOFA, and NEWS2 scores to provide comprehensive risk assessment:
* 🟢 **MINIMAL** - All scores low risk (qSOFA 0, SOFA 0-6, NEWS2 0-4)
* 🟡 **LOW** - Mild elevation in any system (qSOFA 1, SOFA 7-9, NEWS2 0-4)
* 🟠 **MODERATE** - Moderate concern (qSOFA 1-2, SOFA 10-12, NEWS2 5-6)
* 🔴 **HIGH** - High risk in any system (qSOFA ≥2, SOFA 13-14, NEWS2 ≥7)
* 🚨 **CRITICAL** - Critical deterioration (qSOFA 3, SOFA ≥15, NEWS2 ≥7 with multiple parameters = 3)

**Risk Prioritization Logic:** The system takes the highest risk level among all calculated scores, with special priority given to:
- qSOFA ≥2 (sepsis concern)
- NEWS2 ≥7 (clinical deterioration)
- SOFA ≥10 (organ dysfunction)

---

## 🖥️ Architecture Overview

```
                    ┌─────────────────────────────┐
                    │     Epic FHIR R4 Sandbox    │
                    │   (OAuth2 JWT Authentication)│
                    └─────────────┬───────────────┘
                                  │ FHIR R4 Resources
                                  ▼
                 ┌─────────────────────────────────────┐
                 │        FastAPI Application          │
                 │ ┌─────────────────────────────────┐ │
                 │ │     Authentication Service      │ │
                 │ │   (OAuth2 JWT with Retry)       │ │
                 │ └─────────────┬───────────────────┘ │
                 │               │                     │
                 │ ┌─────────────▼───────────────────┐ │
                 │ │       FHIR Client Service       │ │
                 │ │  (Pagination, Error Handling)   │ │
                 │ └─────────────┬───────────────────┘ │
                 │               │                     │
                 │ ┌─────────────▼───────────────────┐ │
                 │ │   Data Processing & Validation  │ │
                 │ │    (Pydantic Models & Utils)    │ │
                 │ └─────────────┬───────────────────┘ │
                 │               │                     │
                 │ ┌─────────────▼───────────────────┐ │
                 │ │     Sepsis Risk Assessment      │ │
                 │ │ (Scoring Algorithms & Alerts)   │ │
                 │ └─────────────┬───────────────────┘ │
                 └───────────────┼───────────────────────┘
                                 │ REST API Endpoints
                                 ▼
                  ┌─────────────────────────────────────┐
                  │   Clinical Dashboard (Future)       │
                  │     React + SMART on FHIR          │
                  └─────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Backend (Current Implementation):
* **Language & Framework**: Python 3.8+ with FastAPI
* **FHIR Integration**: Custom FHIR R4 client with tenacity retry logic
* **Authentication**: OAuth2 JWT with Epic FHIR sandbox
* **Data Validation**: Pydantic models with computed fields
* **Environment Management**: python-dotenv for configuration
* **Dependencies**: 
  - fastapi, uvicorn, pydantic, pydantic-settings
  - requests, tenacity, python-jose
  - python-dotenv

### Key Features:
* **Robust Error Handling**: Custom exceptions and middleware
* **Retry Logic**: Exponential backoff for failed requests
* **Pagination Support**: Automatic FHIR Bundle pagination
* **Request Logging**: Comprehensive request tracking
* **Configuration Management**: Environment-based settings

### Future Frontend:
* **UI Framework**: React with TypeScript
* **Visualization**: Chart.js for clinical trends and risk visualization
* **SMART on FHIR**: EHR integration compatibility

---

## 📁 Current Project Structure

```
Sepsis-AI-Alert/
├── README.md                    # Project documentation
├── CLAUDE.md                    # Development instructions
├── LICENSE                      # MIT license
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Test configuration
├── start_server.py              # Automated server startup script
├── private.pem                  # RSA private key for JWT
├── public_cert.pem              # Public certificate
├── docs/                        # Documentation files
│   ├── API_DOCUMENTATION.md     # Comprehensive API docs
│   └── public.jwks              # JSON Web Key Set
├── backend/src/
│   ├── main.py                  # Application entry point
│   ├── app/                     # New modular FastAPI structure
│   │   ├── main.py              # FastAPI application
│   │   ├── core/                # Core functionality
│   │   │   ├── config.py        # Pydantic settings management
│   │   │   ├── dependencies.py  # Dependency injection
│   │   │   ├── exceptions.py    # Custom exceptions
│   │   │   ├── middleware.py    # Request logging middleware
│   │   │   └── loinc_codes.py   # Comprehensive LOINC mappings
│   │   ├── models/              # Pydantic data models
│   │   │   ├── patient.py       # Simplified patient demographics with flattened fields
│   │   │   ├── vitals.py        # Vital signs with sepsis scoring
│   │   │   ├── labs.py          # Laboratory results by category
│   │   │   ├── clinical.py      # Clinical context models
│   │   │   ├── sofa.py          # SOFA scoring models
│   │   │   ├── qsofa.py         # qSOFA scoring models
│   │   │   └── news2.py         # NEWS2 scoring models
│   │   ├── routers/             # FastAPI route handlers
│   │   │   ├── patients.py      # Patient demographics endpoints
│   │   │   ├── vitals.py        # Vital signs endpoints
│   │   │   ├── labs.py          # Laboratory results endpoints
│   │   │   ├── clinical.py      # Clinical context endpoints
│   │   │   └── sepsis_scoring.py # SOFA, qSOFA, and NEWS2 scoring endpoints
│   │   ├── services/            # Business logic services
│   │   │   ├── auth_client.py   # Enhanced OAuth2 JWT authentication
│   │   │   └── fhir_client.py   # Comprehensive FHIR R4 client
│   │   └── utils/               # Utility functions
│   │       ├── calculations.py  # Clinical calculations (age, BMI, etc.)
│   │       ├── date_utils.py    # FHIR datetime utilities
│   │       ├── fhir_utils.py    # FHIR bundle processing
│   │       ├── sofa_scoring.py  # SOFA scoring algorithms
│   │       ├── qsofa_scoring.py # qSOFA scoring algorithms
│   │       ├── news2_scoring.py # NEWS2 scoring algorithms with 85% API call reduction
│   │       ├── scoring_utils.py # Shared scoring utilities (DRY/KISS)
│   │       ├── tls_utils.py     # TLS certificate validation and context creation
│   │       └── error_handling.py # Standardized error handling
│   └── tests/                   # Comprehensive test suite
│       ├── conftest.py          # Pytest configuration
│       ├── fixtures/            # Test data fixtures
│       │   └── fhir_responses.py # Mock FHIR response data
│       ├── test_endpoints/      # API endpoint tests
│       │   ├── test_clinical.py # Clinical endpoints tests
│       │   ├── test_labs.py     # Laboratory endpoints tests
│       │   ├── test_patients.py # Patient endpoints tests
│       │   └── test_vitals.py   # Vital signs endpoints tests
│       └── test_fhir_client.py  # FHIR client service tests
└── venv/                        # Python virtual environment
```

---

## 🚀 API Endpoints

### Patient Demographics
- **`GET /api/v1/sepsis-alert/patients/{patient_id}`** - Patient demographics with computed fields
  - Returns: Patient info with calculated age, BMI, flattened address and demographics
  - Features: FHIR Patient resource integration, height/weight observations, simplified structure
- **`POST /api/v1/sepsis-alert/patients/match`** - Patient matching by demographics
  - Request Body: `PatientMatchRequest` with given name, family name, birth date, phone, and address
  - Returns: Ranked patient matches with similarity scores and match confidence
  - Features: FHIR Patient.$match operation, demographic-based search with certainty grading

### Vital Signs
- **`GET /api/v1/sepsis-alert/patients/{patient_id}/vitals`** - Time-series vital signs
  - Parameters: `start_date`, `end_date`, `vital_type` (HR, BP, TEMP, RR, SPO2, GCS)
  - Returns: Complete vital signs with sepsis scoring and clinical interpretation
  - Features: LOINC-based filtering, concurrent FHIR calls, trend analysis
- **`GET /api/v1/sepsis-alert/patients/{patient_id}/vitals/latest`** - Most recent vitals
  - Returns: Latest value for each vital sign type with risk assessment
  - Features: Optimized for real-time dashboards, parallel data retrieval

### Laboratory Results
- **`GET /api/v1/sepsis-alert/patients/{patient_id}/labs`** - Comprehensive lab results
  - Parameters: `start_date`, `end_date`, `lab_category` (CBC, METABOLIC, LIVER, INFLAMMATORY, BLOOD_GAS, COAGULATION)
  - Returns: Lab results organized by clinical category with organ dysfunction assessment
  - Features: LOINC code mapping, infection indicators, sepsis scoring
- **`GET /api/v1/sepsis-alert/patients/{patient_id}/labs/critical`** - Critical lab values
  - Returns: Abnormal values with interpretation flags and clinical significance
  - Features: Alert optimization, sepsis likelihood assessment

### Clinical Context
- **`GET /api/v1/sepsis-alert/patients/{patient_id}/encounter`** - Current encounter
  - Returns: Encounter details with ICU status, length of stay, admission type
  - Features: Location-based ICU detection, stay duration calculation
- **`GET /api/v1/sepsis-alert/patients/{patient_id}/conditions`** - Active conditions
  - Returns: Conditions with infection/sepsis classification
  - Features: ICD-10 coding, severity assessment, infection detection
- **`GET /api/v1/sepsis-alert/patients/{patient_id}/medications`** - Medications
  - Parameters: `medication_type` (ANTIBIOTICS, VASOPRESSORS, ALL)
  - Returns: Categorized medications with dosage and administration details
  - Features: Antibiotic class identification, vasopressor detection
- **`GET /api/v1/sepsis-alert/patients/{patient_id}/fluid-balance`** - Fluid balance
  - Parameters: `start_date`, `end_date`
  - Returns: Intake/output analysis with oliguria detection
  - Features: Net balance calculation, hourly urine rate monitoring

### Sepsis Scoring Endpoints
- **`GET /api/v1/sepsis-alert/patients/{patient_id}/sepsis-score`** - Comprehensive sepsis & deterioration risk assessment
  - Query Parameters: `timestamp`, `include_parameters`, `scoring_systems` (SOFA, qSOFA, NEWS2, or any combination - **all three by default**)
  - Returns: Complete assessment with SOFA score (0-24), qSOFA score (0-3), and NEWS2 score (0-20) with mortality risk, organ dysfunction, clinical deterioration assessment, and alerts
  - Features: **Triple scoring system with 85% API call reduction**, intelligent parameter reuse, NHS-compliant NEWS2 standards, combined risk stratification (MINIMAL/LOW/MODERATE/HIGH/CRITICAL), clinical recommendations
- **`POST /api/v1/sepsis-alert/patients/sepsis-score-direct`** - Direct parameter sepsis scoring (no FHIR calls)
  - Request Body: `DirectSepsisScoreRequest` with clinical parameters provided directly
  - Returns: Same comprehensive assessment as FHIR-based endpoint
  - Features: **External system integration**, manual parameter entry, testing/validation support, emergency situations with limited FHIR access
- **`POST /api/v1/sepsis-alert/patients/batch-sepsis-scores`** - Batch comprehensive scoring (max 50 patients)
  - Request Body: `BatchSepsisScoreRequest` with patient IDs and scoring parameters
  - Returns: Individual SOFA, qSOFA, and NEWS2 scores for all patients with error handling for failed calculations
  - Features: Dashboard integration, population monitoring, high-risk patient identification, **triple scoring assessment with data reuse optimization**, performance optimization through parameter sharing

### System Endpoints
- **`GET /health`** - Application health check
- **`GET /api/docs`** - Interactive API documentation (Swagger UI)

---

## 🔧 Installation & Setup

### Prerequisites
- **Python 3.8+** with pip
- **Epic FHIR R4 sandbox credentials** (client ID, private key)
- **Virtual environment** (recommended)
- **Git** for cloning the repository

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Sepsis-AI-Alert
   ```

2. **Create and activate virtual environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # Windows
   venv\Scripts\activate
   # Unix/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create `backend/src/.env` file with your Epic FHIR credentials:
   ```env
   # Epic FHIR Configuration
   CLIENT_ID=your_epic_client_id
   TOKEN_URL=https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token
   PRIVATE_KEY_PATH=./private.pem
   FHIR_API_BASE=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
   
   # Application Configuration
   LOG_LEVEL=INFO
   API_HOST=localhost
   API_PORT=8000
   
   # TLS Configuration (optional)
   TLS_ENABLED=false
   TLS_CERT_FILE=public_cert.pem
   TLS_KEY_FILE=private.pem
   TLS_PORT=8443
   FORCE_HTTPS=false
   TLS_VERSION=TLS
   ```

5. **Set up RSA private key**
   - Place your Epic FHIR private key as `private.pem` in the project root
   - Ensure proper file permissions: `chmod 600 private.pem` (Unix/macOS)

6. **Run the application**
   ```bash
   # Recommended: Automated startup script (handles venv activation and directory navigation)
   python start_server.py
   
   # Alternative: Manual startup
   # First activate virtual environment:
   # Windows: venv\Scripts\activate
   # Unix/macOS: source venv/bin/activate
   # Then navigate and start server:
   cd backend/src
   python main.py
   # or
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```


### Testing the API

1. **Health Check**
   ```bash
   curl http://localhost:8000/health
   ```

2. **API Documentation**
   - Swagger UI: `http://localhost:8000/api/docs`

3. **Sample API Calls** (with Epic FHIR sandbox)
   ```bash
   # Get patient demographics
   curl -X GET \
     "http://localhost:8000/api/v1/sepsis-alert/patients/eRztxMp7qoNfNGkSiB7rDuB" \
     -H "Accept: application/json"
   
   # Match patient by demographics
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
   
   # Get patient vital signs
   curl -X GET \
     "http://localhost:8000/api/v1/sepsis-alert/patients/eRztxMp7qoNfNGkSiB7rDuB/vitals/latest" \
     -H "Accept: application/json"
   
   # FHIR-based sepsis scoring (fetches data from Epic)
   curl -X GET \
     "http://localhost:8000/api/v1/sepsis-alert/patients/eRztxMp7qoNfNGkSiB7rDuB/sepsis-score?scoring_systems=SOFA,qSOFA,NEWS2" \
     -H "Accept: application/json"
   
   # Direct parameter sepsis scoring (no FHIR calls required)
   curl -X POST \
     "http://localhost:8000/api/v1/sepsis-alert/patients/sepsis-score-direct" \
     -H "Content-Type: application/json" \
     -d '{
       "patient_id": "direct-test-001",
       "respiratory_rate": 24,
       "systolic_bp": 95,
       "glasgow_coma_scale": 12,
       "heart_rate": 105,
       "temperature": 38.8,
       "oxygen_saturation": 92,
       "supplemental_oxygen": true,
       "platelets": 90,
       "creatinine": 2.2,
       "scoring_systems": "SOFA,qSOFA,NEWS2"
     }'
   ```


---

## 💡 Direct Parameter Integration

The system now supports **direct parameter input** for sepsis scoring, providing flexibility for external systems and manual data entry scenarios.

### Use Cases for Direct Parameter Endpoint

**External System Integration**
- Non-FHIR systems that want to leverage sepsis scoring algorithms
- Legacy EHR systems without FHIR R4 support
- Third-party clinical applications requiring sepsis risk assessment

**Clinical Scenarios**
- Manual parameter entry during emergency situations
- Bedside risk assessment with limited EHR access
- Educational and training environments
- Research and algorithm validation studies

**Testing and Development**
- Controlled parameter testing for algorithm validation
- Performance testing without FHIR dependency
- Integration testing with known parameter sets
- Clinical decision support system development

### Parameter Categories

**Required Parameters (Minimum Viable Assessment)**
```json
{
  "patient_id": "string",
  "respiratory_rate": "number (breaths/min)",
  "systolic_bp": "number (mmHg)",
  "glasgow_coma_scale": "number (3-15)"
}
```

**Complete Parameter Set (Maximum Clinical Value)**
```json
{
  "patient_id": "string",
  "timestamp": "ISO 8601 datetime",
  
  // SOFA Parameters
  "pao2": "number (mmHg)",
  "fio2": "number (0.21-1.0)",
  "mechanical_ventilation": "boolean",
  "platelets": "number (x10³/μL)",
  "bilirubin": "number (mg/dL)",
  "systolic_bp": "number (mmHg)",
  "diastolic_bp": "number (mmHg)",
  "mean_arterial_pressure": "number (mmHg)",
  "glasgow_coma_scale": "number (3-15)",
  "creatinine": "number (mg/dL)",
  "urine_output_24h": "number (mL)",
  
  // Vasopressor Doses (mcg/kg/min)
  "dopamine": "number",
  "dobutamine": "number",
  "epinephrine": "number",
  "norepinephrine": "number",
  "phenylephrine": "number",
  
  // Vital Signs (shared across systems)
  "respiratory_rate": "number (breaths/min)",
  "heart_rate": "number (bpm)",
  "temperature": "number (°C)",
  "oxygen_saturation": "number (%)",
  "supplemental_oxygen": "boolean",
  
  // Configuration
  "scoring_systems": "string (SOFA,qSOFA,NEWS2)",
  "include_parameters": "boolean",
  "hypercapnic_respiratory_failure": "boolean"
}
```

### Clinical Default Values

When parameters are not provided, the system applies clinically appropriate defaults:
- **Respiratory Rate**: 16 breaths/min
- **Systolic BP**: 120 mmHg
- **Glasgow Coma Scale**: 15 (normal)
- **Heart Rate**: 70 bpm
- **Temperature**: 37°C
- **Oxygen Saturation**: 98%
- **Laboratory Values**: Normal reference ranges

### Response Format

The direct parameter endpoint returns **identical response format** to the FHIR-based endpoint, ensuring compatibility with existing integrations:

```json
{
  "patient_id": "string",
  "timestamp": "ISO 8601 datetime",
  "sofa_score": { "total_score": "0-24", "risk_level": "string" },
  "qsofa_score": { "total_score": "0-3", "risk_level": "string" },
  "news2_score": { "total_score": "0-20", "risk_level": "string" },
  "sepsis_assessment": {
    "risk_level": "MINIMAL|LOW|MODERATE|HIGH|CRITICAL",
    "recommendation": "string",
    "requires_immediate_attention": "boolean"
  },
  "calculation_metadata": {
    "estimated_parameters": "number",
    "missing_parameters": "array",
    "calculation_time_ms": "number"
  }
}
```

---

## 🔒 Security & Compliance

- **OAuth2 JWT Authentication**: Secure token-based authentication with Epic FHIR
- **Environment Configuration**: Sensitive data managed via environment variables
- **Request Validation**: Comprehensive Pydantic model validation
- **Error Handling**: Secure error responses without data leakage
- **HIPAA Considerations**: No PHI logging, secure data processing

---

## 🚀 Future Enhancements

### Immediate Roadmap
- [x] Complete FHIR client implementation with data processing
- [x] Implement comprehensive sepsis scoring algorithms (SOFA and qSOFA)
- [x] Implement NEWS2 (National Early Warning Score) integration with data reuse optimization
- [x] Deploy triple scoring system with 85% API call reduction through parameter reuse
- [x] Implement NHS-compliant NEWS2 clinical standards and risk stratification
- [ ] Add real-time alerting system with trend analysis
- [ ] Create clinical dashboard frontend

### Long-term Vision
- [ ] Machine learning model integration
- [ ] Real-time streaming data processing
- [ ] Integration with Epic App Orchard
- [ ] Multi-condition alerting (ARDS, AMI, PE, Stroke)
- [ ] Clinical workflow integration
- [ ] Explainable AI features (SHAP/LIME)

---

## 📢 Contributions

Contributions are welcome! Please open an issue or submit a pull request for enhancements or bug fixes.

---

## 📄 License

Distributed under the MIT License.

---
