import json
import requests
import logging
from jose import jwt, JWTError
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

logger = logging.getLogger(__name__)

# HTTP Bearer scheme for extracting tokens
security = HTTPBearer()

class Auth0JWTVerifier:
    def __init__(self):
        self.domain = settings.auth0_domain
        self.audience = settings.auth0_api_audience
        self.issuer = f"https://{self.domain}/"
        self.jwks_url = f"https://{self.domain}/.well-known/jwks.json"
        self._jwks_cache: Optional[Dict[str, Any]] = None
        
        if not self.domain or not self.audience:
            raise ValueError("AUTH0_DOMAIN and AUTH0_API_AUDIENCE must be set")

    def get_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Auth0 (with simple caching)"""
        if self._jwks_cache is None:
            try:
                response = requests.get(self.jwks_url, timeout=10)
                response.raise_for_status()
                self._jwks_cache = response.json()
            except requests.RequestException as e:
                logger.error(f"Failed to fetch JWKS: {e}")
                raise HTTPException(status_code=500, detail="Unable to verify token")
        
        return self._jwks_cache

    def get_rsa_key(self, kid: str) -> Dict[str, Any]:
        """Get RSA key from JWKS for given key ID"""
        jwks = self.get_jwks()
        
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return {
                    "kty": key.get("kty"),
                    "kid": key.get("kid"),
                    "use": key.get("use"),
                    "n": key.get("n"),
                    "e": key.get("e")
                }
        
        raise HTTPException(status_code=401, detail="Unable to find appropriate key")

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token from Auth0"""
        try:
            # Get token header to extract key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise HTTPException(status_code=401, detail="Token missing key ID")
            
            # Get RSA key for verification
            rsa_key = self.get_rsa_key(kid)
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer
            )
            
            return payload
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(status_code=401, detail="Token verification failed")

# Global verifier instance
auth0_verifier = Auth0JWTVerifier()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """FastAPI dependency to get current authenticated user"""
    token = credentials.credentials
    return auth0_verifier.verify_token(token)