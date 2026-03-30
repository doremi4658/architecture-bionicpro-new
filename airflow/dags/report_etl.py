from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import psycopg2
from clickhouse_driver import Client

default_args = {
    'owner': 'bionicpro',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'report_etl',
    default_args=default_args,
    description='ETL for report mart',
    schedule_interval='0 1 * * *',
    catchup=False,
)


def extract_crm():
    conn = psycopg2.connect(
        host='keycloak_db',
        database='keycloak_db',
        user='keycloak_user',
        password='keycloak_password'
    )
    cur = conn.cursor()
    cur.execute("SELECT client_id, name, email FROM clients")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    print(f"[extract_crm] Получено {len(rows)} клиентов")
    for r in rows:
        print(f"  {r}")
    return rows


def extract_telemetry():
    conn = psycopg2.connect(
        host='keycloak_db',
        database='keycloak_db',
        user='keycloak_user',
        password='keycloak_password'
    )
    cur = conn.cursor()
    # Временно выбираем данные за последние 7 дней, чтобы старые записи тоже попали
    cur.execute("""
                SELECT client_id,
                       date_trunc('day', timestamp) as day,
               AVG(signal_strength) as avg_signal,
               COUNT(*) as total_events
                FROM telemetry
                WHERE timestamp >= now() - interval '7 days'
                GROUP BY client_id, day
                """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    print(f"[extract_telemetry] Получено {len(rows)} строк телеметрии")
    for r in rows:
        print(f"  {r}")
    return rows


def load_into_clickhouse(ti):
    crm_data = ti.xcom_pull(task_ids='extract_crm')
    telemetry = ti.xcom_pull(task_ids='extract_telemetry')

    if not telemetry:
        print("[load_to_clickhouse] Нет данных для загрузки")
        return

    client = Client(host='clickhouse', port=9000)

    # Создаём таблицу, если её нет
    client.execute("""
                   CREATE TABLE IF NOT EXISTS report_mart
                   (
                       client_id
                       String,
                       report_date
                       Date,
                       client_name
                       String,
                       avg_signal
                       Float32,
                       total_events
                       UInt32,
                       created_at
                       DateTime
                       DEFAULT
                       now
                   (
                   )
                       ) ENGINE = MergeTree
                   (
                   )
                       ORDER BY
                   (
                       client_id,
                       report_date
                   )
                   """)

    data_to_insert = []
    for tele in telemetry:
        client_id = tele[0]
        day = tele[1]
        avg_signal = tele[2]
        total_events = tele[3]
        client_name = next((c[1] for c in crm_data if c[0] == client_id), 'Unknown')

        # Преобразуем день в строку YYYY-MM-DD
        if hasattr(day, 'strftime'):
            day_str = day.strftime('%Y-%m-%d')
        else:
            day_str = str(day)

        data_to_insert.append((client_id, day_str, client_name, avg_signal, total_events))

    if data_to_insert:
        print(f"[load_to_clickhouse] Вставляю {len(data_to_insert)} строк в ClickHouse")
        client.execute(
            "INSERT INTO report_mart (client_id, report_date, client_name, avg_signal, total_events) VALUES",
            data_to_insert
        )
        print("[load_to_clickhouse] Вставка завершена")


extract_crm_task = PythonOperator(
    task_id='extract_crm',
    python_callable=extract_crm,
    dag=dag,
)

extract_telemetry_task = PythonOperator(
    task_id='extract_telemetry',
    python_callable=extract_telemetry,
    dag=dag,
)

load_task = PythonOperator(
    task_id='load_to_clickhouse',
    python_callable=load_into_clickhouse,
    provide_context=True,
    dag=dag,
)

extract_crm_task >> load_task
extract_telemetry_task >> load_task