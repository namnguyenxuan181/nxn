import csv
import glob
import json
import os
from contextvars import ContextVar
from datetime import date, timedelta
from typing import Dict, List, Optional

from services.interest.model import InterestRate
from services.news.model import NewsArticle
from services.stock.model import StockPrice


def _data_dir() -> str:
    return os.environ.get("DATA_DIR", "./data")


def _trino_host() -> Optional[str]:
    return os.environ.get("TRINO_HOST")


def _int_or_none(val: str) -> Optional[int]:
    return int(val) if val and val.strip() else None


def _float_or_none(val: str) -> Optional[float]:
    return float(val) if val and val.strip() else None


# ── User context — set once per request in main.py ───────────────────────────
# ContextVar propagates automatically across async/sync calls in the same request.
_query_user: ContextVar[str] = ContextVar("query_user", default="ai_platform")


def set_query_user(username: str) -> None:
    """Call this at the start of each request with the authenticated username."""
    _query_user.set(username)


# ── Trino helpers ─────────────────────────────────────────────────────────────

def _trino_query(sql: str) -> list:
    import trino
    conn = trino.dbapi.connect(
        host=_trino_host(),
        port=int(os.environ.get("TRINO_PORT", 8080)),
        user=_query_user.get(),   # ← dùng username thực, OPA enforce đúng quyền
        catalog="iceberg",
        schema="mart",
        http_scheme="http",
    )
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetchall()


# ── CSV helpers ───────────────────────────────────────────────────────────────

def _read_stock_csv(path: str) -> List[StockPrice]:
    rows = []
    try:
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(StockPrice(
                    date=row["date"],
                    symbol=row["symbol"],
                    open=_int_or_none(row.get("open", "")),
                    high=_int_or_none(row.get("high", "")),
                    low=_int_or_none(row.get("low", "")),
                    close=_int_or_none(row.get("close", "")),
                    volume=_int_or_none(row.get("volume", "")),
                ))
    except (FileNotFoundError, KeyError):
        pass
    return rows


def _sorted_stock_csvs() -> List[str]:
    pattern = os.path.join(_data_dir(), "stock", "stock_*.csv")
    return sorted(glob.glob(pattern), reverse=True)


def _get_stock_by_index(index: int, symbols: List[str]) -> Dict[str, StockPrice]:
    files = _sorted_stock_csvs()
    if len(files) <= index:
        return {}
    sym_set = set(symbols)
    result = {}
    for row in _read_stock_csv(files[index]):
        if not sym_set or row.symbol in sym_set:
            result[row.symbol] = row
    return result


# ── Public API — routes to Trino when TRINO_HOST is set, else CSV ─────────────

def get_all_symbols() -> List[str]:
    if _trino_host():
        try:
            rows = _trino_query(
                "SELECT DISTINCT symbol FROM iceberg.raw.stock_prices ORDER BY symbol"
            )
            return [r[0] for r in rows]
        except Exception:
            pass
    files = _sorted_stock_csvs()
    if not files:
        return []
    return sorted({row.symbol for row in _read_stock_csv(files[0])})


def get_latest_stock(symbols: List[str]) -> Dict[str, StockPrice]:
    if _trino_host():
        try:
            sym_list = ", ".join(f"'{s}'" for s in symbols) if symbols else "''"
            rows = _trino_query(f"""
                SELECT symbol, open, high, low, close, volume, trade_date
                FROM iceberg.mart.mart_stock_daily
                WHERE trade_date = (SELECT MAX(trade_date) FROM iceberg.mart.mart_stock_daily)
                  AND symbol IN ({sym_list})
            """)
            return {
                r[0]: StockPrice(
                    date=str(r[6]), symbol=r[0],
                    open=r[1], high=r[2], low=r[3], close=r[4], volume=r[5],
                )
                for r in rows
            }
        except Exception:
            pass
    return _get_stock_by_index(0, symbols)


def get_previous_stock(symbols: List[str]) -> Dict[str, StockPrice]:
    if _trino_host():
        try:
            sym_list = ", ".join(f"'{s}'" for s in symbols) if symbols else "''"
            rows = _trino_query(f"""
                SELECT symbol, open, high, low, close, volume, trade_date
                FROM iceberg.mart.mart_stock_daily
                WHERE trade_date = (
                    SELECT MAX(trade_date) FROM iceberg.mart.mart_stock_daily
                    WHERE trade_date < (SELECT MAX(trade_date) FROM iceberg.mart.mart_stock_daily)
                )
                  AND symbol IN ({sym_list})
            """)
            return {
                r[0]: StockPrice(
                    date=str(r[6]), symbol=r[0],
                    open=r[1], high=r[2], low=r[3], close=r[4], volume=r[5],
                )
                for r in rows
            }
        except Exception:
            pass
    return _get_stock_by_index(1, symbols)


def get_stock_history(symbol: str, days: int = 10) -> List[StockPrice]:
    if _trino_host():
        try:
            rows = _trino_query(f"""
                SELECT symbol, open, high, low, close, volume, trade_date
                FROM iceberg.mart.mart_stock_daily
                WHERE symbol = '{symbol}'
                ORDER BY trade_date DESC
                LIMIT {days}
            """)
            return [
                StockPrice(
                    date=str(r[6]), symbol=r[0],
                    open=r[1], high=r[2], low=r[3], close=r[4], volume=r[5],
                )
                for r in reversed(rows)
            ]
        except Exception:
            pass
    files = _sorted_stock_csvs()[:days]
    result = []
    for path in reversed(files):
        for row in _read_stock_csv(path):
            if row.symbol == symbol:
                result.append(row)
                break
    return result


def get_recent_news(symbols: List[str], days: int = 7) -> List[NewsArticle]:
    if _trino_host():
        try:
            sym_conditions = " OR ".join(
                f"(UPPER(title) LIKE '%{s}%' OR UPPER(description) LIKE '%{s}%')"
                for s in symbols
            ) if symbols else "1=1"
            rows = _trino_query(f"""
                SELECT source, title, url, published_at, description, sentiment
                FROM iceberg.raw.news
                WHERE ({sym_conditions})
                  AND published_at >= CAST(CURRENT_DATE - INTERVAL '{days}' DAY AS VARCHAR)
                ORDER BY published_at DESC
                LIMIT 200
            """)
            return [
                NewsArticle(
                    source=r[0] or "", title=r[1] or "", url=r[2] or "",
                    published_at=r[3] or "", description=r[4] or "",
                    summary="", sentiment=r[5] or "neutral",
                )
                for r in rows
            ]
        except Exception:
            pass

    sym_set = {s.upper() for s in symbols}
    articles = []
    for i in range(days):
        d = (date.today() - timedelta(days=i)).strftime("%Y-%m-%d")
        path = os.path.join(_data_dir(), "news", f"news_{d}.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                article = NewsArticle(
                    source=item.get("source", ""),
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    published_at=item.get("published_at", ""),
                    description=item.get("description", ""),
                    summary=item.get("summary", ""),
                    sentiment=item.get("sentiment", "neutral"),
                )
                if not sym_set or any(
                    s in article.title.upper() or s in article.description.upper()
                    for s in sym_set
                ):
                    articles.append(article)
        except (json.JSONDecodeError, KeyError):
            pass
    return articles


def get_interest_rates() -> List[InterestRate]:
    if _trino_host():
        try:
            rows = _trino_query("""
                SELECT bank, channel, rate_3m, rate_6m, rate_12m, rate_24m, fetched_at
                FROM iceberg.raw.interest_rates
                WHERE fetched_at = (SELECT MAX(fetched_at) FROM iceberg.raw.interest_rates)
            """)
            return [
                InterestRate(
                    date=r[6] or "", bank=r[0] or "", channel=r[1] or "",
                    rate_1m=None, rate_3m=r[2], rate_6m=r[3],
                    rate_12m=r[4], rate_18m=None, rate_24m=r[5], rate_36m=None,
                )
                for r in rows
            ]
        except Exception:
            pass

    pattern = os.path.join(_data_dir(), "interest", "interest_*.csv")
    files = sorted(glob.glob(pattern), reverse=True)
    if not files:
        return []
    rates = []
    try:
        with open(files[0], encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rates.append(InterestRate(
                    date=row["date"],
                    bank=row["bank"],
                    channel=row["channel"],
                    rate_1m=_float_or_none(row.get("rate_1m", "")),
                    rate_3m=_float_or_none(row.get("rate_3m", "")),
                    rate_6m=_float_or_none(row.get("rate_6m", "")),
                    rate_12m=_float_or_none(row.get("rate_12m", "")),
                    rate_18m=_float_or_none(row.get("rate_18m", "")),
                    rate_24m=_float_or_none(row.get("rate_24m", "")),
                    rate_36m=_float_or_none(row.get("rate_36m", "")),
                ))
    except (FileNotFoundError, KeyError):
        pass
    return rates
