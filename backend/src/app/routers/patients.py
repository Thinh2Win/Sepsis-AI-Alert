from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from app.models.patient import PatientResponse, PatientMatchRequest, PatientMatchResponse
from app.services.fhir_client import FHIRClient
from app.core.dependencies import get_fhir_client

router = APIRouter()

@router.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """Retrieve patient demographics and basic information"""
    return await fhir_client.get_patient(patient_id)

@router.post("/patients/match", response_model=PatientMatchResponse)
async def match_patient(
    match_request: PatientMatchRequest,
    fhir_client: FHIRClient = Depends(get_fhir_client)
):
    """Match patient using demographics"""
    return await fhir_client.match_patient(match_request)