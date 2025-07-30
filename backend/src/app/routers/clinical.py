from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import datetime
from app.models.clinical import EncounterResponse, ConditionsResponse, MedicationsResponse, FluidBalanceResponse
from app.services.fhir_client import FHIRClient
from app.core.dependencies import get_fhir_client
from app.core.permissions import require_permission

router = APIRouter()

@router.get("/patients/{patient_id}/encounter", response_model=EncounterResponse)
async def get_encounter(
    patient_id: str,
    fhir_client: FHIRClient = Depends(get_fhir_client),
    _: dict = Depends(require_permission("read:phi"))
):
    """Retrieve current patient encounter information"""
    return await fhir_client.get_encounter(patient_id)

@router.get("/patients/{patient_id}/conditions", response_model=ConditionsResponse)
async def get_conditions(
    patient_id: str,
    fhir_client: FHIRClient = Depends(get_fhir_client),
    _: dict = Depends(require_permission("read:phi"))
):
    """Retrieve patient conditions and diagnoses"""
    return await fhir_client.get_conditions(patient_id)

@router.get("/patients/{patient_id}/medications", response_model=MedicationsResponse)
async def get_medications(
    patient_id: str,
    medication_type: Optional[str] = Query(None, description="Filter medications by type: ANTIBIOTICS, VASOPRESSORS, or ALL"),
    fhir_client: FHIRClient = Depends(get_fhir_client),
    _: dict = Depends(require_permission("read:phi"))
):
    """Retrieve patient medications with optional filtering"""
    antibiotics_only = medication_type == "ANTIBIOTICS"
    vasopressors_only = medication_type == "VASOPRESSORS"
    return await fhir_client.get_medications(patient_id, antibiotics_only, vasopressors_only)

@router.get("/patients/{patient_id}/fluid-balance", response_model=FluidBalanceResponse)
async def get_fluid_balance(
    patient_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date for fluid balance"),
    end_date: Optional[datetime] = Query(None, description="End date for fluid balance"),
    fhir_client: FHIRClient = Depends(get_fhir_client),
    _: dict = Depends(require_permission("read:phi"))
):
    """Retrieve patient fluid intake and urine output"""
    return await fhir_client.get_fluid_balance(patient_id, start_date, end_date)