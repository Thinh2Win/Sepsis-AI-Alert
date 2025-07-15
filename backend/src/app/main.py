from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import traceback
from typing import Dict, Any

from app.routers import patients, vitals, labs, clinical
from app.core.config import settings
from app.core.middleware import RequestLoggingMiddleware
from app.core.exceptions import FHIRException, AuthenticationException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sepsis AI Alert System",
    description="AI-powered Clinical Decision Support (CDS) tool for sepsis detection",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

@app.exception_handler(FHIRException)
async def fhir_exception_handler(request: Request, exc: FHIRException):
    logger.error(f"FHIR error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "FHIR_ERROR", "message": exc.detail, "code": exc.code}
    )

@app.exception_handler(AuthenticationException)
async def auth_exception_handler(request: Request, exc: AuthenticationException):
    logger.error(f"Authentication error: {exc.detail}")
    return JSONResponse(
        status_code=401,
        content={"error": "AUTH_ERROR", "message": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
    )

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "service": "sepsis-ai-alert"}

app.include_router(patients.router, prefix="/api/v1/sepsis-alert", tags=["patients"])
app.include_router(vitals.router, prefix="/api/v1/sepsis-alert", tags=["vitals"])
app.include_router(labs.router, prefix="/api/v1/sepsis-alert", tags=["labs"])
app.include_router(clinical.router, prefix="/api/v1/sepsis-alert", tags=["clinical"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)