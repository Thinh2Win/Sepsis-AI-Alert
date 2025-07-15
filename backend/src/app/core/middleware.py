from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
import time
import uuid

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(f"Request {request_id}: {request.method} {request.url}")
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(f"Request {request_id}: {response.status_code} - {process_time:.3f}s")
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response