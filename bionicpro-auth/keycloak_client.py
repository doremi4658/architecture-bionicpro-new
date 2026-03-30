import requests

class KeycloakClient:
    def __init__(self, server_url, realm, client_id, client_secret):
        self.token_url = f"{server_url}/realms/{realm}/protocol/openid-connect/token"
        self.auth_url = f"{server_url}/realms/{realm}/protocol/openid-connect/auth"
        self.client_id = client_id
        self.client_secret = client_secret

    def exchange_code(self, code, redirect_uri):
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        resp = requests.post(self.token_url, data=data)
        resp.raise_for_status()
        return resp.json()

    def refresh_tokens(self, refresh_token):
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        resp = requests.post(self.token_url, data=data)
        resp.raise_for_status()
        return resp.json()