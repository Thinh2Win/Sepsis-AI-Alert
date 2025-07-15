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
├── requirements.txt             # Python dependencies
├── backend/src/
│   ├── main.py                  # Application entry point
│   ├── auth.py                  # Legacy auth (preserved)
│   ├── config.py                # Legacy config (preserved)
│   ├── fetch_patient.py         # Legacy FHIR client (preserved)
│   └── app/                     # New modular FastAPI structure
│       ├── main.py              # FastAPI application
│       ├── core/                # Core functionality
│       │   ├── config.py        # Settings management
│       │   ├── dependencies.py  # Dependency injection
│       │   ├── exceptions.py    # Custom exceptions
│       │   ├── middleware.py    # Request middleware
│       │   └── loinc_codes.py   # LOINC code mappings
│       ├── models/              # Pydantic models
│       │   ├── patient.py       # Patient demographics
│       │   ├── vitals.py        # Vital signs with scoring
│       │   ├── labs.py          # Laboratory results
│       │   └── clinical.py      # Clinical context
│       ├── routers/             # API endpoints
│       │   ├── patients.py      # Patient endpoints
│       │   ├── vitals.py        # Vital signs endpoints
│       │   ├── labs.py          # Laboratory endpoints
│       │   └── clinical.py      # Clinical context endpoints
│       ├── services/            # Business logic
│       │   ├── auth_client.py   # OAuth2 authentication
│       │   └── fhir_client.py   # FHIR API client
│       └── utils/               # Utility functions
│           ├── calculations.py  # Clinical calculations
│           ├── date_utils.py    # Date/time utilities
│           └── fhir_utils.py    # FHIR processing utilities
└── venv/                        # Python virtual environment
```

---

## 🚀 API Endpoints

### Patient Demographics
- `GET /api/v1/sepsis-alert/patients/{patient_id}` - Patient demographics with computed age, BMI
- `POST /api/v1/sepsis-alert/patients/match` - Patient matching by demographics

### Vital Signs
- `GET /api/v1/sepsis-alert/patients/{patient_id}/vitals` - Time-series vital signs with sepsis scoring
- `GET /api/v1/sepsis-alert/patients/{patient_id}/vitals/latest` - Most recent vitals with risk assessment

### Laboratory Results
- `GET /api/v1/sepsis-alert/patients/{patient_id}/labs` - Comprehensive lab results by category
- `GET /api/v1/sepsis-alert/patients/{patient_id}/labs/critical` - Critical/abnormal lab values

### Clinical Context
- `GET /api/v1/sepsis-alert/patients/{patient_id}/encounter` - Current encounter information
- `GET /api/v1/sepsis-alert/patients/{patient_id}/conditions` - Active conditions and diagnoses
- `GET /api/v1/sepsis-alert/patients/{patient_id}/medications` - Medications with antibiotic/vasopressor filtering
- `GET /api/v1/sepsis-alert/patients/{patient_id}/fluid-balance` - Fluid intake/output analysis

---

## 🔧 Installation & Setup

### Prerequisites
- Python 3.8+
- Epic FHIR R4 sandbox credentials
- Virtual environment (recommended)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Sepsis-AI-Alert
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
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
   Create `backend/src/.env` file:
   ```env
   CLIENT_ID=your_epic_client_id
   TOKEN_URL=https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token
   PRIVATE_KEY_PATH=path/to/private_key.pem
   FHIR_API_BASE=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
   ```

5. **Run the application**
   ```bash
   cd backend/src
   python main.py
   # or
   uvicorn main:app --reload
   ```

### Testing the API
- Health check: `GET http://localhost:8000/health`
- API documentation: `http://localhost:8000/api/docs`
- Patient data: `GET http://localhost:8000/api/v1/sepsis-alert/patients/{patient_id}`

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
