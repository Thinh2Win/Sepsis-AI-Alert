from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback
from typing import Dict, Any
from datetime import datetime

from app.routers import patients, vitals, labs, clinical, sepsis_scoring
from app.core.config import settings
from app.core.middleware import RequestLoggingMiddleware, Auth0Middleware
from app.core.exceptions import FHIRException, AuthenticationException
from app.core.auth import auth0_verifier

# Configure logging with selective levels for HIPAA compliance
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set selective log levels to reduce noise and protect PHI
logging.getLogger('app.services.fhir_client').setLevel(logging.WARNING)  # Reduce FHIR noise
logging.getLogger('app.services.auth_client').setLevel(logging.WARNING)  # Reduce auth token noise
logging.getLogger('app.core.middleware').setLevel(logging.WARNING)       # Reduce request logging noise
logging.getLogger('app.utils.scoring_utils').setLevel(logging.WARNING)   # Protect clinical data
logging.getLogger('app.utils.qsofa_scoring').setLevel(logging.WARNING)   # Protect clinical data  
logging.getLogger('app.utils.sofa_scoring').setLevel(logging.WARNING)    # Protect clinical data
logging.getLogger('app.utils.news2_scoring').setLevel(logging.WARNING)   # Protect clinical data

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add HIPAA-compliant security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # HIPAA-compliant security headers
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Remove server header to prevent information disclosure
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


app = FastAPI(
    title="Sepsis AI Alert System",
    description="AI-powered Clinical Decision Support (CDS) tool for sepsis detection",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    # Disable debug mode for production security
    debug=settings.debug,
)

# Add HTTPS redirect middleware (only if force_https is enabled)
if settings.force_https:
    app.add_middleware(HTTPSRedirectMiddleware)

# Add trusted host middleware for additional security
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"] + [
        origin.replace("https://", "").replace("http://", "") 
        for origin in settings.allowed_origins
    ]
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Update CORS middleware to use specific origins (remove wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # No more wildcard "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Specific methods only
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],  # Specific headers
)

app.add_middleware(RequestLoggingMiddleware)

# Add Auth0 JWT verification middleware (protects all endpoints)
app.add_middleware(Auth0Middleware, auth0_verifier=auth0_verifier)

@app.exception_handler(FHIRException)
async def fhir_exception_handler(request: Request, exc: FHIRException):
    # Log detailed error server-side (for debugging)
    logger.error(f"FHIR error for request {request.url}: {exc.detail}")
    logger.error(f"Request ID: {getattr(request.state, 'request_id', 'unknown')}")
    
    # Return sanitized error client-side (prevent PHI leakage)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "FHIR_ERROR", 
            "message": "Unable to process clinical data request",
            "code": exc.code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(AuthenticationException)
async def auth_exception_handler(request: Request, exc: AuthenticationException):
    # Log detailed error server-side
    logger.error(f"Authentication error for request {request.url}: {exc.detail}")
    logger.error(f"Request ID: {getattr(request.state, 'request_id', 'unknown')}")
    
    # Return generic auth error (prevent information disclosure)
    return JSONResponse(
        status_code=401,
        content={
            "error": "AUTH_ERROR", 
            "message": "Authentication required",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced handler for HTTP exceptions including 403 permission denials"""
    
    # Log permission denials and other HTTP errors appropriately
    if exc.status_code == 403:
        # Get user info for audit (no PHI)
        user_payload = getattr(request.state, 'user', {})
        user_id = user_payload.get('sub', 'unknown')
        sanitized_path = request.url.path.replace('/patients/', '/patients/***') if '/patients/' in request.url.path else request.url.path
        
        logger.warning(f"PERMISSION_DENIED: user={user_id} endpoint={sanitized_path} status=403")
    elif exc.status_code >= 400:
        logger.warning(f"HTTP error {exc.status_code} for {request.url.path}: {exc.detail}")
    
    # Return consistent error format
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Log detailed error server-side (for debugging)
    logger.error(f"Unexpected error for request {request.url}: {str(exc)}")
    logger.error(f"Request ID: {getattr(request.state, 'request_id', 'unknown')}")
    logger.error(f"Full traceback: {traceback.format_exc()}")
    
    # Return sanitized error client-side (prevent information/PHI disclosure)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR", 
            "message": "Service temporarily unavailable",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Enhanced health check with TLS status for monitoring"""
    return {
        "status": "healthy", 
        "service": "sepsis-ai-alert",
        "version": "1.0.0",
        "tls_enabled": settings.tls_enabled,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": "production" if not settings.debug else "development"
    }

app.include_router(patients.router, prefix="/api/v1/sepsis-alert", tags=["patients"])
app.include_router(vitals.router, prefix="/api/v1/sepsis-alert", tags=["vitals"])
app.include_router(labs.router, prefix="/api/v1/sepsis-alert", tags=["labs"])
app.include_router(clinical.router, prefix="/api/v1/sepsis-alert", tags=["clinical"])
app.include_router(sepsis_scoring.router, prefix="/api/v1/sepsis-alert", tags=["sepsis-scoring"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)