-- 1. Целевая таблица с ReplacingMergeTree (хранит последнее состояние)
CREATE TABLE IF NOT EXISTS report_mart_final
(
    client_id String,
    client_name String,
    email String,
    avg_signal Float32,
    total_events UInt32,
    version UInt64,          -- из Debezium: payload.source.ts_ms
    deleted UInt8            -- 1 если payload.op = 'd'
)
ENGINE = ReplacingMergeTree(version, deleted)
ORDER BY client_id;

-- 2. Таблица-поток Kafka (принимает сырые сообщения)
CREATE TABLE IF NOT EXISTS crm_kafka_stream
(
    after String,
    before String,
    op String,
    source_ts_ms UInt64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:9092',
    kafka_topic_list = 'crm.public.clients,crm.public.telemetry',
    kafka_group_name = 'clickhouse_crm_consumer',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 2;

-- 3. Материализованное представление: парсит JSON и записывает в целевую таблицу
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_crm_to_final TO report_mart_final
AS SELECT
    JSONExtractString(after, 'client_id') AS client_id,
    JSONExtractString(after, 'name') AS client_name,
    JSONExtractString(after, 'email') AS email,
    JSONExtractFloat(after, 'avg_signal') AS avg_signal,
    JSONExtractUInt(after, 'total_events') AS total_events,
    source_ts_ms AS version,
    if(op = 'd', 1, 0) AS deleted
FROM crm_kafka_stream
WHERE after != '';

-- 4. (Опционально) Представление для API, возвращающее только актуальные записи
CREATE VIEW IF NOT EXISTS report_mart_latest AS
SELECT
    client_id,
    argMax(client_name, version) AS client_name,
    argMax(email, version) AS email,
    argMax(avg_signal, version) AS avg_signal,
    argMax(total_events, version) AS total_events,
    max(version) AS last_version,
    any(deleted) AS deleted
FROM report_mart_final
GROUP BY client_id
HAVING deleted = 0;