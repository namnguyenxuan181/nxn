from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

from stock.scrapers._common import _OHLC_URL, _HEADERS, _to_vnd

_VN_TZ = timezone(timedelta(hours=7))
_MAX_WORKERS = 20


def is_market_open() -> bool:
    now = datetime.now(_VN_TZ)
    if now.weekday() >= 5:
        return False
    return 9 <= now.hour < 15


def _fetch_last_price(symbol: str) -> Optional[tuple]:
    now = datetime.now(_VN_TZ)
    today = now.date()
    start = datetime(today.year, today.month, today.day, 9, 0, tzinfo=_VN_TZ)
    end = datetime(today.year, today.month, today.day, 15, 30, tzinfo=_VN_TZ)
    params = {
        "symbol": symbol,
        "resolution": "1",
        "from": int(start.timestamp()),
        "to": int(end.timestamp()),
    }
    try:
        resp = requests.get(_OHLC_URL, params=params, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("c"):
            return None
        return (symbol, _to_vnd(data["c"][-1]))
    except Exception:
        return None


def fetch_intraday_prices(symbols: list) -> dict:
    results = {}
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        for result in pool.map(_fetch_last_price, symbols):
            if result is not None:
                results[result[0]] = result[1]
    return results
