import os
import time
import secrets
import hashlib
import base64
import httpx
from flask import Flask, request, jsonify, make_response, redirect, session
from flask_cors import CORS
from itsdangerous import URLSafeTimedSerializer
from session_store import SessionStore
from keycloak_client import KeycloakClient

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key')
CORS(app, supports_credentials=True, origins=["http://localhost:3000"])

session_store = SessionStore(secret_key=app.secret_key)

kc_client = KeycloakClient(
    server_url=os.environ.get('KC_URL', 'http://keycloak:8080'),
    realm=os.environ.get('REALM', 'reports-realm'),
    client_id=os.environ.get('CLIENT_ID', 'bionicpro-bff'),
    client_secret=os.environ.get('CLIENT_SECRET', 'very-secret-bff-key-12345'),
    public_url=os.environ.get('KC_URL_EXTERNAL', 'http://localhost:8080')
)

AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://localhost:8000')
FRONTEND_ORIGIN = os.environ.get('FRONTEND_ORIGIN', 'http://localhost:3000')
REPORTS_API_URL = os.environ.get('REPORTS_API_URL', 'http://reports-api:8001/reports')
SESSION_MAX_AGE = int(os.environ.get('SESSION_MAX_AGE_SECONDS', 28800))  # 8 часов

# PKCE helpers
def generate_code_verifier():
    return secrets.token_urlsafe(64)

def generate_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip('=')

@app.route('/auth/login')
def login():
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    session['pkce_verifier'] = verifier

    redirect_uri = AUTH_SERVICE_URL + '/auth/callback'
    auth_url = kc_client.get_authorization_url(
        redirect_uri=redirect_uri,
        code_challenge=challenge,
        code_challenge_method='S256'
    )
    return redirect(auth_url)

@app.route('/auth/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Missing code", 400

    verifier = session.pop('pkce_verifier', None)
    if not verifier:
        return "Missing PKCE verifier", 400

    redirect_uri = AUTH_SERVICE_URL + '/auth/callback'
    token_data = kc_client.exchange_code(
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=verifier
    )
    access_token = token_data['access_token']
    refresh_token = token_data['refresh_token']

    import jwt
    user_info = jwt.decode(access_token, options={"verify_signature": False})

    session_id = session_store.create(access_token, refresh_token, user_info)

    resp = make_response(redirect(FRONTEND_ORIGIN))
    resp.set_cookie('session_id', session_id, httponly=True, secure=False, samesite='Lax', max_age=SESSION_MAX_AGE)
    return resp

@app.route('/api/session', methods=['GET'])
def session_status():
    session_id = request.cookies.get('session_id')
    if session_id and session_store.get(session_id):
        return jsonify({'authenticated': True})
    return jsonify({'authenticated': False})

@app.route('/switch-account')
def switch_account():
    session_id = request.cookies.get('session_id')
    if session_id:
        session_store.delete(session_id)
    resp = make_response(redirect('/auth/login'))
    resp.set_cookie('session_id', '', expires=0, httponly=True, secure=False)
    return resp

@app.route('/api/reports', methods=['GET'])
def get_report():
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'Unauthorized'}), 401
    session_data = session_store.get(session_id)
    if not session_data:
        return jsonify({'error': 'Session expired'}), 401

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        return jsonify({'error': 'Missing start_date or end_date'}), 400

    # Обновляем access_token если нужно
    access_token = refresh_access_token_if_needed(session_id, session_data)
    if not access_token:
        return jsonify({'error': 'Token refresh failed'}), 401

    # Проксируем запрос к reports-api
    import asyncio
    async def call_reports_api():
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                REPORTS_API_URL,
                params={'start_date': start_date, 'end_date': end_date},
                headers={'Authorization': f'Bearer {access_token}'}
            )
            return resp.status_code, resp.json() if resp.is_success else resp.text

    status, data = asyncio.run(call_reports_api())

    if status != 200:
        return jsonify({'error': f'Reports API error: {data}'}), status

    # Ротация сессии после успешного запроса
    new_session_id = session_store.rotate(session_id, new_access_token=None, new_refresh_token=None)
    if new_session_id:
        resp = make_response(jsonify(data))
        resp.set_cookie('session_id', new_session_id, httponly=True, secure=False, samesite='Lax', max_age=SESSION_MAX_AGE)
        return resp
    else:
        return jsonify(data)

def refresh_access_token_if_needed(session_id, session_data):
    access_token = session_data['access_token']
    import jwt
    try:
        payload = jwt.decode(access_token, options={"verify_signature": False})
        exp = payload.get('exp', 0)
    except:
        return None
    # Если истекает через 30 секунд или уже истёк – обновляем
    if exp - time.time() < 30:
        refresh_token = session_data['refresh_token']
        new_tokens = kc_client.refresh_access_token(refresh_token)
        if not new_tokens:
            return None
        session_store.update(session_id, new_tokens['access_token'], new_tokens['refresh_token'])
        return new_tokens['access_token']
    return access_token

@app.route('/auth/logout', methods=['POST'])
def logout():
    session_id = request.cookies.get('session_id')
    if session_id:
        session_store.delete(session_id)
    resp = make_response(jsonify({'message': 'Logged out'}))
    resp.set_cookie('session_id', '', expires=0, httponly=True, secure=False)
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)