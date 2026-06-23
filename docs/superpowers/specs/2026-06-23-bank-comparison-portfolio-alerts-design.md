# Bank Rate Chart, Portfolio Tracker & Alerts — Design Spec

**Date:** 2026-06-23
**Features:** Bank rate comparison chart · Portfolio tracker · Price & news alerts

---

## Overview

Three independent features built in sequence:

1. **Bank Rate Chart** — visualise the existing multi-bank interest rate data as a comparison bar chart
2. **Portfolio Tracker** — new dashboard tab showing a user-defined watchlist and optional holdings with P&L
3. **Alerts** — macOS desktop notifications when watchlist stocks move significantly or appear in news

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

## Feature 3 — Alerts

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

- `portfolio.json` is the single source of truth for the watchlist. Both the Portfolio tab and the Alerts module read from it — no duplication.
- Alert functions are pure and testable without mocking I/O.
- `notifier.py` wraps the OS call so tests never actually fire notifications.
- All three features are independent at the code level: bank chart touches only `interest/` and `app.py`; portfolio touches only `web/` and `app.py`; alerts touches only `alerts/` and `main.py`.

---

## Testing

- **Bank chart**: existing interest scraper tests cover the renamed class; add one test confirming `MultiRateScraper` is importable from the new path
- **Portfolio loader**: unit tests for `load_portfolio` with a tmp `portfolio.json`; test missing-file case returns empty structure
- **P&L calculation**: tested in the data_loader layer by passing known DataFrames
- **Alert checker**: unit tests with mock DataFrames and mock `NewsArticle` lists; assert correct symbols returned
- **Notifier**: mock `subprocess.run` to assert correct `osascript` command is built; no real notification fired in tests
