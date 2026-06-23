# Bank Rate Chart, Portfolio Tracker & Alerts — Design Spec

**Date:** 2026-06-23
**Features:** Bank rate comparison chart · Portfolio tracker · Intraday prices · Price & news alerts

---

## Overview

Three independent features built in sequence:

1. **Bank Rate Chart** — visualise the existing multi-bank interest rate data as a comparison bar chart
2. **Portfolio Tracker** — new dashboard tab showing a user-defined watchlist and optional holdings with P&L
3. **Intraday Prices** — fetch live last-traded price for watchlist symbols during market hours via the entrade API; portfolio tab uses intraday price when market is open, T-1 EOD otherwise
4. **Alerts** — macOS desktop notifications when watchlist stocks move significantly or appear in news

---

## Feature 1 — Bank Rate Comparison Chart

### What changes

The existing `TechcombankScraper` already collects all 8 banks from Techcombank's comparison page. No new scraping is needed.

**Files changed:**
- `interest/scrapers/techcombank.py` → renamed to `interest/scrapers/multi_rate.py`; class `TechcombankScraper` → `MultiRateScraper`. Logic is identical.
- `main.py` — update import from `TechcombankScraper` to `MultiRateScraper`
- `app.py` — add comparison chart to the 💰 Interest Rates tab
- `tests/interest/` — update test import references

**Chart spec:**
- Placed below the existing rate table in the Interest Rates tab
- Grouped bar chart: x-axis = bank name, one bar group per bank, bars represent term buckets (3m, 6m, 12m, 24m)
- A `st.radio` filter for channel: `counter` | `online`
- Uses `st.bar_chart` (Streamlit native, no extra dependencies)
- Data comes from the already-loaded DataFrame for the selected date

---

## Feature 2 — Portfolio Tracker

### Config file

`portfolio.json` at project root. Edited by hand.

```json
{
  "watchlist": ["TCB", "VCB", "HPG"],
  "holdings": [
    {"symbol": "TCB", "quantity": 1000, "buy_price": 28500},
    {"symbol": "VCB", "quantity": 500,  "buy_price": 95000}
  ]
}
```

- `watchlist` — list of stock symbols to track (must be valid symbols from stock CSVs)
- `holdings` — optional; symbols not in watchlist but in holdings are implicitly watched
- `buy_price` is in VND per share

A `portfolio.json.example` file is committed to the repo. The real `portfolio.json` is git-ignored (personal data).

### Data loading

New functions in `web/data_loader.py`:

```python
@st.cache_data(ttl=300)
def load_portfolio() -> dict:
    # returns {"watchlist": [...], "holdings": [...]}
    # returns {"watchlist": [], "holdings": []} if file absent
```

The existing `load_stock(date)` is called twice (today + yesterday) to compute change %. No new loader function needed.

### Dashboard tab — 💼 Portfolio

New fourth tab in `app.py`. Layout:

1. **Header** — shows the date of the stock data being used and a note if `portfolio.json` is missing
2. **Watchlist table** — all symbols from `watchlist` ∪ `{h["symbol"] for h in holdings}`, joined with the latest stock CSV.
   Columns: Symbol · Last Price · Change % · Volume
   Change % = `(close_today − close_yesterday) / close_yesterday * 100`
   If yesterday's data is missing, Change % shows `—`
   Rows with |change %| ≥ 3% are highlighted yellow
3. **Holdings table** — only symbols in `holdings`.
   Columns: Symbol · Qty · Buy Price · Current Price · P&L (VND) · P&L %
   P&L (VND) = `(current_price − buy_price) * quantity`
   P&L % = `(current_price − buy_price) / buy_price * 100`
   A summary row at the bottom: total invested, total current value, total P&L
4. If `portfolio.json` does not exist, show `st.info("Create portfolio.json to track your positions.")`

---

## Feature 3 — Intraday Prices

### Source

The entrade API (`https://services.entrade.com.vn/chart-api/v2/ohlcs/stock`) already supports intraday data. Passing `resolution=1` returns 1-minute OHLCV bars. The same `_to_vnd` conversion applies. Verified live: TCB returned 226 bars, last at 14:45 VN time.

### Market hours

Vietnam stock market: **Mon–Fri, 09:00–15:00 Asia/Ho_Chi_Minh (UTC+7)**. Outside these hours the market is closed and intraday data is empty or stale.

### New file — `stock/scrapers/intraday.py`

```python
def fetch_intraday_prices(symbols: list[str]) -> dict[str, int]:
    # fetches last 1-minute bar for each symbol for today's market session
    # returns {symbol: last_close_vnd} for symbols that returned data
    # uses ThreadPoolExecutor (max_workers=20), same as VnstockScraper
    # skips symbols with no data (market closed, symbol invalid)
```

Internally calls the same `_OHLC_URL` with `resolution=1`, `from=today 09:00 VN`, `to=today 15:30 VN`, and takes the last `c` value. Shares `_HEADERS` and `_to_vnd` from the existing scraper (extracted to `stock/scrapers/_common.py`).

### Market hours helper — `stock/scrapers/intraday.py`

```python
def is_market_open() -> bool:
    # returns True if current VN time is Mon–Fri between 09:00 and 15:00
```

### Data loading — `web/data_loader.py`

```python
@st.cache_data(ttl=60)
def load_intraday_prices(symbols: list[str]) -> dict[str, int]:
    # calls fetch_intraday_prices; ttl=60s so portfolio tab refreshes every minute
    # returns {} outside market hours (is_market_open() == False → skip fetch)
```

TTL is 60 seconds (not 300) so prices update frequently during market hours.

### Portfolio tab — price source logic

When rendering the Watchlist and Holdings tables:

1. Call `load_intraday_prices(all_symbols)` → `intraday`
2. For each symbol, **current price** = `intraday[symbol]` if present, else `close` from latest EOD CSV
3. **Change % basis**:
   - If intraday price used → compare against T-1 EOD close (yesterday's CSV)
   - If EOD price used → compare against T-2 EOD close (day before yesterday's CSV)
4. The price label in the UI shows `🟡 live` (intraday) or `📅 T-1` (EOD) so it's clear which is which

### Alerts — intraday integration

`check_price_alerts` accepts an optional `intraday: dict[str, int]` parameter. When provided (i.e. market is open and `main.py` fetched intraday prices), the checker uses intraday last price vs T-1 close instead of T-1 vs T-2. This means alerts fire on same-day moves during market hours.

`main.py` calls `fetch_intraday_prices` for the watchlist after the stock scrape, passes the result into `check_price_alerts`.

### What intraday does NOT do

- Does not persist intraday data to disk (no new CSV/JSON files)
- Does not replace the daily EOD scrape — `main.py` still saves T-1 OHLCV for all 800+ symbols
- Does not stream tick data; polling is sufficient (60-second cache in the dashboard)

---

## Feature 4 — Alerts

### Package structure

```
alerts/
  __init__.py
  checker.py     # pure functions, no I/O side effects
  notifier.py    # fires osascript notification
```

### `alerts/checker.py`

```python
def check_price_alerts(
    watchlist: list[str],
    df_today: pd.DataFrame,
    df_yesterday: pd.DataFrame,
    threshold_pct: float = 3.0,
) -> list[dict]:
    # returns [{"symbol": "TCB", "change_pct": 4.2}, ...]
    # only symbols where |change_pct| >= threshold_pct

def check_news_alerts(
    watchlist: list[str],
    articles: list[NewsArticle],
) -> list[dict]:
    # returns [{"symbol": "HPG", "title": "...", "url": "..."}, ...]
    # articles whose title or description contains any symbol (case-insensitive)
```

Both functions are pure (take data in, return results out). No file I/O, no notifications.

### `alerts/notifier.py`

```python
def notify(title: str, body: str) -> None:
    # fires macOS notification via osascript
    # silently no-ops if osascript is not available (non-macOS)
```

### Integration in `main.py`

After stock and news scraping, `main.py`:

1. Loads `portfolio.json`; if absent, skips alerts
2. Loads today's and yesterday's stock CSVs
3. Calls `check_price_alerts` → one notification per hit: `"TCB +4.2%"` / `"VCB -3.8%"`
4. Calls `check_news_alerts` on today's articles → one notification per symbol with matches: `"HPG: 2 articles"`

Alert threshold is hardcoded at 3.0% (not configurable via file — simple is fine).

---

## Architecture notes

- `portfolio.json` is the single source of truth for the watchlist. The Portfolio tab, Intraday loader, and Alerts module all read from it — no duplication.
- Intraday prices are on-demand only (dashboard fetch, and optionally `main.py` for alerts). No persistence.
- `stock/scrapers/_common.py` holds `_OHLC_URL`, `_HEADERS`, and `_to_vnd` so both the EOD and intraday scrapers share them without duplication.
- Alert functions are pure and testable without mocking I/O.
- `notifier.py` wraps the OS call so tests never actually fire notifications.
- Feature boundaries: bank chart → `interest/` + `app.py`; portfolio + intraday → `stock/scrapers/intraday.py` + `web/data_loader.py` + `app.py`; alerts → `alerts/` + `main.py`.

---

## Testing

- **Bank chart**: existing interest scraper tests cover the renamed class; add one test confirming `MultiRateScraper` is importable from the new path
- **Portfolio loader**: unit tests for `load_portfolio` with a tmp `portfolio.json`; test missing-file case returns empty structure
- **P&L calculation**: tested in the data_loader layer by passing known DataFrames
- **Intraday scraper**: mock `requests.get` to return a sample entrade JSON response; assert `fetch_intraday_prices` returns correct VND values; assert `is_market_open()` returns `True`/`False` based on mocked `datetime.now()`
- **Alert checker**: unit tests with mock DataFrames and mock `NewsArticle` lists; assert correct symbols returned; test intraday path (intraday dict provided) and EOD path (empty dict) separately
- **Notifier**: mock `subprocess.run` to assert correct `osascript` command is built; no real notification fired in tests
