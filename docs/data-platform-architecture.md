# Enterprise On-Premise Data + AI Platform

## Triết lý kiến trúc

> **Trino làm universal query engine** — kết nối trực tiếp tới mọi nguồn dữ liệu qua connector, không cần tool ingestion riêng cho SQL sources.
> **dbt-trino** chạy toàn bộ transformation thông qua Trino SQL.
> **Apache Iceberg trên MinIO** làm open table format — vừa là data lake vừa là warehouse.

---

## Kiến trúc tổng thể

```
┌──────────────────────────────────────────────────────────────┐
│                       DATA SOURCES                           │
│  MySQL │ PostgreSQL │ REST API │ CSV/Excel │ Kafka │ MongoDB  │
└────────────────────────┬─────────────────────────────────────┘
                         │  Trino Connectors
┌────────────────────────▼─────────────────────────────────────┐
│                        TRINO                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐│
│  │ MySQL    │ │Postgres  │ │ Iceberg  │ │ HTTP / Kafka     ││
│  │connector │ │connector │ │connector │ │ connector        ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘│
│                                                              │
│   → Ingest: SELECT từ source, INSERT INTO Iceberg (raw)     │
│   → Query:  JOIN across nhiều nguồn realtime                │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│              STORAGE — Apache Iceberg on MinIO               │
│                                                              │
│  s3://warehouse/                                             │
│  ├── raw/          ← ingest từ Trino (schema-on-read)       │
│  │   ├── mysql.orders/                                       │
│  │   ├── api.stock_prices/                                   │
│  │   └── api.news/                                          │
│  ├── staging/      ← dbt staging models                     │
│  ├── mart/         ← dbt mart models (serving)              │
│  └── ai/           ← embeddings, vector data                │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│              ETL — dbt-trino + Airflow                       │
│                                                              │
│  Airflow DAG                                                 │
│      └── dbt run  (chạy SQL model qua Trino)                │
│              ├── models/staging/    (clean, cast, rename)   │
│              ├── models/mart/       (join, aggregate, KPI)  │
│              └── models/ai_ready/   (feature cho AI)        │
│                                                              │
│  dbt tự động:  lineage graph │ docs │ data tests           │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│              ACCESS CONTROL                                  │
│  Keycloak  — SSO, OAuth2, user/group/role                   │
│  Trino     — role-based schema/table access                 │
│  dbt       — model-level permissions via Trino              │
└────────────────────────┬─────────────────────────────────────┘
                         │
              ┌──────────┴───────────┐
┌─────────────▼──────┐  ┌───────────▼──────────────────────────┐
│    BI SERVING       │  │          AI LAYER                    │
│                     │  │                                      │
│  Superset           │  │  FastAPI  (AI Gateway)               │
│  └── connect Trino  │  │  ├── query Trino  (structured data) │
│      (SQL query     │  │  ├── query ChromaDB (RAG/semantic)   │
│       Iceberg mart) │  │  ├── Ollama  (LLM on-prem)          │
│                     │  │  └── LangChain (orchestration)       │
└─────────────────────┘  └──────────────────────────────────────┘
```

---

## Trino — Ingest + Query Engine

Trino không chỉ query — nó **ingest** bằng cách đọc source qua connector và ghi vào Iceberg:

```sql
-- Ingest từ MySQL vào Iceberg (raw layer)
CREATE TABLE iceberg.raw.mysql_orders
AS SELECT * FROM mysql.production.orders;

-- Incremental ingest (Airflow chạy hàng ngày)
INSERT INTO iceberg.raw.mysql_orders
SELECT * FROM mysql.production.orders
WHERE updated_at >= CURRENT_DATE - INTERVAL '1' DAY;

-- Federation: JOIN realtime across sources
SELECT o.*, p.close_price
FROM mysql.production.orders o
JOIN iceberg.mart.stock_prices p ON o.symbol = p.symbol
WHERE o.date = CURRENT_DATE;
```

### Trino Connectors

| Connector | Dùng cho |
|-----------|---------|
| `iceberg` | Đọc/ghi Iceberg tables trên MinIO — primary storage |
| `mysql` | Ingest từ MySQL production DB |
| `postgresql` | Ingest từ Postgres |
| `hive` | Đọc file CSV/Parquet trên MinIO |
| `http` | Gọi REST API (stock, news scrapers) |
| `mongodb` | Ingest từ MongoDB |
| `kafka` | Stream ingestion |
| `tpch` | Testing/benchmark |

---

## dbt-trino — ETL Layer

dbt chạy SQL model thông qua Trino, kết quả ghi vào Iceberg:

```
profiles.yml
  nxn_platform:
    type: trino
    host: trino
    port: 8080
    database: iceberg
    schema: mart
```

### Cấu trúc dbt models

```
models/
├── staging/                    ← 1:1 với raw tables, clean + cast
│   ├── stg_stock_prices.sql
│   ├── stg_news.sql
│   └── stg_orders.sql
│
├── mart/                       ← business logic, join, aggregate
│   ├── mart_stock_daily.sql
│   ├── mart_news_sentiment.sql
│   └── mart_portfolio_pnl.sql
│
└── ai_ready/                   ← feature tables cho AI/RAG
    ├── feat_stock_context.sql
    └── feat_news_context.sql
```

### Ví dụ model

```sql
-- models/mart/mart_stock_daily.sql
{{ config(materialized='incremental', unique_key='date || symbol') }}

SELECT
    p.date,
    p.symbol,
    p.open, p.high, p.low, p.close, p.volume,
    LAG(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_close,
    (p.close - LAG(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date))
        / LAG(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date) * 100
        AS change_pct,
    COUNT(n.id) AS news_count,
    AVG(CASE n.sentiment WHEN 'positive' THEN 1 WHEN 'negative' THEN -1 ELSE 0 END)
        AS sentiment_score
FROM {{ ref('stg_stock_prices') }} p
LEFT JOIN {{ ref('stg_news') }} n
    ON n.published_date = p.date
    AND STRPOS(n.content, p.symbol) > 0
{% if is_incremental() %}
WHERE p.date >= CURRENT_DATE - INTERVAL '3' DAY
{% endif %}
GROUP BY 1, 2, 3, 4, 5, 6, 7
```

---

## Airflow — Orchestration

```python
# dags/daily_pipeline.py
from airflow.operators.bash import BashOperator

with DAG('daily_pipeline', schedule='0 18 * * 1-5'):  # 18:00 mỗi ngày thường

    ingest = BashOperator(
        task_id='trino_ingest',
        bash_command='trino --execute "INSERT INTO iceberg.raw.stock_prices SELECT ..."',
    )

    transform = BashOperator(
        task_id='dbt_run',
        bash_command='dbt run --profiles-dir /opt/dbt --project-dir /opt/dbt/nxn',
    )

    test = BashOperator(
        task_id='dbt_test',
        bash_command='dbt test --profiles-dir /opt/dbt --project-dir /opt/dbt/nxn',
    )

    ingest >> transform >> test
```

---

## Storage — Apache Iceberg trên MinIO

Iceberg là open table format — vừa là data lake vừa là warehouse:

| Tính năng | Iceberg |
|-----------|---------|
| Schema evolution | Thêm/đổi column không break query cũ |
| Time travel | `SELECT * FROM table FOR TIMESTAMP AS OF '2026-01-01'` |
| Incremental | Chỉ đọc file mới, không scan toàn bộ |
| ACID | Insert/update/delete an toàn |
| Partition pruning | Query nhanh theo date/symbol |

```sql
-- Time travel
SELECT * FROM iceberg.mart.stock_prices
FOR TIMESTAMP AS OF TIMESTAMP '2026-06-01 00:00:00';

-- Xem lịch sử thay đổi
SELECT * FROM iceberg.mart.stock_prices$snapshots;
```

---

## Access Control

```
Keycloak
  ├── Realm: nxn-platform
  ├── Groups:
  │   ├── data-engineers  → Trino: schema CREATE, dbt run
  │   ├── analysts        → Trino: SELECT on mart.*, Superset access
  │   ├── viewers         → Superset: chỉ xem dashboard
  │   └── api-users       → FastAPI: AI endpoints
  └── SSO: Superset, Airflow, MinIO, FastAPI cùng login

Trino RBAC (file-based hoặc Ranger):
  GRANT SELECT ON iceberg.mart.* TO ROLE analyst;
  DENY  SELECT ON iceberg.raw.*  TO ROLE analyst;   -- raw data ẩn
```

---

## AI Layer tích hợp

```
User query (tiếng Việt)
        │
        ▼
FastAPI AI Gateway
        │
        ├─ 1. Phân tích intent
        │
        ├─ 2. NL → SQL (qua Ollama)
        │       └─ Trino execute → Iceberg mart
        │
        ├─ 3. Semantic search
        │       └─ ChromaDB (embeddings từ ai_ready tables)
        │
        └─ 4. Generate response
                └─ Ollama (LLM on-prem)
```

**Tính năng AI được bật bởi Trino + dbt:**
- **NL→SQL**: "doanh thu tháng trước" → Trino query mart_orders
- **RAG chất lượng cao**: dbt `ai_ready` models chuẩn hoá context cho LLM
- **Báo cáo tự động**: Airflow trigger report generation sau mỗi dbt run
- **Anomaly detection**: dbt test phát hiện bất thường → alert

---

## Deploy — Docker Compose

```yaml
services:
  # Storage
  minio:
    image: minio/minio
    command: server /data --console-address :9001
    ports: ["9000:9000", "9001:9001"]

  # Query Engine + Ingestion
  trino:
    image: trinodb/trino:latest
    ports: ["8080:8080"]
    volumes:
      - ./trino/catalog:/etc/trino/catalog   # connector configs

  # ETL
  airflow:
    image: apache/airflow:2.9.0
    ports: ["8082:8080"]

  # dbt chạy trong Airflow hoặc container riêng
  dbt:
    build: ./dbt
    command: dbt docs serve --port 8085
    ports: ["8085:8085"]

  # Auth
  keycloak:
    image: quay.io/keycloak/keycloak:24.0
    ports: ["8180:8080"]

  # BI
  superset:
    image: apache/superset:latest
    ports: ["8088:8088"]

  # AI Layer
  chromadb:
    image: chromadb/chroma:latest
    ports: ["8200:8000"]

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]

  fastapi:
    build: ./ai_platform
    ports: ["8300:8000"]

  # Reverse proxy
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
```

**Yêu cầu server:**
- RAM: 32 GB (Trino ngốn RAM nhất ~8-16 GB)
- CPU: 8 core
- Disk: 500 GB SSD
- OS: Ubuntu 22.04

---

## Roadmap demo (4 tuần)

| Tuần | Việc | Output |
|------|------|--------|
| 1 | MinIO + Iceberg + Trino catalog config | Query được Iceberg tables |
| 2 | dbt-trino project + staging/mart models + Airflow DAG | Pipeline ETL tự động |
| 3 | Keycloak RBAC + Superset dashboard | Platform bảo mật, BI live |
| 4 | ChromaDB + NL→SQL + AI gateway | AI features đầy đủ |

---

## Lý do chọn Trino + dbt

| Tiêu chí | Trino + dbt | Airbyte + Spark |
|----------|-------------|-----------------|
| Ingestion SQL sources | Connector trực tiếp, không copy data | Cần Airbyte pull về trước |
| Transformation | dbt SQL thuần, version control | PySpark, phức tạp hơn |
| Federation query | Native, join realtime cross-source | Không hỗ trợ tốt |
| Learning curve | SQL — mọi analyst đều biết | Python/Scala — cần engineer |
| Maintenance | Ít service hơn | Nhiều component hơn |
| On-prem | Hoàn toàn on-prem | Hoàn toàn on-prem |
