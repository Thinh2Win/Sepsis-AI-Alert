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

### Backend Structure (`backend/src/app/`)

#### Core (`app/core/`)
- **main.py**: FastAPI application setup
- **config.py**: Environment settings management
- **auth.py**: Auth0 JWT verification middleware
- **exceptions.py**: Custom exception classes
- **middleware.py**: Request logging and Auth0 authentication with RBAC
- **permissions.py**: RBAC permission validation system
- **loinc_codes.py**: Clinical code mappings

#### Models (`app/models/`)
- **patient.py**: Patient demographics
- **vitals.py**: Vital signs data
- **labs.py**: Laboratory results
- **clinical.py**: Clinical context
- **sofa.py**: SOFA scoring models
- **qsofa.py**: qSOFA scoring models
- **news2.py**: NEWS2 scoring models

#### Services (`app/services/`)
- **auth_client.py**: Epic OAuth2 JWT authentication for FHIR access
- **fhir_client.py**: FHIR R4 client
- **sepsis_scoring_service.py**: Scoring calculations
- **sepsis_response_builder.py**: Response building

#### Utils (`app/utils/`)
- **calculations.py**: Clinical calculations
- **fhir_utils.py**: FHIR data processing
- **scoring_utils.py**: Shared scoring functions
- **sofa_scoring.py**: SOFA algorithms
- **qsofa_scoring.py**: qSOFA algorithms
- **news2_scoring.py**: NEWS2 algorithms

### Key Dependencies

- **FastAPI**: Web framework
- **pydantic**: Data validation
- **python-jose**: JWT authentication (Auth0 + Epic)
- **uvicorn**: ASGI server
- **tenacity**: Retry logic
- **requests**: HTTP client

### FHIR Integration

The system integrates with Epic FHIR R4 APIs for:

#### Patient Data
- Demographics (age, BMI, contacts)
- Vital signs (heart rate, BP, temperature, respiratory rate, oxygen saturation, GCS)
- Laboratory results (CBC, metabolic panel, liver function, inflammatory markers, blood gas, coagulation)
- Clinical context (encounters, conditions, medications, fluid balance)

### Configuration

Environment variables in `backend/src/.env`:

#### Epic FHIR Authentication
- **CLIENT_ID**: Epic app client identifier
- **TOKEN_URL**: OAuth2 token endpoint
- **PRIVATE_KEY_PATH**: RSA private key path
- **FHIR_API_BASE**: FHIR API base URL

#### Auth0 Authentication
- **AUTH0_DOMAIN**: Auth0 domain for JWT verification
- **AUTH0_API_AUDIENCE**: Auth0 API audience identifier

## Dual Authentication System with RBAC

The system implements two authentication layers with role-based access control:

### Inbound API Protection (Auth0 + RBAC)
- **Purpose**: Protects FastAPI endpoints from unauthorized access with permission validation
- **Implementation**: Global middleware in `auth.py` and `middleware.py` + permission dependencies in `permissions.py`
- **Token Source**: Auth0 JWT tokens with `"read:phi"` permission in Authorization header
- **RBAC**: All clinical endpoints require `"read:phi"` permission for PHI access
- **Scope**: All clinical API endpoints require valid Auth0 JWT with proper permissions
- **Public Exceptions**: `/health`, `/docs`, `/redoc`, `/openapi.json` remain publicly accessible

### Outbound FHIR Access (Epic OAuth2)
- **Purpose**: Authenticates with Epic FHIR sandbox for patient data
- **Implementation**: `auth_client.py` service for token management
- **Token Source**: Client credentials flow with RSA JWT assertion
- **Scope**: FHIR API calls to Epic sandbox

### HIPAA-Compliant Audit Logging
- **PHI Protection**: All patient IDs sanitized in logs (replaced with `***`)
- **Access Tracking**: Every PHI access attempt logged with user ID, endpoint, and result
- **Compliance**: Structured audit trail for regulatory compliance

## Scoring Systems

### SOFA (Sequential Organ Failure Assessment)
- **Purpose**: 6-organ system assessment for sepsis severity
- **Parameters**: 24 clinical parameters across respiratory, coagulation, liver, cardiovascular, CNS, and renal systems
- **Time Window**: 24-hour lookback

### qSOFA (Quick SOFA)
- **Purpose**: Rapid bedside sepsis screening
- **Parameters**: 3 core parameters (respiratory rate ≥22, systolic BP ≤100, GCS <15)
- **Time Window**: 4-hour lookback
- **Risk**: Score ≥2 indicates high mortality risk

### NEWS2 (National Early Warning Score 2)
- **Purpose**: Clinical deterioration detection
- **Parameters**: 7 parameters (respiratory rate, SpO2, supplemental O2, temperature, systolic BP, heart rate, consciousness)
- **Performance**: 85% parameter reuse from SOFA/qSOFA data

### Direct Parameter Input
Alternative endpoint accepts clinical parameters directly without FHIR calls for external system integration.

## API Endpoints

### Core Endpoints
- `GET /api/v1/sepsis-alert/patients/{patient_id}` - Patient demographics
- `POST /api/v1/sepsis-alert/patients/match` - Patient matching
- `GET /api/v1/sepsis-alert/patients/{patient_id}/vitals` - Vital signs
- `GET /api/v1/sepsis-alert/patients/{patient_id}/labs` - Laboratory results
- `GET /api/v1/sepsis-alert/patients/{patient_id}/encounter` - Clinical context

### Scoring Endpoints
- `GET /api/v1/sepsis-alert/patients/{patient_id}/sepsis-score` - Triple scoring (SOFA, qSOFA, NEWS2)
- `POST /api/v1/sepsis-alert/patients/sepsis-score-direct` - Direct parameter scoring
- `POST /api/v1/sepsis-alert/patients/batch-sepsis-scores` - Batch processing

## ML Feature Engineering Pipeline

The system includes an advanced feature engineering pipeline for early sepsis detection that goes beyond traditional SOFA/qSOFA scoring to identify hidden, early, and personalized patterns.

### Architecture (`app/ml/`)

#### Feature Definitions (`feature_definitions.py`)
- **Clinical Features**: Comprehensive metadata for 80+ advanced features with clinical rationale
- **Feature Calculations**: Lambda functions for computing derived features from raw clinical data
- **Feature Dependencies**: Dependency mapping for proper feature ordering
- **Validation Rules**: Clinical bounds for all parameters and derived features

#### Feature Engineering (`feature_engineering.py`)
- **SepsisFeatureEngineer**: Main pipeline class for transforming raw clinical parameters
- **Version Tracking**: Feature engineering version management for reproducibility
- **Quality Metrics**: Feature completeness and reliability scoring
- **Batch Processing**: Support for both single prediction and batch transformation

#### ML Models (`ml_features.py`)
- **RawClinicalParameters**: Pydantic model for input validation
- **EngineeredFeatureSet**: Complete set of 76 engineered features for ML training
- **FeatureQualityMetrics**: Metadata about feature quality and completeness

### Advanced Features for Early Sepsis Detection

#### Hidden Patterns (Complex Interactions)
- **Age-adjusted shock indices**: Personalizes hemodynamic assessment by age
- **Multi-organ interaction scores**: Captures cross-system organ dysfunction
- **Complex hemodynamic ratios**: Pulse pressure ratios, perfusion pressure calculations
- **Vasopressor load scoring**: Norepinephrine-equivalent dosing across multiple agents

#### Early Patterns (4-6 Hours Before Traditional Alerts)
- **Compensated vs. decompensated shock detection**: Identifies pre-failure states
- **Work of breathing estimation**: Subtle respiratory distress before obvious failure
- **Relative bradycardia patterns**: Temperature-HR dissociation in sepsis
- **Subtle organ dysfunction indicators**: Early AKI, coagulopathy, hepatic changes

#### Personalized Patterns (Age/Comorbidity-Specific)
- **Age-stratified risk indicators**: Adjusts features for pediatric, adult, elderly patients
- **Estimated GFR calculations**: Age and gender-adjusted renal function
- **Organ-specific dysfunction scoring**: Tailored thresholds for different organ systems
- **Critical illness severity scoring**: Personalized intervention intensity assessment

### Integration with Traditional Scoring

The ML pipeline enhances rather than replaces traditional scoring:
- **SOFA/qSOFA/NEWS2 compatibility**: All traditional parameters included
- **Enhanced data generator**: Creates synthetic training data with traditional score labels
- **Feature reuse optimization**: Leverages existing clinical calculations
- **Backward compatibility**: Maintains existing API endpoints and scoring functionality

### Training Data Pipeline

1. **Enhanced Data Generator** → Creates realistic patient cases with SOFA/qSOFA/NEWS2 labels
2. **Feature Engineering** → Extracts 76 advanced features capturing subtle patterns
3. **ML Model Training** → Learns to predict sepsis 4-6 hours before traditional alerts
4. **Validation** → 100% feature alignment between engineering and ML models confirmed

## Implementation Status

### ✅ Completed
- FastAPI application structure
- Authentication service (OAuth2 JWT)
- **RBAC permission system with "read:phi" validation**
- **HIPAA-compliant audit logging with PHI sanitization**
- FHIR client with retry logic
- Data models and validation
- SOFA, qSOFA, and NEWS2 scoring
- Triple scoring system with data reuse optimization
- Direct parameter input endpoint
- Batch processing capabilities
- **ML feature engineering pipeline with 76 advanced features**
- **Enhanced data generator for ML training data**
- **Complete feature definitions with clinical rationale**
- **Feature engineering validation and integration testing**
- **✨ ENHANCED (Dec 2024): Production-ready ML pipeline improvements**
  - Complete NEWS2 scoring implementation (no more placeholders)
  - Centralized clinical constants and configuration management
  - Comprehensive error handling and input validation
  - Professional showcase documentation and demo scripts

### 🔄 In Progress
- Trend analysis for historical scoring
- Real-time ML prediction API endpoints

### 📋 Next Steps
- ML model deployment and inference endpoints (training pipeline ✅ complete)
- Epic FHIR R4 sandbox testing
- Early sepsis alert dashboard with ML predictions
- Real-time alerting with 4-6 hour lead time