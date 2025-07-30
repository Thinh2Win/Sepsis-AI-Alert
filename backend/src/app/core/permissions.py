from typing import List, Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


security = HTTPBearer()


def require_permission(required_permission: str):
    """
    FastAPI dependency factory for checking JWT permissions.
    
    Args:
        required_permission: The permission required (e.g., "read:phi")
        
    Returns:
        FastAPI dependency function that validates the permission
        
    Raises:
        HTTPException: 403 if permission is missing or JWT payload invalid
    """
    def check_permission(request: Request):
        # Get user from request state (set by Auth0 middleware)
        user_payload = getattr(request.state, 'user', None)
        
        if not user_payload:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: User authentication required"
            )
        
        # Extract permissions from JWT payload
        permissions = user_payload.get('permissions', [])
        
        # Handle case where permissions might be a string (scope format)
        if isinstance(permissions, str):
            permissions = permissions.split(' ')
        
        # Check if required permission exists
        if required_permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Missing required permission '{required_permission}'"
            )
        
        return user_payload
    
    return check_permission


def get_user_permissions(request: Request) -> List[str]:
    """
    Extract permissions from the authenticated user's JWT payload.
    
    Args:
        request: FastAPI request object
        
    Returns:
        List of permissions, empty list if none found
    """
    user_payload = getattr(request.state, 'user', None)
    if not user_payload:
        return []
    
    permissions = user_payload.get('permissions', [])
    
    # Handle both array and space-separated string formats
    if isinstance(permissions, str):
        return permissions.split(' ')
    
    return permissions if isinstance(permissions, list) else []


def get_user_id(request: Request) -> Optional[str]:
    """
    Extract user ID from the authenticated user's JWT payload.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User ID string or None if not found
    """
    user_payload = getattr(request.state, 'user', None)
    if not user_payload:
        return None
    
    return user_payload.get('sub')