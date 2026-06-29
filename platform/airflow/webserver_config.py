import logging
from flask_appbuilder.security.manager import AUTH_OAUTH
from airflow.providers.fab.auth_manager.security_manager.override import (
    FabAirflowSecurityManagerOverride,
)

log = logging.getLogger(__name__)

AUTH_TYPE = AUTH_OAUTH
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = "Viewer"
AUTH_ROLES_SYNC_AT_LOGIN = True
AUTH_ROLES_MAPPING = {
    "admin":         ["Admin"],
    "data_engineer": ["Op"],
    "analyst":       ["Viewer"],
    "ai_user":       ["Viewer"],
    "viewer":        ["Viewer"],
}

OAUTH_PROVIDERS = [{
    "name": "keycloak",
    "token_key": "access_token",
    "icon": "fa-key",
    "remote_app": {
        "client_id": "airflow",
        "client_secret": "airflow-secret",
        "authorize_url": "http://localhost:8090/realms/nxn/protocol/openid-connect/auth",
        "access_token_url": "http://keycloak:8080/realms/nxn/protocol/openid-connect/token",
        "api_base_url":     "http://keycloak:8080/realms/nxn/protocol/",
        "jwks_uri":         "http://keycloak:8080/realms/nxn/protocol/openid-connect/certs",
        "client_kwargs": {"scope": "openid email profile"},
    },
}]


class NxnSecurityManager(FabAirflowSecurityManagerOverride):
    def get_oauth_user_info(self, provider, resp):
        if provider == "keycloak":
            # Authlib 1.x fetches userinfo during authorize_access_token() and stores
            # it in resp['userinfo']. Use that to avoid cross-origin token rejection.
            data = dict(resp.get("userinfo") or {})
            if not data:
                # Fallback: decode claims from id_token
                import json as _json, base64 as _b64
                id_token = resp.get("id_token", "")
                if id_token:
                    parts = id_token.split(".")
                    if len(parts) >= 2:
                        data = _json.loads(_b64.urlsafe_b64decode(parts[1] + "=="))
            log.info("Keycloak userinfo for %s: roles=%s",
                     data.get("preferred_username"), data.get("roles"))
            return {
                "username":   data.get("preferred_username", ""),
                "first_name": data.get("given_name", ""),
                "last_name":  data.get("family_name", ""),
                "email":      data.get("email", ""),
                "role_keys":  data.get("roles", []),
            }
        return super().get_oauth_user_info(provider, resp)


SECURITY_MANAGER_CLASS = NxnSecurityManager
