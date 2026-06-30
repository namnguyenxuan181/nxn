"""
OPA client — query OPA cho mọi quyết định phân quyền.
Policy định nghĩa trong platform/opa/policies/data_access.rego
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from ai_platform.auth import CurrentUser

log = logging.getLogger(__name__)

OPA_URL = os.environ.get("OPA_URL", "http://opa:8181")


@dataclass
class DataPolicy:
    allow: bool = False
    restricted: bool = False           # True = symbol_whitelist áp dụng
    symbol_whitelist: List[str] = field(default_factory=list)
    masked_columns: List[str] = field(default_factory=list)
    mask_values: Dict[str, str] = field(default_factory=dict)
    accessible_tables: List[str] = field(default_factory=list)

    def filter_symbols(self, symbols: List[str]) -> Tuple[List[str], List[str]]:
        """Trả về (allowed, blocked). Nếu không bị restricted → cho phép tất cả."""
        if not self.restricted:
            return symbols, []
        allowed = [s for s in symbols if s in self.symbol_whitelist]
        blocked = [s for s in symbols if s not in self.symbol_whitelist]
        return allowed, blocked

    def mask_record(self, record: dict) -> dict:
        """Áp dụng mask lên 1 row dict."""
        if not self.masked_columns:
            return record
        result = dict(record)
        for col in self.masked_columns:
            if col in result:
                result[col] = self.mask_values.get(col, "***")
        return result

    def mask_records(self, records: List[dict]) -> List[dict]:
        return [self.mask_record(r) for r in records]


# Singleton HTTP client (connection pool)
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=3.0)
    return _client


async def check_access(
    user: Optional["CurrentUser"],
    table: str = "",
) -> DataPolicy:
    """
    Hỏi OPA: user này được làm gì với table này?
    Fail-open: nếu OPA không phản hồi → log warning và cho phép (tránh block service).
    """
    if user is None:
        return DataPolicy(allow=False)

    try:
        resp = await _get_client().post(
            f"{OPA_URL}/v1/data/ai/access",
            json={"input": {
                "user":  user.username,
                "roles": user.roles,
                "table": table,
            }},
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})

        return DataPolicy(
            allow=result.get("allow", False),
            restricted=result.get("restricted", False),
            symbol_whitelist=result.get("symbol_whitelist", []),
            masked_columns=result.get("masked_columns", []),
            mask_values=result.get("mask_values", {}),
            accessible_tables=result.get("accessible_tables", []),
        )

    except Exception as exc:
        log.warning("OPA unreachable, fail-open for user=%s: %s", user.username, exc)
        return DataPolicy(allow=True)  # fail-open
