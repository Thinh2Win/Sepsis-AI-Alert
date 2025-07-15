from fastapi import HTTPException
from typing import Optional, Any

class FHIRException(HTTPException):
    def __init__(self, status_code: int, detail: str, code: Optional[str] = None):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code

class AuthenticationException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=401, detail=detail)

class PaginationException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)

class ValidationException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=422, detail=detail)