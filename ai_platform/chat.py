import re
from typing import TYPE_CHECKING, Dict, Generator, List, Optional

from ai_platform.data_access import get_all_symbols, get_recent_news, get_stock_history
from ai_platform.llm import stream_response
from ai_platform.permissions import filter_symbols

if TYPE_CHECKING:
    from ai_platform.auth import CurrentUser

_SYSTEM = (
    "Bạn là trợ lý phân tích thị trường chứng khoán Việt Nam. "
    "Trả lời bằng tiếng Việt, ngắn gọn và chính xác. "
    "Dựa vào dữ liệu được cung cấp."
)

_known_symbols: List[str] = []


def _ensure_symbols() -> List[str]:
    global _known_symbols
    if not _known_symbols:
        _known_symbols = get_all_symbols()
    return _known_symbols


def extract_symbols(message: str, known_symbols: List[str]) -> List[str]:
    upper = message.upper()
    return [s for s in known_symbols if re.search(r"\b" + re.escape(s) + r"\b", upper)]


def _build_context(symbols: List[str]) -> str:
    parts: List[str] = []
    if symbols:
        parts.append("=== Giá cổ phiếu ===")
        for sym in symbols:
            history = get_stock_history(sym, days=5)
            if history:
                lines: List[str] = []
                prev = None
                for row in history:
                    if row.close and prev:
                        pct = (row.close - prev) / prev * 100
                        lines.append(f"{row.date} close={row.close:,} ({pct:+.1f}%)")
                    elif row.close:
                        lines.append(f"{row.date} close={row.close:,}")
                    prev = row.close
                parts.append(f"{sym}: " + " | ".join(lines))
        news = get_recent_news(symbols, days=3)
    else:
        news = get_recent_news([], days=1)

    if news:
        parts.append("\n=== Tin tức liên quan ===")
        for article in news[:10]:
            parts.append(f"[{article.source} {article.published_at[:10]}] {article.title}")

    return "\n".join(parts)


def stream_chat(
    message: str,
    history: List[Dict],
    user: Optional["CurrentUser"] = None,
) -> Generator[str, None, None]:
    symbols = extract_symbols(message, _ensure_symbols())

    if symbols:
        allowed, blocked = filter_symbols(symbols, user)
        if blocked:
            who = user.username if user else "Bạn"
            yield f"⚠️ {who} không có quyền truy vấn: **{', '.join(blocked)}**.\n"
            if not allowed:
                return
            symbols = allowed

    context = _build_context(symbols)
    messages = list(history[-10:])
    user_content = (context + "\n\nCâu hỏi: " + message) if context else message
    messages.append({"role": "user", "content": user_content})
    yield from stream_response(_SYSTEM, messages)
