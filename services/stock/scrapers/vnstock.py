import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import Optional

import requests

from services.stock.model import StockPrice
from services.stock.scrapers.base import BaseStockScraper
from services.stock.scrapers._common import _OHLC_URL, _HEADERS, _to_vnd

_LISTING_URL = (
    "https://raw.githubusercontent.com/thinh-vu/vnstock/beta/data/"
    "listing_companies_enhanced-2023.csv"
)
_MAX_WORKERS = 20


def _fetch_ohlc(symbol: str, target_date: str) -> Optional[StockPrice]:
    start_dt = datetime.strptime(target_date, "%Y-%m-%d")
    end_dt = start_dt + timedelta(days=1)
    params = {
        "from": int(start_dt.timestamp()),
        "to": int(end_dt.timestamp()),
        "symbol": symbol,
        "resolution": "1D",
    }
    try:
        resp = requests.get(_OHLC_URL, params=params, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("t"):
            return None
        return StockPrice(
            date=target_date,
            symbol=symbol,
            open=_to_vnd(data["o"][0]),
            high=_to_vnd(data["h"][0]),
            low=_to_vnd(data["l"][0]),
            close=_to_vnd(data["c"][0]),
            volume=int(data["v"][0]),
        )
    except Exception:
        return None


class VnstockScraper(BaseStockScraper):
    def __init__(
        self,
        target_date: Optional[str] = None,
        max_workers: int = _MAX_WORKERS,
    ):
        self._date = target_date or (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        self._max_workers = max_workers

    def _get_symbols(self) -> list[str]:
        resp = requests.get(_LISTING_URL, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        return [row["ticker"].strip() for row in reader if row.get("ticker", "").strip()]

    def scrape(self) -> list[StockPrice]:
        symbols = self._get_symbols()
        results: list[StockPrice] = []
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {pool.submit(_fetch_ohlc, sym, self._date): sym for sym in symbols}
            for future in as_completed(futures):
                record = future.result()
                if record is not None:
                    results.append(record)
        results.sort(key=lambda r: r.symbol)
        return results
