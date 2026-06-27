# Phân quyền người dùng — Research & Implementation Plan

## 1. So sánh giải pháp

### Apache Ranger
Ranger là giải pháp enterprise được dùng rộng rãi trong Hadoop ecosystem (HDP, CDP).

| | |
|---|---|
| **Ưu điểm** | Fine-grained policy (column/row level), audit log có UI, plugin chính thức cho Trino, Kafka, HDFS, S3 |
| **Nhược điểm** | Rất nặng: cần Ranger Admin (~2GB RAM) + Solr (audit) + ZooKeeper. Cấu hình phức tạp. Thiết kế cho Hadoop on-prem lớn |
| **Trino support** | Plugin `ranger-trino-plugin` — enforce policy tại query time |
| **Verdict** | ❌ Overkill cho stack này. 3-4 extra containers chỉ để làm ACL |

### OPA (Open Policy Agent)
Policy-as-code engine, lightweight, REST-based.

| | |
|---|---|
| **Ưu điểm** | Rất nhẹ (~50MB), Trino 400+ có OPA plugin native, policy viết bằng Rego (declarative), không cần extra DB |
| **Nhược điểm** | Không có user management (chỉ làm authz, không làm authn), không có UI, Rego cần học |
| **Trino support** | Native — Trino gọi OPA REST API để hỏi "user X có được query table Y không?" |
| **Verdict** | ✅ Tốt cho Trino authz, nhưng cần IdP riêng cho user management |

### Keycloak
Full-featured Identity Provider (IdP) — OAuth2 / OIDC / SAML.

| | |
|---|---|
| **Ưu điểm** | SSO qua tất cả services, admin UI quản lý user/role/group, tích hợp tốt với Superset/Airflow/FastAPI qua OAuth2 |
| **Nhược điểm** | ~512MB RAM, không tự enforce table-level policy (chỉ làm authn + role assignment) |
| **Trino support** | Trino hỗ trợ OAuth2 authentication — Keycloak cấp JWT token, Trino validate và lấy username/roles từ token |
| **Verdict** | ✅ Best-in-class cho authn và user management |

---

## 2. Kiến trúc đề xuất: Keycloak + OPA

Kết hợp hai giải pháp để có full stack:

```
┌─────────────────────────────────────────────────────────────┐
│                      USER / CLIENT                          │
│  Browser / API Client / Superset / Airflow                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ Login
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    KEYCLOAK  :8090                          │
│  • User & Group management                                  │
│  • OAuth2 / OIDC provider                                   │
│  • Phát JWT token có chứa roles                             │
│  • Realm: nxn  |  Roles: admin, engineer, analyst, viewer   │
└──────┬───────────────────┬───────────────────────┬──────────┘
       │ JWT               │ OAuth2 callback        │ OIDC
       │                   │                        │
┌──────▼──────┐  ┌─────────▼────────┐  ┌───────────▼────────┐
│  FastAPI    │  │   Superset       │  │    Airflow         │
│  AI Platform│  │  OAuth2 via KC   │  │  LDAP/OAuth via KC │
│             │  │  row-level roles  │  │  RBAC roles        │
│  Validate   │  └──────────────────┘  └────────────────────┘
│  JWT, check │
│  roles      │
└──────┬──────┘
       │ username + roles
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    TRINO  :8080                             │
│  • OAuth2 authentication (validate JWT từ Keycloak)         │
│  • System Access Control → hỏi OPA                         │
└──────────────────────┬──────────────────────────────────────┘
                       │ "user=alice, role=analyst, action=SELECT, table=mart.stock_daily?"
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     OPA  :8181                             │
│  • Policy engine — trả lời allow/deny                      │
│  • Policies viết bằng Rego (version controlled)            │
│  • Ví dụ:                                                   │
│    analyst → SELECT on iceberg.mart.*                       │
│    analyst → DENY on iceberg.raw.*                          │
│    engineer → SELECT + CREATE on iceberg.raw.* + mart.*     │
│    admin → full access                                      │
└─────────────────────────────────────────────────────────────┘
```

### Roles và quyền

| Role | Trino | Superset | AI Platform | Airflow |
|------|-------|----------|-------------|---------|
| `admin` | Full access | Admin | Full | Admin |
| `data_engineer` | raw + staging + mart (r/w) | Nhìn tất cả | Full | Trigger DAGs |
| `analyst` | mart (r), staging (r) | Dashboards của mình | report + screen | — |
| `ai_user` | — | — | chat + intraday | — |
| `viewer` | mart (r) | Public dashboards | intraday only | — |

---

## 3. Implementation Plan

### Task 1 — Keycloak: thêm vào docker-compose + cấu hình realm
**Files:**
- Modify: `platform/docker-compose.yml`
- Create: `platform/keycloak/realm-nxn.json` (realm export để auto-import)

**Steps:**
1. Thêm service `keycloak` vào docker-compose (image: `quay.io/keycloak/keycloak:24.0`)
2. Mount `realm-nxn.json` để auto-import realm khi khởi động
3. Tạo `realm-nxn.json` với:
   - Realm: `nxn`
   - Client: `trino`, `superset`, `ai-platform` (confidential, client_credentials + authorization_code)
   - Roles: `admin`, `data_engineer`, `analyst`, `ai_user`, `viewer`
   - Users test: `admin/admin`, `alice/alice` (analyst), `bob/bob` (ai_user)

**Verify:** `curl http://localhost:8090/realms/nxn/.well-known/openid-configuration`

---

### Task 2 — FastAPI: JWT middleware + role-based access
**Files:**
- Modify: `ai_platform/main.py`
- Create: `ai_platform/auth.py`
- Modify: `requirements.txt` (thêm `python-jose[cryptography]`)

**Steps:**
1. Tạo `auth.py`:
   - `get_public_keys()`: fetch JWKS từ Keycloak
   - `verify_token(token)`: validate JWT, extract username + roles
   - `require_role(*roles)`: FastAPI dependency
2. Áp dụng vào các routes:
   ```python
   # Chỉ ai_user trở lên
   @app.post("/api/chat")
   def chat(req, user=Depends(require_role("ai_user", "analyst", "admin"))):

   # Chỉ analyst trở lên
   @app.get("/api/report/{symbol}")
   def report(symbol, user=Depends(require_role("analyst", "data_engineer", "admin"))):
   ```
3. Add `Authorization: Bearer <token>` support vào `static/index.html` (login form → lấy token từ Keycloak)

**Verify:** `curl -H "Authorization: Bearer <token>" http://localhost:8300/api/report/TCB`

---

### Task 3 — OPA: policy engine
**Files:**
- Create: `platform/opa/policies/trino.rego`
- Modify: `platform/docker-compose.yml`

**Steps:**
1. Thêm service `opa` vào docker-compose (image: `openpolicyagent/opa:latest`)
2. Viết `trino.rego`:
   ```rego
   package trino

   # Mặc định deny
   allow = false

   # Admin được tất cả
   allow {
     "admin" in input.context.identity.groups
   }

   # Analyst chỉ đọc mart
   allow {
     "analyst" in input.context.identity.groups
     input.action.operation in {"SelectColumns", "FilterColumns"}
     input.action.resource.schema.schemaName in {"mart"}
   }

   # Engineer đọc/ghi raw + staging + mart
   allow {
     "data_engineer" in input.context.identity.groups
     input.action.resource.schema.schemaName in {"raw", "staging", "mart"}
   }
   ```
3. Expose OPA REST API tại port 8181

**Verify:** `curl -X POST http://localhost:8181/v1/data/trino/allow -d '{"input": {...}}'`

---

### Task 4 — Trino: OAuth2 auth + OPA access control
**Files:**
- Create: `platform/trino/config/access-control.properties`
- Create: `platform/trino/config/opa.properties`
- Modify: `platform/trino/config/config.properties` (thêm OAuth2)
- Modify: `platform/docker-compose.yml` (mount thêm configs)

**Steps:**
1. Thêm `access-control.properties`:
   ```properties
   access-control.name=opa
   opa.policy.uri=http://opa:8181/v1/data/trino/allow
   ```
2. Cấu hình OAuth2 trong `config.properties`:
   ```properties
   http-server.authentication.type=OAUTH2
   http-server.authentication.oauth2.issuer=http://keycloak:8090/realms/nxn
   http-server.authentication.oauth2.client-id=trino
   http-server.authentication.oauth2.client-secret=<secret>
   ```
3. Mount configs vào Trino container

**Verify:** Query Trino với user `alice` (analyst) → chỉ xem được `iceberg.mart.*`

---

### Task 5 — Superset: OAuth2 với Keycloak
**Files:**
- Modify: `platform/superset/superset_config.py`

**Steps:**
1. Thêm OAuth2 provider config vào `superset_config.py`:
   ```python
   from flask_appbuilder.security.manager import AUTH_OAUTH
   AUTH_TYPE = AUTH_OAUTH
   OAUTH_PROVIDERS = [{
     "name": "keycloak",
     "token_key": "access_token",
     "remote_app": {
       "client_id": "superset",
       "client_secret": "...",
       "api_base_url": "http://keycloak:8090/realms/nxn/protocol/openid-connect",
       "jwks_uri": "http://keycloak:8090/realms/nxn/protocol/openid-connect/certs",
       ...
     }
   }]
   # Map Keycloak roles → Superset roles
   AUTH_ROLES_MAPPING = {
     "analyst": ["Alpha"],
     "admin": ["Admin"],
     "viewer": ["Gamma"],
   }
   ```

**Verify:** Login Superset qua Keycloak SSO

---

### Task 6 — MinIO: OIDC integration
**Files:**
- Modify: `platform/docker-compose.yml` (thêm env MinIO)

**Steps:**
1. Cấu hình MinIO với Keycloak OIDC:
   ```yaml
   MINIO_IDENTITY_OPENID_CONFIG_URL: http://keycloak:8090/realms/nxn/.well-known/openid-configuration
   MINIO_IDENTITY_OPENID_CLIENT_ID: minio
   ```
2. Tạo bucket policies trong Keycloak client scope cho MinIO

**Verify:** `mc` login bằng SSO token

---

## 4. Ports sau khi triển khai

| Service | Port | Login |
|---------|------|-------|
| Keycloak Admin UI | 8090 | admin/admin |
| OPA (REST API) | 8181 | — |
| Trino | 8080 | OAuth2 via Keycloak |
| Superset | 8088 | OAuth2 via Keycloak |
| AI Platform | 8300 | Bearer JWT |
| Airflow | 8082 | admin/admin (hoặc KC) |

## 5. Thứ tự triển khai

```
Task 1 (Keycloak) → Task 3 (OPA) → Task 4 (Trino) → Task 2 (FastAPI) → Task 5 (Superset) → Task 6 (MinIO)
```

Task 1 trước vì tất cả service khác phụ thuộc Keycloak để lấy JWT/client credentials.
Task 3 + 4 có thể làm song song.

## 6. Effort estimate

| Task | Complexity | Effort |
|------|-----------|--------|
| Task 1: Keycloak setup | Medium | ~3h |
| Task 2: FastAPI auth | Low | ~2h |
| Task 3: OPA policies | Medium | ~2h |
| Task 4: Trino OAuth2 + OPA | High | ~4h |
| Task 5: Superset OAuth2 | Low | ~1h |
| Task 6: MinIO OIDC | Low | ~1h |
| **Total** | | **~13h** |
