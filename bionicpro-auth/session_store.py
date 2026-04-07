import secrets
import time
from itsdangerous import URLSafeTimedSerializer, BadSignature

class SessionStore:
    def __init__(self, secret_key=None):
        self._store = {}  # session_id -> {access_token, refresh_token, user_info, created_at}
        self.serializer = URLSafeTimedSerializer(secret_key or 'default-secret')

    def _encrypt_token(self, token):
        return self.serializer.dumps(token)

    def _decrypt_token(self, encrypted):
        try:
            return self.serializer.loads(encrypted, max_age=86400)  # 1 day max
        except BadSignature:
            return None

    def create(self, access_token, refresh_token, user_info):
        session_id = secrets.token_urlsafe(32)
        self._store[session_id] = {
            'access_token': access_token,
            'refresh_token': self._encrypt_token(refresh_token),
            'user_info': user_info,
            'created_at': time.time()
        }
        return session_id

    def get(self, session_id):
        data = self._store.get(session_id)
        if not data:
            return None
        # Расшифровываем refresh_token при возврате
        decrypted = self._decrypt_token(data['refresh_token'])
        if not decrypted:
            return None
        return {
            'access_token': data['access_token'],
            'refresh_token': decrypted,
            'user_info': data['user_info'],
            'created_at': data['created_at']
        }

    def update(self, session_id, new_access_token, new_refresh_token):
        if session_id not in self._store:
            return False
        self._store[session_id]['access_token'] = new_access_token
        if new_refresh_token:
            self._store[session_id]['refresh_token'] = self._encrypt_token(new_refresh_token)
        return True

    def rotate(self, session_id, new_access_token=None, new_refresh_token=None):
        """Создаёт новый session_id, копирует данные, удаляет старый, возвращает новый id"""
        data = self._store.get(session_id)
        if not data:
            return None
        new_id = secrets.token_urlsafe(32)
        new_data = data.copy()
        if new_access_token:
            new_data['access_token'] = new_access_token
        if new_refresh_token:
            new_data['refresh_token'] = self._encrypt_token(new_refresh_token)
        self._store[new_id] = new_data
        del self._store[session_id]
        return new_id

    def delete(self, session_id):
        if session_id in self._store:
            del self._store[session_id]