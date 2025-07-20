"""
Error Handling Utilities

Provides decorators and utilities for consistent error handling across
the sepsis scoring endpoints to eliminate duplicate error handling code.
"""

import logging
import functools
from typing import Any, Callable, Optional, Dict
from fastapi import HTTPException

from app.core.exceptions import FHIRException, AuthenticationException

logger = logging.getLogger(__name__)


def handle_sepsis_errors(
    operation_name: str = "operation",
    patient_id_param: str = "patient_id",
    include_patient_in_log: bool = True
):
    """
    Decorator for consistent error handling in sepsis scoring operations
    
    Args:
        operation_name: Name of the operation for logging
        patient_id_param: Name of the parameter containing patient_id
        include_patient_in_log: Whether to include patient ID in error logs
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            
            except FHIRException as e:
                patient_id = _extract_patient_id(patient_id_param, args, kwargs)
                patient_log = f" for patient [REDACTED]" if include_patient_in_log and patient_id else ""
                logger.error(f"FHIR error during {operation_name}{patient_log}: {e.detail}")
                raise HTTPException(
                    status_code=e.status_code,
                    detail=f"Failed to retrieve patient data: {e.detail}"
                )
            
            except AuthenticationException as e:
                logger.error(f"Authentication error during {operation_name}: {e.detail}")
                raise HTTPException(
                    status_code=401,
                    detail=f"Authentication failed: {e.detail}"
                )
            
            except ValueError as e:
                logger.error(f"Validation error during {operation_name}: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid request parameters: {str(e)}"
                )
            
            except Exception as e:
                patient_id = _extract_patient_id(patient_id_param, args, kwargs)
                patient_log = f" for patient [REDACTED]" if include_patient_in_log and patient_id else ""
                logger.error(f"Unexpected error during {operation_name}{patient_log}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"An unexpected error occurred during {operation_name}"
                )
        
        return wrapper
    return decorator


def handle_batch_patient_errors(operation_name: str = "batch operation"):
    """
    Decorator for handling errors in batch patient processing
    Returns errors list instead of raising exceptions for individual patients
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            
            except FHIRException as e:
                error_msg = f"FHIR error: {e.detail}"
                logger.warning(f"Failed {operation_name}: {error_msg}")
                return {"error": error_msg, "type": "FHIR_ERROR"}
            
            except AuthenticationException as e:
                error_msg = f"Authentication error: {e.detail}"
                logger.warning(f"Failed {operation_name}: {error_msg}")
                return {"error": error_msg, "type": "AUTH_ERROR"}
            
            except ValueError as e:
                error_msg = f"Validation error: {str(e)}"
                logger.warning(f"Failed {operation_name}: {error_msg}")
                return {"error": error_msg, "type": "VALIDATION_ERROR"}
            
            except Exception as e:
                error_msg = f"Calculation error: {str(e)}"
                logger.error(f"Unexpected error in {operation_name}: {error_msg}")
                return {"error": error_msg, "type": "UNEXPECTED_ERROR"}
        
        return wrapper
    return decorator


def validate_patient_id(patient_id: str, parameter_name: str = "patient_id") -> None:
    """
    Validate patient ID format and raise appropriate exceptions
    
    Args:
        patient_id: Patient ID to validate
        parameter_name: Name of the parameter for error messages
    
    Raises:
        HTTPException: If patient ID is invalid
    """
    if not patient_id or not patient_id.strip():
        raise HTTPException(
            status_code=400,
            detail=f"{parameter_name} is required and cannot be empty"
        )
    
    # Additional validation can be added here
    # e.g., format validation, length checks, etc.


def validate_batch_request(
    patient_ids: list,
    max_patients: int = 50,
    allow_duplicates: bool = False
) -> None:
    """
    Validate batch request parameters
    
    Args:
        patient_ids: List of patient IDs
        max_patients: Maximum number of patients allowed
        allow_duplicates: Whether to allow duplicate patient IDs
    
    Raises:
        HTTPException: If batch request is invalid
    """
    if len(patient_ids) > max_patients:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {max_patients} patients allowed per batch request"
        )
    
    if not allow_duplicates and len(set(patient_ids)) != len(patient_ids):
        raise HTTPException(
            status_code=400,
            detail="Duplicate patient IDs are not allowed"
        )
    
    # Validate each patient ID
    for i, patient_id in enumerate(patient_ids):
        try:
            validate_patient_id(patient_id, f"patient_ids[{i}]")
        except HTTPException as e:
            # Re-raise with more specific error message
            raise HTTPException(
                status_code=e.status_code,
                detail=f"Invalid patient ID at index {i}: {e.detail}"
            )


def validate_scoring_systems(
    requested_systems: list,
    supported_systems: list = None
) -> None:
    """
    Validate requested scoring systems
    
    Args:
        requested_systems: List of requested scoring systems
        supported_systems: List of supported systems (defaults to ["SOFA"])
    
    Raises:
        HTTPException: If unsupported systems are requested
    """
    if supported_systems is None:
        supported_systems = ["SOFA"]
    
    unsupported = [sys for sys in requested_systems if sys not in supported_systems]
    if unsupported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported scoring systems: {', '.join(unsupported)}. "
                   f"Currently supported: {', '.join(supported_systems)}"
        )


def _extract_patient_id(param_name: str, args: tuple, kwargs: dict) -> Optional[str]:
    """
    Extract patient_id from function arguments for logging
    
    Args:
        param_name: Name of the patient_id parameter
        args: Function positional arguments
        kwargs: Function keyword arguments
    
    Returns:
        Patient ID if found, None otherwise
    """
    # Try to get from kwargs first
    if param_name in kwargs:
        return kwargs[param_name]
    
    # For common patterns in our API, try to extract from args
    # This is a simple implementation - could be enhanced based on function signatures
    if args and len(args) > 0 and isinstance(args[0], str):
        return args[0]
    
    return None


class ErrorSummary:
    """Utility class for summarizing errors in batch operations"""
    
    def __init__(self):
        self.errors_by_type: Dict[str, int] = {}
        self.total_errors = 0
    
    def add_error(self, error_type: str):
        """Add an error to the summary"""
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
        self.total_errors += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error summary dictionary"""
        return {
            "total_errors": self.total_errors,
            "errors_by_type": self.errors_by_type,
            "most_common_error": max(self.errors_by_type.items(), key=lambda x: x[1])[0] if self.errors_by_type else None
        }
    
    def log_summary(self, operation_name: str = "operation"):
        """Log error summary"""
        if self.total_errors > 0:
            logger.warning(f"{operation_name} completed with {self.total_errors} errors: {self.errors_by_type}")
        else:
            logger.info(f"{operation_name} completed successfully with no errors")