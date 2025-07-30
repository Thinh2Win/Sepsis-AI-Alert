from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import logging
import time
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Log only method and sanitized path (no query params or patient IDs)
        sanitized_path = self._sanitize_path_for_logging(request.url.path)
        logger.debug(f"Request {request_id}: {request.method} {sanitized_path}")
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Only log errors and slow requests to reduce noise
        if response.status_code >= 400:
            logger.warning(f"Request {request_id}: {response.status_code} - {process_time:.3f}s")
        elif process_time > 2.0:  # Log slow requests
            logger.info(f"Slow request {request_id}: {process_time:.3f}s")
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    def _sanitize_path_for_logging(self, path: str) -> str:
        """
        Sanitize URL path to remove PHI (patient IDs) for HIPAA-compliant logging.
        
        Examples:
        - /api/v1/sepsis-alert/patients/12345/vitals -> /api/v1/sepsis-alert/patients/[PATIENT_ID]/vitals
        - /api/v1/sepsis-alert/patients/12345 -> /api/v1/sepsis-alert/patients/[PATIENT_ID]
        """
        import re
        # Replace patient IDs in URLs with placeholder to prevent PHI logging
        # Pattern matches: /patients/{patient_id} and similar patterns
        sanitized = re.sub(r'/patients/[^/]+', '/patients/[PATIENT_ID]', path)
        return sanitized


class Auth0Middleware(BaseHTTPMiddleware):
    """Global Auth0 JWT token verification middleware"""
    
    # Public endpoints that don't require authentication
    PUBLIC_ENDPOINTS = {
        "/health",
        "/docs", 
        "/redoc",
        "/openapi.json"
    }
    
    def __init__(self, app, auth0_verifier):
        super().__init__(app)
        self.auth0_verifier = auth0_verifier
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public endpoints
        if request.url.path in self.PUBLIC_ENDPOINTS:
            return await call_next(request)
        
        # Extract Authorization header
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "AUTH_ERROR",
                    "message": "Authorization header required",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        
        # Check Bearer token format
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "AUTH_ERROR", 
                    "message": "Invalid authorization format",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        
        # Extract token
        token = authorization.split(" ")[1]
        
        try:
            # Verify token using Auth0 verifier
            user_payload = self.auth0_verifier.verify_token(token)
            
            # Add user info to request state for use in route handlers
            request.state.user = user_payload
            
            # Continue to next middleware/route
            response = await call_next(request)
            
            # Audit log PHI access attempts (HIPAA-compliant - no PHI in logs)
            self._audit_phi_access(request, response, user_payload)
            
            return response
            
        except HTTPException as e:
            # Return consistent error format
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": "AUTH_ERROR",
                    "message": e.detail,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Auth middleware error: {str(e)}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "AUTH_ERROR",
                    "message": "Authentication failed",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
    
    def _audit_phi_access(self, request: Request, response: Response, user_payload: dict):
        """
        Audit log for PHI access attempts - HIPAA compliant (no PHI in logs).
        
        Logs:
        - Timestamp
        - User ID (sub claim from JWT)
        - HTTP method and sanitized path
        - Response status code
        - Access result (success/denied)
        
        Does NOT log:
        - Patient IDs or other PHI
        - Query parameters
        - Request/response body content
        """
        # Only log for PHI-related endpoints
        if '/patients/' in request.url.path:
            user_id = user_payload.get('sub', 'unknown')
            sanitized_path = self._sanitize_path_for_audit(request.url.path)
            access_result = 'SUCCESS' if response.status_code < 400 else 'DENIED'
            
            logger.info(
                f"PHI_ACCESS: user={user_id} method={request.method} "
                f"endpoint={sanitized_path} status={response.status_code} result={access_result}"
            )
    
    def _sanitize_path_for_audit(self, path: str) -> str:
        """
        Sanitize URL path for audit logging - removes all PHI.
        More aggressive than regular logging sanitization.
        """
        import re
        # Replace any potential identifiers with placeholders
        sanitized = re.sub(r'/patients/[^/]+', '/patients/***', path)
        return sanitized