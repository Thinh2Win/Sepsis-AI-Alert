from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings(BaseSettings):
    client_id: str = os.getenv("CLIENT_ID", "")
    token_url: str = os.getenv("TOKEN_URL", "")
    private_key_path: str = os.getenv("PRIVATE_KEY_PATH", "")
    fhir_api_base: str = os.getenv("FHIR_API_BASE", "")
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # FHIR Configuration
    fhir_timeout: int = 30
    fhir_retry_attempts: int = 3
    fhir_retry_delay: float = 1.0
    
    # Authentication
    token_cache_buffer_seconds: int = 60
    jwt_expiry_minutes: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()