import threading
import uuid

class SessionStore:
    def __init__(self):
        self._sessions = {}
        self._lock = threading.Lock()

    def create(self, access_token, refresh_token, user_info):
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id] = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': user_info
            }
        return session_id

    def get(self, session_id):
        with self._lock:
            return self._sessions.get(session_id)

    def update_tokens(self, session_id, access_token, refresh_token=None):
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]['access_token'] = access_token
                if refresh_token:
                    self._sessions[session_id]['refresh_token'] = refresh_token

    def delete(self, session_id):
        with self._lock:
            self._sessions.pop(session_id, None)