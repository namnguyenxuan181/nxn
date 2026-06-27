"""JWT authentication via Keycloak. Auth is optional: disabled when KEYCLOAK_URL is not set."""

import os
import time
from typing import List, Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

_KC_URL = os.environ.get("KEYCLOAK_URL", "")       # e.g. http://keycloak:8080 (server-side)
_KC_PUBLIC_URL = os.environ.get("KEYCLOAK_PUBLIC_URL", "")  # e.g. http://localhost:8090 (browser)
_REALM = os.environ.get("KEYCLOAK_REALM", "nxn")
_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "ai-platform")

_bearer = HTTPBearer(auto_error=False)

# Simple JWKS cache — refreshed every 5 minutes
_jwks_cache: Optional[dict] = None
_jwks_fetched_at: float = 0
_JWKS_TTL = 300


def auth_enabled() -> bool:
    return bool(_KC_URL)


def auth_config() -> dict:
    """Config returned to the browser so it knows where Keycloak is."""
    if not auth_enabled():
        return {"enabled": False}
    public_url = _KC_PUBLIC_URL or _KC_URL
    return {
        "enabled": True,
        "keycloak_url": public_url,
        "realm": _REALM,
        "client_id": _CLIENT_ID,
    }


def _get_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    now = time.time()
    if _jwks_cache and (now - _jwks_fetched_at) < _JWKS_TTL:
        return _jwks_cache
    url = f"{_KC_URL}/realms/{_REALM}/protocol/openid-connect/certs"
    try:
        resp = httpx.get(url, timeout=5)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = now
        return _jwks_cache
    except Exception:
        if _jwks_cache:
            return _jwks_cache  # stale cache is better than nothing
        raise HTTPException(status_code=503, detail="Auth service unavailable")


def _decode_token(token: str) -> dict:
    jwks = _get_jwks()
    try:
        return jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            # Relax issuer check — issuer URL differs inside/outside Docker
            options={"verify_aud": False, "verify_iss": False},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


class CurrentUser:
    def __init__(self, username: str, roles: List[str]):
        self.username = username
        self.roles = roles

    def has_role(self, *required: str) -> bool:
        return any(r in self.roles for r in required)


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional["CurrentUser"]:
    """Return CurrentUser if auth is enabled and token is valid, else None."""
    if not auth_enabled():
        return None
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(creds.credentials)
    username = payload.get("preferred_username") or payload.get("sub", "unknown")
    roles: List[str] = payload.get("realm_access", {}).get("roles", [])
    return CurrentUser(username=username, roles=roles)


def require_role(*roles: str):
    """FastAPI dependency — requires at least one matching role."""
    async def _check(
        user: Optional[CurrentUser] = Depends(get_current_user),
    ) -> Optional[CurrentUser]:
        if not auth_enabled():
            return user
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if not user.has_role(*roles):
            raise HTTPException(
                status_code=403,
                detail=f"Required one of: {list(roles)}. Your roles: {user.roles}",
            )
        return user
    return _check
