# Kết nối giữa các Services — Hướng dẫn chi tiết

> Tài liệu này giải thích cách từng service kết nối với nhau: cổng nào, giao thức nào, API hay thư viện gì. Dành cho người mới muốn hiểu "dây chằng" bên trong hệ thống.

---

## Bản đồ kết nối tổng thể

```
                        ┌─────────────────────────────────────────┐
                        │           BROWSER (localhost)            │
                        └──┬──────┬──────┬──────┬──────┬──────────┘
                           │:80   │:8090 │:8082 │:8088 │:9002  :8300
                           ▼      │      │      │      │       │
  ┌─────────────────┐  Portal     │      │      │      │       │
  │  nginx :80/:9002│◄────────────┘      │      │      │       │
  │  - /api/ proxy  │                    │      │      │       │
  │  - MinIO proxy  │                    │      │      │       │
  └────────┬────────┘                    │      │      │       │
           │ HTTP :8000                  │      │      │       │
           ▼                             ▼      ▼      │       ▼
  ┌─────────────────┐   ┌────────────────────────┐  ┌──────────────┐
  │   AI Platform   │   │       Keycloak          │  │   Airflow    │
  │   FastAPI :8000 │   │       OIDC :8080        │  │   FAB :8080  │
  └──┬──────┬───────┘   └────────────────────────┘  └──────┬───────┘
     │      │                                               │
     │      │ trino-python-client                           │ trino connector
     │      │ :8080                                         │ :8080
     │      ▼                                               ▼
     │  ┌─────────────────────────────────────────────────────────┐
     │  │                    Trino :8080                           │
     │  │              Distributed SQL Engine                      │
     │  └──────────────────┬────────────────────────────┬─────────┘
     │                     │ Nessie REST API             │ OPA REST API
     │                     │ :19120                      │ :8181
     │   ChromaDB HTTP      ▼                             ▼
     │   :8000  ┌──────────────────┐           ┌──────────────────┐
     └──────────►  Nessie          │           │   OPA            │
                │  Iceberg catalog │           │  Policy engine   │
                └────────┬─────────┘           └──────────────────┘
                         │ S3 API :9000
                         ▼
                ┌──────────────────┐
                │   MinIO          │
                │  Object Storage  │
                └──────────────────┘
```

---

## Chi tiết từng kết nối

### 1. Browser → Portal (nginx)

| Thuộc tính | Giá trị |
|------------|---------|
| Giao thức | HTTP |
| Cổng browser | `localhost:80` |
| Cổng MinIO proxy | `localhost:9002` |
| Loại | Nginx static file + reverse proxy |

**nginx làm gì:**
- Serve `index.html` (Portal SPA)
- `/api/*` → proxy đến AI Platform `http://ai_platform:8000`
- Port `9002` → proxy toàn bộ đến MinIO console `http://minio:9001`

```nginx
location /api/ {
    proxy_pass http://ai_platform:8000;  # giữ nguyên path /api/...
}
```

---

### 2. Portal (JS) → Keycloak — Xác thực người dùng

| Thuộc tính | Giá trị |
|------------|---------|
| Giao thức | HTTPS/HTTP + OAuth 2.0 PKCE |
| URL từ browser | `http://localhost:8090` |
| Client ID | `ai-platform` (public client) |
| Flow | Authorization Code + PKCE |

**Luồng chi tiết:**
```
1. Portal JS tạo code_verifier (random) + code_challenge (SHA-256 hash)
2. Redirect browser đến:
   GET http://localhost:8090/realms/nxn/protocol/openid-connect/auth
       ?client_id=ai-platform
       &code_challenge=<hash>
       &code_challenge_method=S256
       &redirect_uri=http://localhost/
3. Keycloak xác thực user → redirect về:
   http://localhost/?code=<auth_code>&state=<random>
4. Portal JS exchange code:
   POST http://localhost:8090/realms/nxn/protocol/openid-connect/token
        code=<auth_code>
        code_verifier=<original_verifier>
5. Nhận access_token (JWT) → lưu localStorage
```

**Token được dùng để:**
- Inject vào AI Platform iframe: `http://localhost:8300#portal-token=<jwt>`
- Hiển thị thông tin user (decode JWT payload)
- Xác định role → ẩn/hiện services trong sidebar

---

### 3. Portal (nginx) → AI Platform

| Thuộc tính | Giá trị |
|------------|---------|
| Giao thức | HTTP |
| Container-to-container | `http://ai_platform:8000` |
| Các endpoint chính | `GET /api/auth`, `POST /api/chat`, `GET /api/symbols` |

**Endpoints AI Platform:**
```
GET  /api/auth              → Trả config Keycloak (enabled, url, realm, client_id)
GET  /api/symbols           → Danh sách mã chứng khoán
POST /api/chat              → AI chat (body: {message, token})
GET  /api/report/{symbol}   → Báo cáo tự động
GET  /api/screen            → Bộ lọc cổ phiếu
GET  /api/intraday/{symbol} → Dữ liệu intraday
```

---

### 4. AI Platform → Trino

| Thuộc tính | Giá trị |
|------------|---------|
| Giao thức | Trino HTTP protocol (REST-based) |
| Host:Port | `trino:8080` |
| Thư viện | `trino-python-client` (pip: `trino`) |
| User kết nối | `ai_platform` (mapped role: analyst trong OPA) |

```python
import trino

conn = trino.dbapi.connect(
    host="trino",
    port=8080,
    user="ai_platform",
    catalog="iceberg",
    schema="mart",
)
cursor = conn.cursor()
cursor.execute("SELECT * FROM iceberg.mart.stock_prices LIMIT 100")
```

---

### 5. AI Platform → ChromaDB

| Thuộc tính | Giá trị |
|------------|---------|
| Giao thức | HTTP REST |
| Host:Port | `chromadb:8000` |
| Thư viện | `chromadb-client` |
| Mục đích | Lưu và tìm kiếm vector embeddings cho AI |

```python
import chromadb

client = chromadb.HttpClient(host="chromadb", port=8000)
collection = client.get_or_create_collection("documents")
# Tìm kiếm vector similarity
results = collection.query(query_embeddings=[...], n_results=5)
```

---

### 6. AI Platform → Ollama

| Thuộc tính | Giá trị |
|------------|---------|
| Giao thức | HTTP REST |
| Host:Port | `host.docker.internal:11434` |
| Mục đích | Chạy LLM model (llama3.2) |
| Lưu ý | Ollama chạy trên HOST machine, không phải container |

```python
# Ollama OpenAI-compatible API
POST http://host.docker.internal:11434/api/chat
{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "..."}]
}
```

`host.docker.internal` → resolve đến IP của máy host, cho phép container gọi ra ngoài.

---

### 7. Airflow → Keycloak — SSO Login

| Thuộc tính | Giá trị |
|------------|---------|
| Giao thức | OAuth 2.0 Authorization Code |
| `authorize_url` | `http://localhost:8090/...` (browser gọi) |
| `access_token_url` | `http://keycloak:8080/...` (server-to-server) |
| Client | `airflow` (confidential, secret: `airflow-secret`) |
| Thư viện | Authlib 1.x (qua Flask-AppBuilder) |

**Tại sao 2 URL khác nhau:**
- `authorize_url` dùng `localhost:8090` vì **browser** cần truy cập được
- `access_token_url` dùng `keycloak:8080` vì **Airflow container** gọi nội bộ
- Nếu dùng cùng 1 URL, sẽ bị lỗi ISS mismatch trong token validation

**Cách lấy thông tin user (NxnSecurityManager):**
```python
# Authlib 1.x tự fetch userinfo và cache vào resp['userinfo']
# → dùng trực tiếp, không cần gọi HTTP riêng
data = resp.get("userinfo")  # {'preferred_username': 'admin', 'roles': [...]}
```

---

### 8. Superset → Keycloak — SSO Login

Tương tự Airflow, cùng cơ chế. Khác biệt:
- Client: `superset` (secret: `superset-secret`)
- Config file: `superset/superset_config.py`
- Key config: `CUSTOM_SECURITY_MANAGER = NxnSecurityManager`
- Database: SQLite tại `/app/superset_home/superset.db`

---

### 9. Trino → Nessie — Iceberg Catalog

| Thuộc tính | Giá trị |
|------------|---------|
| Giao thức | HTTP REST (Nessie REST API v1) |
| Host:Port | `nessie:19120` |
| Cấu hình | `platform/trino/catalog/iceberg.properties` |

```properties
iceberg.catalog.type=nessie
iceberg.nessie-catalog.uri=http://nessie:19120/api/v1
iceberg.nessie-catalog.ref=main          # Git-like branch
```

Nessie hoạt động như một Git repo cho metadata của Iceberg tables. Trino query Nessie để biết table schema và vị trí file Parquet.

---

### 10. Trino → MinIO — Đọc/Ghi dữ liệu

| Thuộc tính | Giá trị |
|------------|---------|
| Giao thức | S3-compatible API (HTTP) |
| Host:Port | `minio:9000` |
| Credentials | `minioadmin / minioadmin` |
| Bucket | `warehouse` |
| Format file | Parquet + Snappy compression |

```properties
s3.endpoint=http://minio:9000
s3.aws-access-key=minioadmin
s3.aws-secret-key=minioadmin
s3.path-style-access=true          # dùng path style thay vì virtual-hosted
```

**Path dữ liệu thực tế:**
```
s3://warehouse/
  └── <namespace>/
        └── <table_name>/
              ├── metadata/   ← Iceberg metadata JSON
              └── data/       ← Parquet files
```

---

### 11. Trino → OPA — Kiểm tra quyền

| Thuộc tính | Giá trị |
|------------|---------|
| Giao thức | HTTP REST |
| Host:Port | `opa:8181` |
| Endpoint | `POST /v1/data/trino/allow` |
| Cấu hình | `platform/trino/config/access-control.properties` |

**Mỗi query Trino đều hỏi OPA:**
```json
POST http://opa:8181/v1/data/trino/allow
{
  "input": {
    "context": { "identity": { "user": "alice" } },
    "action": {
      "operation": "SelectFromColumns",
      "resource": {
        "table": { "catalogName": "iceberg", "schemaName": "mart", "tableName": "..." }
      }
    }
  }
}
→ { "result": true/false }
```

**Phân quyền theo role trong OPA:**
| Role | Được phép |
|------|-----------|
| admin | Tất cả operations, tất cả catalog |
| data_engineer | CRUD trên `iceberg.*` |
| analyst | SELECT trên `iceberg.mart.*` |
| ai_user | Chỉ listing operations |

---

### 12. Airflow → Trino — Chạy ETL

| Thuộc tính | Giá trị |
|------------|---------|
| Giao thức | Trino HTTP protocol |
| Connection string | `trino://admin@trino:8080/iceberg` |
| Thư viện | `trino-python-client` |
| Cấu hình | `AIRFLOW_CONN_TRINO_DEFAULT` env var |

DAG trong Airflow dùng `TrinoOperator` hoặc Python hook để chạy SQL transformation qua Trino → ghi kết quả vào Iceberg tables trên MinIO.

---

### 13. Superset → Trino — Query dữ liệu cho BI

| Thuộc tính | Giá trị |
|------------|---------|
| Giao thức | SQLAlchemy + Trino connector |
| Connection string | `trino://admin@trino:8080/iceberg` |
| Thư viện | `sqlalchemy-trino` |
| Cấu hình | Qua Superset UI → Settings → Database Connections |

---

## Thứ tự khởi động (dependencies)

```
MinIO (healthy)
    └── minio-init (tạo bucket warehouse)

Nessie (healthy)    MinIO (healthy)    OPA (healthy)
    └───────────────────┴──────────────────┘
                        │
                     Trino (started)

PostgreSQL (healthy)    Trino (started)
    └──────────────────────┘
                    │
                Airflow

Trino (started)
    └── Superset

Trino + ChromaDB + Keycloak
    └── AI Platform

AI Platform
    └── Portal
```

---

## URL nhanh cho developer

| Service | URL nội bộ (container) | URL từ host |
|---------|------------------------|-------------|
| Keycloak | `http://keycloak:8080` | `http://localhost:8090` |
| Trino | `http://trino:8080` | `http://localhost:8080` |
| MinIO S3 API | `http://minio:9000` | `http://localhost:9000` |
| MinIO Console | `http://minio:9001` | `http://localhost:9002` |
| AI Platform | `http://ai_platform:8000` | `http://localhost:8300` |
| ChromaDB | `http://chromadb:8000` | `http://localhost:8200` |
| Nessie | `http://nessie:19120` | `http://localhost:19120` |
| OPA | `http://opa:8181` | `http://localhost:8181` |
| Airflow | `http://airflow:8080` | `http://localhost:8082` |
| Superset | `http://superset:8088` | `http://localhost:8088` |

> **Lưu ý:** Container-to-container dùng tên service làm hostname (Docker DNS tự động resolve). Từ host machine dùng `localhost:<mapped_port>`.
