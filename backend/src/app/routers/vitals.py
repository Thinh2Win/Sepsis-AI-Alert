from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import datetime
from app.models.vitals import VitalSignsResponse, VitalSignsLatestResponse
from app.services.fhir_client import FHIRClient
from app.core.dependencies import get_fhir_client

router = APIRouter()

@router.get("/patients/{patient_id}/vitals", response_model=VitalSignsResponse)
async def get_vitals(
    patient_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date for vital signs"),
    end_date: Optional[datetime] = Query(None, description="End date for vital signs"),
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """Retrieve patient vital signs within date range"""
    return await fhir_client.get_vitals(patient_id, start_date, end_date)

@router.get("/patients/{patient_id}/vitals/latest", response_model=VitalSignsLatestResponse)
async def get_latest_vitals(
    patient_id: str,
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """Retrieve most recent vital signs for patient"""
    return await fhir_client.get_latest_vitals(patient_id)