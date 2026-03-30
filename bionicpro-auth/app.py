import time
import jwt
from flask import Flask, request, jsonify, make_response, redirect
from flask_cors import CORS
from session_store import SessionStore
from keycloak_client import KeycloakClient

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:3000"])

session_store = SessionStore()
kc_client = KeycloakClient(
    server_url="http://keycloak:8080",
    realm="reports-realm",
    client_id="bionicpro-auth",
    client_secret="your-secret-here"
)

@app.route('/auth/login')
def login():
    redirect_uri = request.host_url.rstrip('/') + '/auth/callback'
    auth_url = (
        f"{kc_client.auth_url}?"
        f"client_id=reports-frontend&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=openid&"
        f"code_challenge_method=S256"
    )
    return redirect(auth_url)

@app.route('/auth/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Missing code", 400

    token_data = kc_client.exchange_code(code, request.host_url.rstrip('/') + '/auth/callback')
    access_token = token_data['access_token']
    refresh_token = token_data['refresh_token']

    user_info = jwt.decode(access_token, options={"verify_signature": False})

    session_id = session_store.create(access_token, refresh_token, user_info)

    resp = make_response(redirect('http://localhost:3000'))
    resp.set_cookie('session_id', session_id, httponly=True, secure=True, samesite='Lax', max_age=30*60)
    return resp

@app.route('/api/reports', methods=['GET'])
def get_report():
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'Unauthorized'}), 401

    session = session_store.get(session_id)
    if not session:
        return jsonify({'error': 'Session expired'}), 401

    access_token = session['access_token']
    refresh_token = session['refresh_token']

    # Проверка срока действия access_token
    try:
        payload = jwt.decode(access_token, options={"verify_signature": False})
        exp = payload.get('exp')
        if exp and exp < time.time():
            raise jwt.ExpiredSignatureError
    except jwt.ExpiredSignatureError:
        # Обновляем токены
        try:
            new_tokens = kc_client.refresh_tokens(refresh_token)
            new_access = new_tokens['access_token']
            new_refresh = new_tokens.get('refresh_token', refresh_token)
            session_store.update_tokens(session_id, new_access, new_refresh)
            access_token = new_access
        except Exception:
            session_store.delete(session_id)
            return jsonify({'error': 'Session expired, please login again'}), 401

    # Ротация сессии
    new_session_id = session_store.create(access_token, refresh_token, session['user'])
    session_store.delete(session_id)

    # Имитация отчёта
    report_content = f"Отчёт для пользователя {session['user'].get('preferred_username', 'unknown')}\n\nДанные о работе протеза..."

    resp = make_response(report_content, 200)
    resp.headers['Content-Type'] = 'application/octet-stream'
    resp.headers['Content-Disposition'] = 'attachment; filename=report.txt'
    resp.set_cookie('session_id', new_session_id, httponly=True, secure=True, samesite='Lax', max_age=30*60)
    return resp

@app.route('/auth/logout', methods=['POST'])
def logout():
    session_id = request.cookies.get('session_id')
    if session_id:
        session_store.delete(session_id)
    resp = make_response(jsonify({'message': 'Logged out'}))
    resp.set_cookie('session_id', '', expires=0, httponly=True, secure=True)
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)