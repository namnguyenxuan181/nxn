import json
import re
from typing import Dict, List, Optional

from ai_platform.data_access import (
    get_all_symbols,
    get_latest_stock,
    get_previous_stock,
    get_recent_news,
)
from ai_platform.llm import complete

_FILTER_PROMPT = (
    'Convert this Vietnamese stock screening query to a JSON filter spec.\n'
    'Query: "{query}"\n\n'
    "Respond with JSON only, using these optional fields:\n"
    '{{\n'
    '  "price_change_pct_min": <float or null>,\n'
    '  "price_change_pct_max": <float or null>,\n'
    '  "sentiment": <"positive"|"negative"|"neutral"|null>,\n'
    '  "min_volume": <int or null>\n'
    '}}'
)


def _parse_filter(query: str) -> Optional[Dict]:
    text = complete([{"role": "user", "content": _FILTER_PROMPT.format(query=query)}]).strip()
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def screen_stocks(query: str) -> Dict:
    spec = _parse_filter(query)
    if spec is None:
        return {"error": "Could not parse query"}

    symbols = get_all_symbols()
    if not symbols:
        return {"filter": spec, "results": []}

    latest = get_latest_stock(symbols)
    previous = get_previous_stock(symbols)
    news = get_recent_news([], days=1)

    news_sentiment: Dict[str, str] = {}
    news_headline: Dict[str, str] = {}
    for article in news:
        for sym in symbols:
            if sym in article.title.upper() or sym in article.description.upper():
                if sym not in news_sentiment:
                    news_sentiment[sym] = article.sentiment
                    news_headline[sym] = article.title

    results: List[Dict] = []
    for sym, stock in latest.items():
        if stock.close is None:
            continue

        change_pct: Optional[float] = None
        prev = previous.get(sym)
        if prev and prev.close:
            change_pct = (stock.close - prev.close) / prev.close * 100

        if spec.get("price_change_pct_min") is not None:
            if change_pct is None or change_pct < spec["price_change_pct_min"]:
                continue
        if spec.get("price_change_pct_max") is not None:
            if change_pct is None or change_pct > spec["price_change_pct_max"]:
                continue
        if spec.get("sentiment") is not None:
            if news_sentiment.get(sym) != spec["sentiment"]:
                continue
        if spec.get("min_volume") is not None:
            if stock.volume is None or stock.volume < spec["min_volume"]:
                continue

        results.append({
            "symbol": sym,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "price": stock.close,
            "news_headline": news_headline.get(sym),
        })

    results.sort(
        key=lambda r: r["change_pct"] if r["change_pct"] is not None else float("-inf"),
        reverse=True,
    )
    return {"filter": spec, "results": results[:50]}
