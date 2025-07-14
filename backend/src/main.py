# main.py

from fastapi import FastAPI, Depends, HTTPException, Query
from typing import Optional
import requests
from pydantic import BaseModel, Field
from config import CLIENT_ID, TOKEN_URL, PRIVATE_KEY_PATH, FHIR_API_BASE
from auth import EpicAuthClient

app = FastAPI(title="FHIR Patient Ingestion API")

# instantiate your auth client once
auth_client = EpicAuthClient(CLIENT_ID, TOKEN_URL, PRIVATE_KEY_PATH)

def get_auth_headers() -> dict:
    """
    Dependency that returns a valid Authorization header.
    Raises 502 if we can’t get a token.
    """
    try:
        token = auth_client.get_token()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Auth failure: {e}")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/fhir+json"
    }

@app.get("/patients/{patient_id}")
async def read_patient(
    patient_id: str,
    headers: dict = Depends(get_auth_headers)
):
    url = f"{FHIR_API_BASE}/Patient/{patient_id}"
    resp = requests.get(url, headers=headers)
    if not resp.ok:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

class Address(BaseModel):
    line: list[str] = Field(["134 Elm Street"])
    city: str = Field("Madison")
    state: str = Field("WI")
    postalCode: str = Field("53706")

class PatientMatchRequest(BaseModel):
    given: str = Field("Theodore")
    family: str = Field("Mychart")
    birthDate: str = Field("1948-07-07")
    phone: str | None = Field("555-555-5555")
    address: Address

@app.post("/patients/match")
def match_patient(req: PatientMatchRequest):
    # 1. Grab a valid token
    token = auth_client.get_token()

    # 2. Build the Parameters resource
    patient_res = {
        "resourceType": "Patient",
        "name": [{"family": req.family, "given": [req.given]}],
        "birthDate": req.birthDate,
        "address":[{"line": [req.address.line], "city": req.address.city, "state": req.address.state, "postalCode": req.address.postalCode}]
    }
    if req.phone:
        patient_res["telecom"] = [{"system": "phone", "value": req.phone, "use": "mobile"}]
    if req.address:
        patient_res["address"] = [req.address.dict()]

    body = {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "resource", "resource": patient_res},
            {"name": "OnlyCertainMatches", "valueBoolean": True}
        ],
    }

    # 3. Call the $match endpoint
    url = f"{FHIR_API_BASE}/Patient/$match"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json",
    }
    resp = requests.post(url, headers=headers, json=body)

    # 4. Handle errors or return the result
    if not resp.ok:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()