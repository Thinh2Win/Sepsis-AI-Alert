from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import datetime
from app.models.vitals import VitalSignsResponse, VitalSignsLatestResponse
from app.services.fhir_client import FHIRClient
from app.core.dependencies import get_fhir_client
from app.core.permissions import require_permission

router = APIRouter()

@router.get("/patients/{patient_id}/vitals", response_model=VitalSignsResponse)
async def get_vitals(
    patient_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date for vital signs (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date for vital signs (ISO format)"),
    vital_type: Optional[str] = Query(None, description="Specific vital sign type (HR, BP, TEMP, RR, SPO2, GCS)"),
    fhir_client: FHIRClient = Depends(get_fhir_client),
    _: dict = Depends(require_permission("read:phi"))
):
    """
    Retrieve patient vital signs within date range with optional filtering by vital type.
    
    **Vital Types:**
    - HR: Heart Rate (LOINC: 8867-4)
    - BP: Blood Pressure (LOINC: 85354-9, 8480-6, 8462-4)
    - TEMP: Temperature (LOINC: 8310-5)
    - RR: Respiratory Rate (LOINC: 9279-1)
    - SPO2: Oxygen Saturation (LOINC: 2708-6, 59408-5)
    - GCS: Glasgow Coma Score (LOINC: 9269-2)
    
    If no vital_type is specified, all vital signs will be fetched concurrently.
    """
    return await fhir_client.get_vitals(patient_id, start_date, end_date, vital_type)

@router.get("/patients/{patient_id}/vitals/latest", response_model=VitalSignsLatestResponse)
async def get_latest_vitals(
    patient_id: str,
    fhir_client: FHIRClient = Depends(get_fhir_client),
    _: dict = Depends(require_permission("read:phi"))
):
    """
    Retrieve most recent vital signs for patient (latest value for each vital sign type).
    
    Uses concurrent FHIR calls with _count=1 parameter to get the most recent values
    for all vital sign types: HR, BP, TEMP, RR, SPO2, GCS.
    """
    return await fhir_client.get_latest_vitals(patient_id)