import os

from flask_appbuilder.security.manager import AUTH_OAUTH

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "nxn-superset-secret-2026")
SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db"

# Cho phép iframe embed
WTF_CSRF_ENABLED = False
SESSION_COOKIE_SAMESITE = None
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = False

FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_NATIVE_FILTERS": True,
}

# ── Keycloak OAuth2 ──────────────────────────────────────────────────────────
# KC chạy ở keycloak:8080 (Docker internal), browser redirect về localhost:8090
_KC_INTERNAL = "http://keycloak:8080"
_KC_EXTERNAL = "http://localhost:8090"
_REALM = "nxn"

AUTH_TYPE = AUTH_OAUTH
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = "Gamma"
AUTH_ROLES_SYNC_AT_LOGIN = True

# Map Keycloak realm roles → Superset roles
AUTH_ROLES_MAPPING = {
    "admin":         ["Admin"],
    "data_engineer": ["Alpha"],
    "analyst":       ["Alpha"],
    "ai_user":       ["Gamma"],
    "viewer":        ["Gamma"],
}

OAUTH_PROVIDERS = [
    {
        "name": "keycloak",
        "icon": "fa-key",
        "token_key": "access_token",
        "remote_app": {
            "client_id": "superset",
            "client_secret": "superset-secret",
            # Browser redirect → external URL
            "authorize_url": f"{_KC_EXTERNAL}/realms/{_REALM}/protocol/openid-connect/auth",
            # Server-side calls → internal URL
            "access_token_url": f"{_KC_INTERNAL}/realms/{_REALM}/protocol/openid-connect/token",
            "api_base_url": f"{_KC_INTERNAL}/realms/{_REALM}/protocol/openid-connect",
            "jwks_uri": f"{_KC_INTERNAL}/realms/{_REALM}/protocol/openid-connect/certs",
            "userinfo_endpoint": f"{_KC_INTERNAL}/realms/{_REALM}/protocol/openid-connect/userinfo",
            "client_kwargs": {
                "scope": "openid email profile roles",
            },
        },
    }
]

# Trino connection template (thêm thủ công trong UI)
# Host: trino, Port: 8080, Database: iceberg
