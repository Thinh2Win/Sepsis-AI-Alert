from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import datetime
from app.models.labs import LabResultsResponse, CriticalLabsResponse
from app.services.fhir_client import FHIRClient
from app.core.dependencies import get_fhir_client

router = APIRouter()

@router.get("/patients/{patient_id}/labs", response_model=LabResultsResponse)
async def get_labs(
    patient_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date for lab results (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date for lab results (ISO format)"),
    lab_category: Optional[str] = Query(None, description="Lab category (CBC, METABOLIC, LIVER, INFLAMMATORY, BLOOD_GAS, COAGULATION)"),
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """
    Retrieve patient laboratory results within date range with optional category filtering.
    
    **Lab Categories:**
    - CBC: WBC Count (LOINC: 6690-2), Platelet Count (LOINC: 777-3)
    - METABOLIC: Creatinine (LOINC: 2160-0), BUN (LOINC: 3094-0), Glucose (LOINC: 2345-7)
    - LIVER: Bilirubin (LOINC: 1975-2), Albumin (LOINC: 1742-6), LDH (LOINC: 14804-9)
    - INFLAMMATORY: CRP (LOINC: 1988-5), Procalcitonin (LOINC: 75241-0)
    - BLOOD_GAS: Lactate (LOINC: 2019-8), pH (LOINC: 2744-1), PaO2/FiO2 (LOINC: 50984-4)
    - COAGULATION: PT/INR (LOINC: 5902-2), PTT (LOINC: 3173-2)
    
    If no lab_category is specified, all categories will be fetched concurrently.
    """
    return await fhir_client.get_labs(patient_id, start_date, end_date, lab_category)

@router.get("/patients/{patient_id}/labs/critical", response_model=CriticalLabsResponse)
async def get_critical_labs(
    patient_id: str,
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """
    Retrieve critical/abnormal lab values for patient.
    
    Only returns lab values with abnormal interpretation flags:
    - H, HH: High/Critical High values
    - L, LL: Low/Critical Low values  
    - A, AA: Abnormal/Critical Abnormal values
    
    Results include reference ranges and interpretation flags for clinical decision support.
    """
    return await fhir_client.get_critical_labs(patient_id)