# 🩺 Sepsis AI EHR Alert System

An AI-powered Clinical Decision Support (CDS) tool integrated with Electronic Health Records (EHRs) leveraging FHIR interoperability standards to proactively detect sepsis in hospitalized patients.

---

## 📖 Project Overview

**Sepsis** is a life-threatening medical condition triggered by the body's extreme response to an infection. Each hour that treatment is delayed increases mortality by approximately **8%**. Timely identification and intervention are critical to patient survival and outcome improvement.

This project showcases a practical application of Artificial Intelligence (AI) and interoperability in healthcare. Using Fast Healthcare Interoperability Resources (FHIR), this clinical decision support system:

* Ingests real-time patient data from EHRs.
* Predicts sepsis risk through AI-driven models.
* Clearly visualizes risks, providing actionable insights to clinicians through a modern UI integrated into existing clinical workflows.

---

## 🎯 Objectives

* **Clinical Objective:**

  * Rapidly detect and predict sepsis using clinically validated scoring systems (e.g., SIRS, qSOFA, SOFA scores).
  * Alert clinicians proactively, clearly indicating severity and recommended interventions.

* **Technical Objective:**

  * Leverage FHIR resources to ingest, normalize, and extract features from clinical data.
  * Integrate securely with AI predictive models for real-time inference.
  * Implement explainability tools (SHAP/LIME) for clinician trust and actionable insights.
  * Demonstrate secure, HIPAA-compliant architecture principles.

---

## 📊 Clinical Indicators & Scoring

The AI model analyzes the following clinical indicators from standardized FHIR resources:

| FHIR Resource               | Clinical Indicators                                                                                     |
| --------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Patient**                 | Age, Gender, Chronic conditions                                                                         |
| **Observation**             | Heart rate, Respiratory rate, Temperature, Blood Pressure, Oxygen Saturation, WBC count, Lactate levels |
| **Encounter**               | Encounter type, Admission & discharge dates, Clinical context                                           |
| **Condition** *(optional)*  | Relevant medical conditions                                                                             |
| **Medication** *(optional)* | Antibiotics administration                                                                              |

### Sepsis Severity Levels

* 🟢 **Low Risk**
* 🟡 **Moderate Risk (Monitor closely)**
* 🔴 **High Risk (Immediate intervention recommended)**

---

## 🖥️ Architecture Overview

```
                       ┌─────────────────────────────┐
                       │      EHR (FHIR API)         │
                       └─────────────┬───────────────┘
                                     │ (FHIR Resources)
                                     ▼
                   ┌───────────────────────────────────┐
                   │      Sepsis Alert AI System       │
                   │ ┌───────────────────────────────┐ │
                   │ │       Data Ingestion          │ │
                   │ └───────────────┬───────────────┘ │
                   │                 │                 │
                   │ ┌───────────────▼───────────────┐ │
                   │ │ Data Normalization & Feature  │ │
                   │ │          Extraction           │ │
                   │ └───────────────┬───────────────┘ │
                   │                 │                 │
                   │ ┌───────────────▼───────────────┐ │
                   │ │      AI Predictive Model      │ │
                   │ └───────────────┬───────────────┘ │
                   │                 │                 │
                   │ ┌───────────────▼───────────────┐ │
                   │ │  Explainability (SHAP/LIME)   │ │
                   │ └───────────────┬───────────────┘ │
                   │                 │                 │
                   │ ┌───────────────▼───────────────┐ │
                   │ │      Alert Orchestration      │ │
                   │ └───────────────┬───────────────┘ │
                   └─────────────────┼─────────────────┘
                                     │ (Alerts)
                                     ▼
                    ┌───────────────────────────────────┐
                    │ React Dashboard / SMART on FHIR UI│
                    └───────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Backend:

* **Language & Framework**: Node.js (Express/Fastify) or Python (Flask/FastAPI)
* **FHIR Integration**: [FHIR.js](https://github.com/FHIR/fhir.js) or HAPI-FHIR
* **AI Integration**: Secure REST APIs (pre-built or fine-tuned models)
* **Containerization**: Docker, Docker Compose
* **Explainability**: SHAP, LIME

### Frontend:

* **UI Framework**: React
* **Visualization Libraries**: Chart.js or Recharts for displaying risk factors and explainability visuals
* **SMART on FHIR**: Integration compatibility for EHR embedding

### Infrastructure & Deployment (Recommended Setup):

* **Local Development**: Docker Compose
* **Cloud (Optional)**: AWS (ECS, Fargate), Azure (AKS), or GCP (Cloud Run)

### Security & Compliance:

* HIPAA-compliant data handling strategies
* Secure handling of PHI with encryption at rest/in-transit
* OAuth 2.0 / OpenID Connect for secure authentication

---

## 📁 Project Structure

```
sepsis-alert-system/
├── README.md                  # Project overview, architecture, tech stack
├── backend/
│   ├── src/
│   │   ├── api/               # API routes/endpoints
│   │   ├── controllers/       # Request handling logic
│   │   ├── services/          # Business logic (FHIR ingestion, AI integration)
│   │   └── models/            # Data schemas
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── pages/             # Main dashboard and pages
│   │   └── hooks/             # Custom React hooks
│   ├── Dockerfile
│   └── package.json
└── docs/
    ├── clinical_requirements.md
    └── technical_requirements.md
```

---

## 🚀 Future Enhancements

* Real-time streaming integration
* More advanced AI model fine-tuning
* Integration with clinical workflows (e.g. Epic App Orchard APIs)
* Additional condition support alerts (e.g. ARDS, AMI, PE, Stroke)

---

## 📢 Contributions

Contributions are welcome! Please open an issue or submit a pull request for enhancements or bug fixes.

---

## 📄 License

Distributed under the MIT License.

---
