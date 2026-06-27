from typing import Optional

import pandas as pd

from services.news.model import NewsArticle


def check_price_alerts(
    watchlist: list,
    df_today: pd.DataFrame,
    df_yesterday: pd.DataFrame,
    threshold_pct: float = 3.0,
    intraday: Optional[dict] = None,
) -> list:
    eod_today = dict(zip(df_today["symbol"], df_today["close"]))
    eod_yest = dict(zip(df_yesterday["symbol"], df_yesterday["close"]))
    results = []
    for sym in watchlist:
        current = (intraday or {}).get(sym) or eod_today.get(sym)
        baseline = eod_yest.get(sym)
        if current is None or baseline is None or baseline == 0:
            continue
        change_pct = (current - baseline) / baseline * 100
        if abs(change_pct) >= threshold_pct:
            results.append({"symbol": sym, "change_pct": round(change_pct, 2)})
    return results


def check_news_alerts(watchlist: list, articles: list) -> list:
    results = []
    for sym in watchlist:
        for article in articles:
            sym_lower = sym.lower()
            if sym_lower in article.title.lower() or sym_lower in article.description.lower():
                results.append({"symbol": sym, "title": article.title, "url": article.url})
    return results
