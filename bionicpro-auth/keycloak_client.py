import httpx
from urllib.parse import urlencode

class KeycloakClient:
    def __init__(self, server_url, realm, client_id, client_secret, public_url=None):
        self.server_url = server_url.rstrip('/')
        self.public_url = (public_url or server_url).rstrip('/')
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = f"{self.server_url}/realms/{self.realm}/protocol/openid-connect/token"
        self.auth_url = f"{self.public_url}/realms/{self.realm}/protocol/openid-connect/auth"
        self.logout_url = f"{self.public_url}/realms/{self.realm}/protocol/openid-connect/logout"

    def get_authorization_url(self, redirect_uri, code_challenge, code_challenge_method='S256'):
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': 'openid email profile',
            'code_challenge': code_challenge,
            'code_challenge_method': code_challenge_method,
        }
        return f"{self.auth_url}?{urlencode(params)}"

    def exchange_code(self, code, redirect_uri, code_verifier):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'code_verifier': code_verifier,
        }
        with httpx.Client() as client:
            resp = client.post(self.token_url, data=data)
            resp.raise_for_status()
            return resp.json()

    def refresh_access_token(self, refresh_token):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        }
        with httpx.Client() as client:
            resp = client.post(self.token_url, data=data)
            if resp.status_code != 200:
                return None
            return resp.json()