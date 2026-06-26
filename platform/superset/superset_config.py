import os

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

# Trino connection template (thêm thủ công trong UI)
# Host: trino, Port: 8080, Database: iceberg
