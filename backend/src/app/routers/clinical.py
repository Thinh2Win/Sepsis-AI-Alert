from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import datetime
from app.models.clinical import EncounterResponse, ConditionsResponse, MedicationsResponse, FluidBalanceResponse
from app.services.fhir_client import FHIRClient
from app.core.dependencies import get_fhir_client

router = APIRouter()

@router.get("/patients/{patient_id}/encounter", response_model=EncounterResponse)
async def get_encounter(
    patient_id: str,
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """Retrieve current patient encounter information"""
    return await fhir_client.get_encounter(patient_id)

@router.get("/patients/{patient_id}/conditions", response_model=ConditionsResponse)
async def get_conditions(
    patient_id: str,
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """Retrieve patient conditions and diagnoses"""
    return await fhir_client.get_conditions(patient_id)

@router.get("/patients/{patient_id}/medications", response_model=MedicationsResponse)
async def get_medications(
    patient_id: str,
    antibiotics_only: bool = Query(False, description="Filter for antibiotics only"),
    vasopressors_only: bool = Query(False, description="Filter for vasopressors only"),
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """Retrieve patient medications with optional filtering"""
    return await fhir_client.get_medications(patient_id, antibiotics_only, vasopressors_only)

@router.get("/patients/{patient_id}/fluid-balance", response_model=FluidBalanceResponse)
async def get_fluid_balance(
    patient_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date for fluid balance"),
    end_date: Optional[datetime] = Query(None, description="End date for fluid balance"),
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """Retrieve patient fluid intake and urine output"""
    return await fhir_client.get_fluid_balance(patient_id, start_date, end_date)