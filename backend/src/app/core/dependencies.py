from functools import lru_cache
from app.services.fhir_client import FHIRClient
from app.core.config import settings

@lru_cache()
def get_fhir_client() -> FHIRClient:
    return FHIRClient()