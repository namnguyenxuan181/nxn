# NXN Data & AI Platform — Tổng kết

## 1. Mục tiêu

Xây dựng một nền tảng Data + AI nội bộ hoàn chỉnh, chạy hoàn toàn bằng Docker, gồm:
- Data Lake + Warehouse (Iceberg trên MinIO)
- ETL pipeline (Airflow + dbt + Trino)
- BI Dashboard (Superset)
- AI Assistant (FastAPI + Ollama + ChromaDB)
- Single Sign-On (Keycloak)
- Portal thống nhất cho tất cả services

---

## 2. Kiến trúc hệ thống

```
Browser
  │
  ▼
Portal (nginx :80)  ──── Keycloak (:8090) ─── SSO cho tất cả services
  │
  ├── [iframe]  AI Platform (:8300)   ← FastAPI + Ollama + ChromaDB
  ├── [tab mới] Superset (:8088)      ← BI Dashboard
  ├── [tab mới] Airflow (:8082)       ← ETL Orchestration
  ├── [iframe]  MinIO (:9002→9001)    ← Data Lake Storage
  ├── [iframe]  Trino (:8080)         ← Query Engine
  └── [tab mới] Keycloak (:8090)      ← Admin IAM

Data Flow:
  MinIO (S3) ←→ Nessie (Iceberg catalog) ←→ Trino (query) ←→ Superset
                                                    ↑
                                            Airflow (DAGs + dbt)

Auth Flow:
  Portal → Keycloak (PKCE) → token → AI Platform
  Airflow/Superset → Keycloak (OAuth Code) → SSO login
```

---

## 3. Stack chi tiết (11 containers)

| Service | Image | Port | Mục đích |
|---------|-------|------|----------|
| Portal | nginx:alpine | 80, 9002 | Entry point, proxy, MinIO UI |
| Keycloak | keycloak:24.0 | 8090 | IdP, SSO, OAuth2/OIDC |
| AI Platform | custom FastAPI | 8300 | Chat, Screener, Report |
| Airflow | custom (FAB) | 8082 | DAG orchestration |
| Superset | superset:3.1.3 | 8088 | BI Dashboard |
| MinIO | minio | 9000/9001 | Object storage (S3-compatible) |
| Trino | trino:438 | 8080 | Distributed SQL query engine |
| Nessie | projectnessie | 19120 | Iceberg REST catalog |
| OPA | opa:latest | 8181 | Policy-based access control |
| PostgreSQL | postgres:16 | 5432 | Airflow metadata DB |
| ChromaDB | chroma:0.5.0 | 8200 | Vector store cho AI |

---

## 4. Authentication & Authorization

### 4.1 Keycloak Realm `nxn`

**Users:**
| User | Password | Roles |
|------|----------|-------|
| admin | admin | admin, data_engineer, analyst, ai_user, viewer |
| alice | alice | analyst, ai_user |
| bob | bob | ai_user |
| carol | carol | data_engineer, analyst, ai_user |

**Clients:**
- `ai-platform` — public client, PKCE, dùng cho Portal
- `airflow` — confidential, secret: `airflow-secret`
- `superset` — confidential, secret: `superset-secret`

### 4.2 Portal Login (PKCE Flow)

```
1. Portal load → fetch /api/auth → {enabled: true}
2. Không có token → redirect Keycloak với PKCE challenge
3. User login → Keycloak redirect về /?code=...
4. Portal exchange code → access_token
5. Token lưu localStorage, inject vào AI Platform iframe
```

### 4.3 Airflow & Superset SSO (OAuth Authorization Code)

```
1. User click service → mở tab mới (vì Keycloak block iframe)
2. Airflow/Superset redirect → Keycloak login
3. Keycloak SSO → auto-login nếu đã auth ở Portal
4. Callback → NxnSecurityManager.get_oauth_user_info()
5. Lấy userinfo từ resp['userinfo'] (Authlib cache)
6. Map Keycloak roles → Airflow/Superset roles
```

**Role mapping:**
| Keycloak | Airflow | Superset |
|----------|---------|----------|
| admin | Admin | Admin |
| data_engineer | Op | Alpha |
| analyst | Viewer | Gamma |
| ai_user | Viewer | Gamma |

### 4.4 Role-based visibility trong Portal

| Service | Roles được phép |
|---------|----------------|
| AI Platform | ai_user, analyst, data_engineer, admin |
| Superset | analyst, data_engineer, admin |
| Airflow | data_engineer, admin |
| MinIO | admin |
| Trino | admin |
| Keycloak | admin |

---

## 5. Cách chạy

```bash
cd platform/
docker compose up -d          # khởi động tất cả
docker compose down           # dừng (giữ data)
docker compose down -v        # dừng + xóa data
docker compose restart <svc>  # restart 1 service
```

**Lưu ý quan trọng:** `realm-nxn.json` chỉ được import **lần đầu** khi volume `keycloak_data` chưa tồn tại. Muốn apply thay đổi realm: dùng Keycloak Admin API hoặc `docker compose down -v`.

---

## 6. Các file cấu hình quan trọng

```
platform/
├── docker-compose.yml              # toàn bộ stack
├── keycloak/
│   └── realm-nxn.json             # Keycloak realm (import lần đầu)
├── airflow/
│   ├── Dockerfile
│   ├── webserver_config.py        # OAuth config + NxnSecurityManager
│   └── dags/
├── superset/
│   └── superset_config.py         # OAuth config + NxnSecurityManager
├── portal/
│   ├── index.html                 # SPA portal (PKCE, role-based UI)
│   └── nginx.conf                 # proxy /api/ → AI Platform, MinIO
├── trino/catalog/                 # Iceberg, MinIO connector config
└── opa/policies/                  # OPA access control policies
```

---

## 7. Bugs đã fix & lessons learned

### Bug 1: Keycloak "Account not fully set up"
- **Nguyên nhân:** User có required action `UPDATE_PASSWORD` (temporary password)
- **Fix:** Phải hoàn thành qua browser, không bypass được qua API

### Bug 2: Airflow/Superset bị block trong iframe
- **Nguyên nhân:** Keycloak 24.0 set `X-Frame-Options: SAMEORIGIN`
- **Fix:** Chuyển sang mở tab mới, thêm launcher card UI

### Bug 3: `FAB_SECURITY_MANAGER_CLASS` bị ignore
- **Nguyên nhân:** Airflow đọc key `SECURITY_MANAGER_CLASS`, không phải `FAB_SECURITY_MANAGER_CLASS`
- **Fix:** Đổi key đúng trong `webserver_config.py`

### Bug 4: Userinfo 401 — iss mismatch
- **Nguyên nhân:** Token có `iss: http://localhost:8090` (browser auth), nhưng code gọi userinfo tại `http://keycloak:8080` → Keycloak reject
- **Fix:** Dùng `resp['userinfo']` mà Authlib 1.x đã tự cache trong `authorize_access_token()`, không cần gọi HTTP riêng
- **Key insight:** Authlib 1.x với OIDC scope tự fetch userinfo và lưu vào `OAuth2Token['userinfo']`

### Bug 5: Portal hiện "guest" trong incognito
- **Nguyên nhân:** nginx `proxy_pass http://ai_platform:8000/api/` với URI gây path rewriting sai → `/api/auth` bị 404 → fallback guest mode
- **Fix:** Đổi thành `proxy_pass http://ai_platform:8000` (không có URI path)

### Bug 6: Portal bị kẹt "Đang xác thực..."
- **Nguyên nhân:** Browser cache index.html cũ, safety timer không chạy
- **Fix:** Thêm `Cache-Control: no-store` vào nginx cho tất cả response

---

## 8. Hướng phát triển tiếp theo

- [ ] Thêm auth proxy (oauth2-proxy) cho MinIO và Trino
- [ ] Cấu hình dbt models và Airflow DAGs cho pipeline thực tế
- [ ] Thêm data sources (MySQL, PostgreSQL production)
- [ ] Setup Superset dashboards với dữ liệu thật
- [ ] HTTPS với self-signed cert hoặc Caddy
