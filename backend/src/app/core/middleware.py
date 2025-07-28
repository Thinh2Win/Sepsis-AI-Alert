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
        
        # Log only method and path (no query params or patient IDs)
        path = request.url.path
        logger.debug(f"Request {request_id}: {request.method} {path}")
        
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


class Auth0Middleware(BaseHTTPMiddleware):
    """Global Auth0 JWT token verification middleware"""
    
    def __init__(self, app, auth0_verifier):
        super().__init__(app)
        self.auth0_verifier = auth0_verifier
    
    async def dispatch(self, request: Request, call_next):
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