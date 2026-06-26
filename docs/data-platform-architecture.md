# Enterprise On-Premise Data + AI Platform

## Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                         │
│  DB (MySQL/Postgres) │ Files (CSV/Excel) │ API │ Stream │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│              INTEGRATION & INGESTION                    │
│         Airbyte  (300+ connectors, UI quản lý)          │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│                   STORAGE LAYER                         │
│  MinIO (Data Lake, S3-compatible)                       │
│  ├── raw/        ← dữ liệu thô từ Airbyte              │
│  ├── processed/  ← sau ETL                             │
│  └── serving/    ← sẵn sàng query                      │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│              ETL / TRANSFORMATION                       │
│  Apache Airflow  (orchestration, schedule, monitor)     │
│  dbt             (SQL transform, lineage, docs)         │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│                  QUERY ENGINE                           │
│  ClickHouse  (OLAP, cực nhanh, on-prem)                │
│  DuckDB      (embedded, analytics nhẹ)                 │
│  Trino       (query across nhiều nguồn)                │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│           ACCESS CONTROL / GOVERNANCE                   │
│  Keycloak    (SSO, OAuth2, user/role management)        │
│  Apache Ranger (row/column level security)              │
└──────────────┬──────────────────────────────────────────┘
               │
       ┌───────┴────────┐
┌──────▼──────┐  ┌──────▼──────────────────────────────┐
│  BI SERVING │  │         AI LAYER                    │
│  Superset   │  │  Ollama   (LLM on-prem)             │
│  (dashboard,│  │  ChromaDB (vector store, RAG)        │
│   charts)   │  │  FastAPI  (AI API gateway)           │
└─────────────┘  │  LangChain (orchestration)           │
                 └──────────────────────────────────────┘
```

---

## Công nghệ từng tầng

| Tầng | Tool | Lý do chọn |
|------|------|------------|
| **Ingestion** | Airbyte | 300+ connector, UI kéo thả, self-hosted |
| **Storage** | MinIO | S3-compatible, on-prem, open source |
| **Orchestration** | Apache Airflow | Chuẩn industry, UI monitor pipeline |
| **Transform** | dbt | SQL-based, lineage + docs tự động |
| **Warehouse** | ClickHouse | OLAP nhanh nhất, on-prem, open source |
| **Query multi-source** | Trino | Query ClickHouse + MinIO + Postgres cùng lúc |
| **Auth / RBAC** | Keycloak | SSO, LDAP/AD integration, enterprise ready |
| **BI** | Apache Superset | Dashboard, chart, on-prem, open source |
| **LLM** | Ollama | Chạy local, data không ra ngoài |
| **Vector DB** | ChromaDB | RAG, embedding search |
| **AI Gateway** | FastAPI | Lightweight, dễ mở rộng |

---

## Deploy — Docker Compose

Toàn bộ hệ thống chạy bằng 1 lệnh trên 1 server on-prem:

```yaml
# docker-compose.yml
services:
  airbyte:      # ingestion UI — port 8000
  minio:        # data lake   — port 9000 (API), 9001 (UI)
  airflow:      # orchestration — port 8080
  clickhouse:   # warehouse   — port 8123
  superset:     # BI dashboard — port 8088
  keycloak:     # auth + RBAC — port 8180
  chromadb:     # vector store — port 8200
  ollama:       # local LLM   — port 11434
  fastapi:      # AI platform — port 8300
  nginx:        # reverse proxy / single entrypoint — port 80/443
```

```bash
docker compose up -d   # toàn bộ hệ thống lên
```

**Yêu cầu server tối thiểu cho demo:**
- RAM: 32 GB
- CPU: 8 core
- Disk: 200 GB SSD
- OS: Ubuntu 22.04

---

## Tích hợp với NXN hiện tại

| Hiện tại (NXN) | Thay thế / Tích hợp |
|----------------|---------------------|
| `stock/news/interest` scrapers | Airbyte connector hoặc giữ scraper → đẩy vào MinIO |
| CSV / JSON files | MinIO (raw) → ClickHouse (serving) |
| `main.py` ETL runner | Airflow DAG |
| FastAPI AI platform | Giữ nguyên, kết nối ClickHouse + ChromaDB |
| Ollama | Giữ nguyên |

---

## Data Flow chi tiết

```
1. INGEST
   Airbyte / Scrapers
       → MinIO/raw/  (Parquet hoặc JSON)

2. TRANSFORM
   Airflow trigger dbt
       → dbt đọc MinIO/raw/
       → clean, join, aggregate
       → ghi MinIO/processed/ + ClickHouse

3. SERVE
   ClickHouse  ← Superset (BI dashboard)
   ClickHouse  ← FastAPI  (AI context / RAG)
   ChromaDB    ← FastAPI  (vector search)
   Ollama      ← FastAPI  (LLM inference)

4. ACCESS CONTROL
   Keycloak    → JWT token cho mọi service
   Role: admin / analyst / viewer / api-user
```

---

## AI Integration

```
User query
    │
    ▼
FastAPI AI Gateway
    ├── extract intent + entities
    ├── query ClickHouse (structured data)
    ├── query ChromaDB  (semantic search / RAG)
    └── prompt Ollama / Anthropic
    │
    ▼
Response (text / JSON / chart data)
```

**Các tính năng AI:**
- Chat Q&A dựa trên dữ liệu nội bộ (RAG)
- Tự động sinh báo cáo phân tích
- NL → SQL (hỏi bằng tiếng Việt, lấy dữ liệu từ warehouse)
- Screener / filter thông minh
- Anomaly detection / cảnh báo

---

## Phân quyền (RBAC)

| Role | Quyền |
|------|-------|
| `admin` | Toàn quyền: quản lý user, pipeline, data |
| `data-engineer` | Quản lý pipeline, ETL, schema |
| `analyst` | Query ClickHouse, dùng Superset, xem báo cáo |
| `viewer` | Chỉ xem dashboard và báo cáo |
| `api-user` | Gọi FastAPI AI endpoints |

---

## Roadmap demo (4 tuần)

| Tuần | Việc | Output |
|------|------|--------|
| 1 | MinIO + ClickHouse + migrate data từ CSV | Data layer chạy được |
| 2 | Airflow DAG + Airbyte connector | Pipeline tự động |
| 3 | Keycloak auth + Superset dashboard | UI doanh nghiệp |
| 4 | ChromaDB RAG + AI gateway hoàn chỉnh | AI features đầy đủ |

---

## Lý do chọn on-prem

- **Data sovereignty** — dữ liệu nội bộ không ra ngoài
- **Compliance** — kiểm soát hoàn toàn (PDPA, ISO 27001)
- **Cost** — không trả cloud theo GB sau khi scale
- **Latency** — LLM inference local, không phụ thuộc internet
- **Customization** — tuỳ chỉnh mọi thứ theo nhu cầu doanh nghiệp
