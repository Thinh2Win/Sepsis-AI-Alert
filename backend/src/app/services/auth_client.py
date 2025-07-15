import time
import uuid
import requests
import logging
from jose import jwt
from typing import Optional
from app.core.config import settings
from app.core.exceptions import AuthenticationException

logger = logging.getLogger(__name__)

class EpicAuthClient:
    def __init__(self):
        self.client_id = settings.client_id
        self.token_url = settings.token_url
        self.private_key_path = settings.private_key_path
        
        if not all([self.client_id, self.token_url, self.private_key_path]):
            raise AuthenticationException("Missing required authentication configuration")
        
        try:
            with open(self.private_key_path, "r") as f:
                self.private_key = f.read()
        except Exception as e:
            raise AuthenticationException(f"Failed to load private key: {str(e)}")
        
        self._token: Optional[str] = None
        self._exp: int = 0
        self.session = requests.Session()

    def _make_assertion(self) -> str:
        now = int(time.time())
        payload = {
            'iss': self.client_id,
            'sub': self.client_id,
            'aud': self.token_url,
            'jti': str(uuid.uuid4()),
            'iat': now,
            'exp': now + (settings.jwt_expiry_minutes * 60)
        }
        headers = {"alg": "RS384", "typ": "JWT"}
        return jwt.encode(payload, self.private_key, algorithm='RS384', headers=headers)

    def _request_token(self) -> dict:
        try:
            assertion = self._make_assertion()
            data = {
                "grant_type": "client_credentials",
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": assertion,
            }
            
            response = self.session.post(
                self.token_url, 
                data=data,
                timeout=settings.fhir_timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Token request failed: {response.status_code} - {response.text}")
                raise AuthenticationException(f"Token request failed: {response.status_code}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Token request network error: {str(e)}")
            raise AuthenticationException(f"Token request network error: {str(e)}")
        except Exception as e:
            logger.error(f"Token request error: {str(e)}")
            raise AuthenticationException(f"Token request error: {str(e)}")

    def fetch_token(self) -> str:
        token_data = self._request_token()
        self._token = token_data.get('access_token')
        
        if not self._token:
            raise AuthenticationException("No access token received")
        
        expires_in = token_data.get('expires_in', 3600)
        self._exp = int(time.time()) + expires_in - settings.token_cache_buffer_seconds
        
        logger.info(f"Token fetched successfully, expires in {expires_in} seconds")
        return self._token

    def get_token(self) -> str:
        if not self._token or time.time() >= self._exp:
            self.fetch_token()
        return self._token

    def get_auth_headers(self) -> dict:
        token = self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json"
        }