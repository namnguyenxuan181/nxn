import os
from datetime import datetime
from typing import Dict, List, Optional

import anthropic

from ai_platform.data_access import get_interest_rates, get_recent_news, get_stock_history

_CLIENT = anthropic.Anthropic()


def _build_context(symbol: str) -> str:
    parts: List[str] = []

    history = get_stock_history(symbol, days=10)
    if history:
        parts.append(f"=== Giá cổ phiếu {symbol} (10 ngày) ===")
        prev = None
        for row in history:
            if row.close and prev:
                pct = (row.close - prev) / prev * 100
                parts.append(
                    f"{row.date}: open={row.open:,} high={row.high:,} low={row.low:,} "
                    f"close={row.close:,} vol={row.volume:,} ({pct:+.1f}%)"
                )
            elif row.close:
                parts.append(
                    f"{row.date}: open={row.open:,} high={row.high:,} low={row.low:,} "
                    f"close={row.close:,} vol={row.volume:,}"
                )
            prev = row.close

    news = get_recent_news([symbol], days=7)
    if news:
        parts.append(f"\n=== Tin tức về {symbol} (7 ngày) ===")
        labels = {"positive": "tích cực", "negative": "tiêu cực"}
        for article in news[:15]:
            label = labels.get(article.sentiment, "trung lập")
            parts.append(f"[{article.source} {article.published_at[:10]}] [{label}] {article.title}")

    rates = get_interest_rates()
    if rates:
        parts.append("\n=== Lãi suất ngân hàng (mới nhất) ===")
        for r in rates[:4]:
            parts.append(f"{r.bank} ({r.channel}): 3m={r.rate_3m}% 6m={r.rate_6m}% 12m={r.rate_12m}%")

    return "\n".join(parts)


def generate_report(symbol: str) -> Optional[Dict]:
    history = get_stock_history(symbol, days=10)
    if not history:
        return None

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {"error": "ANTHROPIC_API_KEY not configured", "symbol": symbol}

    context = _build_context(symbol)
    prompt = (
        f"Phân tích cổ phiếu {symbol} dựa trên dữ liệu sau:\n\n{context}\n\n"
        "Viết báo cáo phân tích ngắn gồm:\n"
        "1. Xu hướng giá (10 ngày gần nhất)\n"
        "2. Tóm tắt tin tức và cảm xúc thị trường\n"
        "3. Rủi ro chính cần lưu ý\n"
        "4. Nhận định ngắn (1-2 câu)\n\n"
        "Trả lời bằng tiếng Việt, súc tích."
    )

    response = _CLIENT.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return {
        "symbol": symbol,
        "report": response.content[0].text,
        "generated_at": datetime.utcnow().isoformat(),
    }
