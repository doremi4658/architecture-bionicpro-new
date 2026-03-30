import os
import time
import jwt
from flask import Flask, request, jsonify, make_response, redirect
from flask_cors import CORS
from session_store import SessionStore
from keycloak_client import KeycloakClient
from clickhouse_driver import Client
from s3_client import S3Client

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:3000"])

session_store = SessionStore()
s3 = S3Client()

kc_client = KeycloakClient(
    server_url=os.environ.get('KEYCLOAK_URL', 'http://keycloak:8080'),
    realm=os.environ.get('KEYCLOAK_REALM', 'reports-realm'),
    client_id=os.environ.get('KEYCLOAK_CLIENT_ID', 'bionicpro-auth'),
    client_secret=os.environ.get('KEYCLOAK_CLIENT_SECRET', 'your-secret-here'),
    public_url=os.environ.get('KEYCLOAK_PUBLIC_URL')
)

AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://localhost:8000')
CDN_URL = os.environ.get('CDN_URL', 'http://localhost:8082')

@app.route('/auth/login')
def login():
    redirect_uri = AUTH_SERVICE_URL + '/auth/callback'
    auth_url = (
        f"{kc_client.auth_url}?"
        f"client_id=reports-frontend&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=openid"
    )
    print(f"Redirecting to: {auth_url}")
    return redirect(auth_url)

@app.route('/auth/callback')
def callback():
    print("Callback args:", request.args)
    code = request.args.get('code')
    if not code:
        return "Missing code", 400

    token_data = kc_client.exchange_code(code, AUTH_SERVICE_URL + '/auth/callback')
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

    user = session['user']
    client_id = user.get('preferred_username')

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        return jsonify({'error': 'Missing start_date or end_date'}), 400

    # Формируем ключ для S3
    s3_key = f"{client_id}/{start_date}_{end_date}.csv"
    cdn_url = f"{CDN_URL}/reports/{s3.bucket}/{s3_key}"

    # Проверяем, есть ли отчёт в S3
    if s3.object_exists(s3_key):
        # Отдаём ссылку на CDN
        return jsonify({'download_url': cdn_url}), 200

    # Если нет – генерируем из ClickHouse
    try:
        client = Client(host='clickhouse', port=9000)
        rows = client.execute("""
            SELECT client_name, report_date, avg_signal, total_events
            FROM report_mart
            WHERE client_id = %(client_id)s AND report_date BETWEEN %(start)s AND %(end)s
            ORDER BY report_date
        """, {'client_id': client_id, 'start': start_date, 'end': end_date})
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

    # Генерируем CSV
    output = "Client,Date,Avg Signal,Total Events\n"
    for row in rows:
        output += f"{row[0]},{row[1]},{row[2]},{row[3]}\n"

    # Сохраняем в S3
    s3.put_object(s3_key, output.encode('utf-8'))

    # Возвращаем ссылку на CDN
    return jsonify({'download_url': cdn_url}), 200

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