from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(override=True)

class Settings(BaseSettings):
    client_id: str = os.getenv("CLIENT_ID", "")
    token_url: str = os.getenv("TOKEN_URL", "")
    private_key_path: str = os.getenv("PRIVATE_KEY_PATH", "")
    fhir_api_base: str = os.getenv("FHIR_API_BASE", "")
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # FHIR Configuration
    fhir_timeout: int = 30
    fhir_retry_attempts: int = 3
    fhir_retry_delay: float = 1.0
    
    # Authentication
    token_cache_buffer_seconds: int = 60
    jwt_expiry_minutes: int = 5
    
    # Auth0 Configuration
    auth0_domain: str = os.getenv("AUTH0_DOMAIN", "")
    auth0_api_audience: str = os.getenv("AUTH0_API_AUDIENCE", "")
    
    # TLS Configuration
    tls_enabled: bool = os.getenv("TLS_ENABLED", "false").lower() == "true"
    tls_cert_file: str = os.getenv("TLS_CERT_FILE", "public_cert.pem")
    tls_key_file: str = os.getenv("TLS_KEY_FILE", "private.pem")
    tls_port: int = int(os.getenv("TLS_PORT", "8443"))
    force_https: bool = os.getenv("FORCE_HTTPS", "false").lower() == "true"
    tls_version: str = os.getenv("TLS_VERSION", "TLS")
    tls_verify_mode: str = os.getenv("TLS_VERIFY_MODE", "CERT_NONE")
    
    # Security Configuration
    secure_cookies: bool = os.getenv("SECURE_COOKIES", "false").lower() == "true"
    session_timeout_minutes: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    
    @property
    def allowed_origins(self) -> List[str]:
        """Get allowed origins from environment or return defaults"""
        origins_str = os.getenv("ALLOWED_ORIGINS")
        if origins_str:
            return [origin.strip() for origin in origins_str.split(",")]
        return ["http://localhost:3000", f"https://localhost:{self.tls_port}"]
    
    def get_tls_cert_path(self) -> Path:
        """Get absolute path to TLS certificate file"""
        if Path(self.tls_cert_file).is_absolute():
            return Path(self.tls_cert_file)
        # Go up to project root from backend/src/app/core/config.py
        return Path(__file__).parent.parent.parent.parent.parent / self.tls_cert_file
    
    def get_tls_key_path(self) -> Path:
        """Get absolute path to TLS private key file"""
        if Path(self.tls_key_file).is_absolute():
            return Path(self.tls_key_file)
        # Go up to project root from backend/src/app/core/config.py
        return Path(__file__).parent.parent.parent.parent.parent / self.tls_key_file
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

settings = Settings()