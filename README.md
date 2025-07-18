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
  * Rapidly detect and predict sepsis using clinically validated scoring systems (SIRS, qSOFA, SOFA scores)
  * Alert clinicians proactively with severity indicators and recommended interventions
  * Provide comprehensive sepsis-related data aggregation and trend analysis

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

### Sepsis Risk Assessment Levels
* 🟢 **MINIMAL** - No significant risk factors
* 🟡 **LOW** - 1-2 risk factors present
* 🟠 **MODERATE** - 3-4 risk factors present  
* 🔴 **HIGH** - 5+ risk factors present
* 🚨 **CRITICAL** - Immediate intervention required

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
├── private.pem                  # RSA private key for JWT
├── public_cert.pem              # Public certificate
├── docs/                        # Documentation files
│   ├── API_DOCUMENTATION.md     # Comprehensive API docs
│   └── public.jwks              # JSON Web Key Set
├── backend/src/
│   ├── main.py                  # Application entry point
│   ├── app/                     # New modular FastAPI structure
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── core/                # Core functionality
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # Pydantic settings management
│   │   │   ├── dependencies.py  # Dependency injection
│   │   │   ├── exceptions.py    # Custom exceptions
│   │   │   ├── middleware.py    # Request logging middleware
│   │   │   └── loinc_codes.py   # Comprehensive LOINC mappings
│   │   ├── models/              # Pydantic data models
│   │   │   ├── __init__.py
│   │   │   ├── patient.py       # Patient demographics with computed fields
│   │   │   ├── vitals.py        # Vital signs with sepsis scoring
│   │   │   ├── labs.py          # Laboratory results by category
│   │   │   └── clinical.py      # Clinical context models
│   │   ├── routers/             # FastAPI route handlers
│   │   │   ├── __init__.py
│   │   │   ├── patients.py      # Patient demographics endpoints
│   │   │   ├── vitals.py        # Vital signs endpoints
│   │   │   ├── labs.py          # Laboratory results endpoints
│   │   │   └── clinical.py      # Clinical context endpoints
│   │   ├── services/            # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── auth_client.py   # Enhanced OAuth2 JWT authentication
│   │   │   └── fhir_client.py   # Comprehensive FHIR R4 client
│   │   └── utils/               # Utility functions
│   │       ├── __init__.py
│   │       ├── calculations.py  # Clinical calculations (age, BMI, etc.)
│   │       ├── date_utils.py    # FHIR datetime utilities
│   │       └── fhir_utils.py    # FHIR bundle processing
│   └── tests/                   # Comprehensive test suite
│       ├── __init__.py
│       ├── conftest.py          # Pytest configuration
│       ├── fixtures/            # Test data fixtures
│       │   ├── __init__.py
│       │   └── fhir_responses.py # Mock FHIR response data
│       ├── test_endpoints/      # API endpoint tests
│       │   ├── __init__.py
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
  - Returns: Patient info with calculated age, BMI, primary contact
  - Features: FHIR Patient resource integration, height/weight observations
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
   ```

5. **Set up RSA private key**
   - Place your Epic FHIR private key as `private.pem` in the project root
   - Ensure proper file permissions: `chmod 600 private.pem` (Unix/macOS)

6. **Run the application**
   ```bash
   cd backend/src
   
   # Option 1: Direct Python execution
   python main.py
   
   # Option 2: Using uvicorn (recommended for development)
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Option 3: Production mode
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

### Running Tests

The project includes a comprehensive test suite using pytest:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=app

# Run specific test files
pytest backend/src/tests/test_endpoints/test_patients.py

# Run tests with verbose output
pytest -v

# Run tests and generate HTML coverage report
pytest --cov=app --cov-report=html
```

### Testing the API

1. **Health Check**
   ```bash
   curl http://localhost:8000/health
   ```

2. **API Documentation**
   - Swagger UI: `http://localhost:8000/api/docs`
   - ReDoc: `http://localhost:8000/redoc`

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
   ```

### Development Setup

For development with auto-reload and debugging:

```bash
# Install development dependencies (if any)
pip install -r requirements-dev.txt  # if exists

# Run with debug mode and auto-reload
uvicorn app.main:app --reload --debug --host 0.0.0.0 --port 8000

# Run tests in watch mode (requires pytest-watch)
ptw backend/src/tests/
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
- [ ] Complete FHIR client implementation with data processing
- [ ] Implement comprehensive sepsis scoring algorithms
- [ ] Add real-time alerting system
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
