from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import requests

from services.stock.scrapers._common import _OHLC_URL, _HEADERS, _to_vnd

_VN_TZ = timezone(timedelta(hours=7))
_MAX_WORKERS = 20


def is_market_open() -> bool:
    now = datetime.now(_VN_TZ)
    if now.weekday() >= 5:
        return False
    return 9 <= now.hour < 15


def _trading_window() -> tuple:
    today = datetime.now(_VN_TZ).date()
    start = datetime(today.year, today.month, today.day, 9, 0, tzinfo=_VN_TZ)
    end   = datetime(today.year, today.month, today.day, 15, 30, tzinfo=_VN_TZ)
    return int(start.timestamp()), int(end.timestamp())


def _fetch_last_price(symbol: str) -> Optional[tuple]:
    t_from, t_to = _trading_window()
    params = {"symbol": symbol, "resolution": "1", "from": t_from, "to": t_to}
    try:
        resp = requests.get(_OHLC_URL, params=params, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("c"):
            return None
        return (symbol, _to_vnd(data["c"][-1]))
    except Exception:
        return None


def fetch_intraday_ohlc(symbol: str, resolution: int = 5) -> List[Dict]:
    """Return OHLC bars for today. resolution: 1, 5, or 10 (minutes)."""
    t_from, t_to = _trading_window()
    params = {"symbol": symbol, "resolution": str(resolution), "from": t_from, "to": t_to}
    try:
        resp = requests.get(_OHLC_URL, params=params, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        closes = data.get("c") or []
        if not closes:
            return []
        timestamps = data.get("t", [])
        opens     = data.get("o", [])
        highs     = data.get("h", [])
        lows      = data.get("l", [])
        volumes   = data.get("v", [])
        return [
            {
                "t": timestamps[i],
                "o": _to_vnd(opens[i]),
                "h": _to_vnd(highs[i]),
                "l": _to_vnd(lows[i]),
                "c": _to_vnd(closes[i]),
                "v": int(volumes[i]) if volumes else 0,
            }
            for i in range(len(closes))
        ]
    except Exception:
        return []


def fetch_intraday_prices(symbols: list) -> dict:
    results = {}
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        for result in pool.map(_fetch_last_price, symbols):
            if result is not None:
                results[result[0]] = result[1]
    return results
