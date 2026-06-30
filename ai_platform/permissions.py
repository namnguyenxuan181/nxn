"""
Stock symbol access control — per-user và per-role.

Cấu hình:
  STOCK_ACCESS  : username → danh sách mã được phép, hoặc "*" (tất cả)
  ROLE_FALLBACK : role → danh sách mã hoặc "*"  (dùng khi username không có trong STOCK_ACCESS)

Thêm user/role mới vào đây mà không cần sửa code khác.
"""

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ai_platform.auth import CurrentUser

# ── Per-user permissions ──────────────────────────────────────────────────────
STOCK_ACCESS: dict[str, list[str] | str] = {
    "admin": "*",
    "alice": ["SSI"],
    "bob":   ["FPT"],
    "carol": "*",
}

# ── Role fallback (áp dụng khi username không có trong STOCK_ACCESS) ─────────
ROLE_FALLBACK: dict[str, list[str] | str] = {
    "admin":          "*",
    "data_engineer":  "*",
    "analyst":        "*",
    "ai_user":        "*",
}


def get_allowed_symbols(user: Optional["CurrentUser"]) -> Optional[List[str]]:
    """
    Trả về:
      None           → được phép tất cả symbols
      []             → không được phép symbol nào
      ["SSI", ...]   → chỉ được phép symbols trong danh sách
    """
    if user is None:
        return []

    # username-based (ưu tiên cao nhất)
    if user.username in STOCK_ACCESS:
        perm = STOCK_ACCESS[user.username]
        return None if perm == "*" else list(perm)

    # role-based fallback (lấy role đầu tiên có trong map)
    for role in user.roles:
        if role in ROLE_FALLBACK:
            perm = ROLE_FALLBACK[role]
            return None if perm == "*" else list(perm)

    return []  # không khớp gì → từ chối


def filter_symbols(
    symbols: List[str],
    user: Optional["CurrentUser"],
) -> tuple[List[str], List[str]]:
    """
    Trả về (allowed_list, blocked_list).
    """
    allowed = get_allowed_symbols(user)
    if allowed is None:
        return symbols, []
    permitted  = [s for s in symbols if s in allowed]
    blocked    = [s for s in symbols if s not in allowed]
    return permitted, blocked
