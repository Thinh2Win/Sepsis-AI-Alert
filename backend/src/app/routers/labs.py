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
    start_date: Optional[datetime] = Query(None, description="Start date for lab results"),
    end_date: Optional[datetime] = Query(None, description="End date for lab results"),
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """Retrieve patient laboratory results within date range"""
    return await fhir_client.get_labs(patient_id, start_date, end_date)

@router.get("/patients/{patient_id}/labs/critical", response_model=CriticalLabsResponse)
async def get_critical_labs(
    patient_id: str,
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """Retrieve critical/abnormal lab values for patient"""
    return await fhir_client.get_critical_labs(patient_id)