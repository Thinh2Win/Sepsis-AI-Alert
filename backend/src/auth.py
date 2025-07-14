import time
import uuid
import requests
import logging
from jose import jwt

# Configure basic logging for auth operations
logging.basicConfig(level=logging.INFO)

class EpicAuthClient:
    """
    OAuth2 JWT client for Epic FHIR sandbox using client_credentials flow.

    Handles:
      - JWT assertion creation
      - Access token fetching with error logging
      - Automatic token caching and expiration handling
    """

    def __init__(self, client_id: str, token_url: str, private_key_path: str):
        self.client_id = client_id
        self.token_url = token_url
        # Load private key for signing JWT assertions
        self.private_key = open(private_key_path, "r").read()
        self._token = None
        self._exp = 0
        # Use a session to reuse TCP connections
        self.session = requests.Session()

    def _make_assertion(self) -> str:
        """
        Build a signed JWT assertion for client_credentials grant.
        """
        now = int(time.time())
        payload = {
            'iss': self.client_id,
            'sub': self.client_id,
            'aud': self.token_url,
            'jti': str(uuid.uuid4()),
            'iat': now,
            'exp': now + 300  # valid for 5 minutes
        }
        headers = {"alg": "RS384", "typ": "JWT"}
        return jwt.encode(payload, self.private_key, algorithm='RS384', headers=headers)

    def fetch_token(self) -> str:
        """
        Request a fresh access token (with error-dump logging), cache it,
        and set its expiry 60 seconds before the real expiry.
        """
        token_data = self._request_token()
        self._token = token_data['access_token']
        self._exp = int(time.time()) + token_data.get('expires_in', 0) - 60
        return self._token

    def get_token(self) -> str:
        """
        Return a valid access token, fetching a new one if missing or expired.
        """
        if not self._token or time.time() >= self._exp:
            self.fetch_token()
        return self._token
        

    def _request_token(self) -> dict:
        """
        Internal: perform the token endpoint POST and return the JSON response.
        Logs non-200 responses to help diagnose errors.
        """
        assertion = self._make_assertion()
        data = {
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": assertion,
        }
        resp = requests.post(self.token_url, data=data)
        if resp.status_code != 200:
            logging.error(f"[Auth] token endpoint replied {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        return resp.json()
