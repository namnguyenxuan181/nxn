# Bank Chart, Portfolio Tracker & Alerts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a multi-bank rate comparison chart, an intraday price fetcher, a portfolio tracker tab, and macOS desktop alerts for price moves and news mentions.

**Architecture:** Six sequential tasks. Tasks 1–2 are data-layer changes (rename scraper, add intraday module). Tasks 3–4 are the portfolio feature (config loader + dashboard tab). Tasks 5–6 are the alerts package wired into `main.py`. All new logic is pure-function-first so it is testable without mocking Streamlit or the OS.

**Tech Stack:** Python 3.9, Streamlit, pandas, requests, ThreadPoolExecutor, osascript (macOS)

## Global Constraints

- Python 3.9 — no `dict | None` union syntax; use `Optional[dict]` from `typing`
- All new files follow the existing package pattern: domain folder + `__init__.py`
- Test files mirror source paths: `stock/scrapers/intraday.py` → `tests/stock/scrapers/test_intraday.py`
- Run the full suite with `source venv/bin/activate && python -m pytest tests/ -q` — must stay at 80+ passing, 0 failures
- `portfolio.json` is git-ignored (personal data); `portfolio.json.example` is committed
- Streamlit cache: `@st.cache_data(ttl=300)` for portfolio loader, `@st.cache_data(ttl=60)` for intraday prices
- Entrade API: `https://services.entrade.com.vn/chart-api/v2/ohlcs/stock`; multiply raw price × 1000 for VND
- Market hours: Mon–Fri 09:00–15:00 Asia/Ho_Chi_Minh (UTC+7)

---

## File Map

| Action | Path |
|--------|------|
| Rename | `interest/scrapers/techcombank.py` → `interest/scrapers/multi_rate.py` |
| Update | `main.py` (import rename + alerts wiring) |
| Update | `tests/interest/scrapers/test_techcombank.py` → `test_multi_rate.py` |
| Update | `app.py` (bar chart in tab1, add tab4) |
| Create | `stock/scrapers/_common.py` |
| Update | `stock/scrapers/vnstock.py` (import from `_common`) |
| Create | `stock/scrapers/intraday.py` |
| Create | `tests/stock/scrapers/test_intraday.py` |
| Update | `web/data_loader.py` (`load_portfolio`, `load_intraday_prices`) |
| Update | `tests/web/test_data_loader.py` (portfolio + intraday loader tests) |
| Create | `portfolio.json.example` |
| Update | `.gitignore` (add `portfolio.json`) |
| Create | `alerts/__init__.py` |
| Create | `alerts/checker.py` |
| Create | `alerts/notifier.py` |
| Create | `tests/alerts/__init__.py` |
| Create | `tests/alerts/test_checker.py` |
| Create | `tests/alerts/test_notifier.py` |

---

## Task 1: Rename Scraper + Bank Rate Chart

**Files:**
- Rename: `interest/scrapers/techcombank.py` → `interest/scrapers/multi_rate.py`
- Rename: `tests/interest/scrapers/test_techcombank.py` → `tests/interest/scrapers/test_multi_rate.py`
- Modify: `main.py`
- Modify: `app.py` (Interest Rates tab — add chart)

**Interfaces:**
- Produces: `MultiRateScraper` importable from `interest.scrapers.multi_rate`; used by `main.py` and existing tests

- [ ] **Step 1: Rename the scraper file and class**

In `interest/scrapers/multi_rate.py` (rename from `techcombank.py`), change only the class name and the import in the module itself — all logic stays identical:

```python
# interest/scrapers/multi_rate.py
import re
from datetime import date
from typing import Optional

import requests
from bs4 import BeautifulSoup

from interest.model import InterestRate
from interest.scrapers.base import BaseScraper

_URL = "https://techcombank.com/thong-tin/blog/lai-suat-tiet-kiem"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

_SKIP_BANK_NAMES = {"Ngân hàng", ""}


def _parse_rate(text: str) -> Optional[float]:
    text = text.strip()
    if not text or text in ("-", "—", "N/A", "n/a"):
        return None
    match = re.search(r"\d+(?:\.\d+)?", text)
    if match:
        return float(match.group())
    return None


class MultiRateScraper(BaseScraper):
    def scrape(self) -> list[InterestRate]:
        response = requests.get(_URL, headers=_HEADERS, timeout=30)
        response.raise_for_status()
        return self._parse(response.text)

    def _parse(self, html: str) -> list[InterestRate]:
        soup = BeautifulSoup(html, "html.parser")
        rate_tables = [
            t for t in soup.find_all("table")
            if t.find("tr") and t.find("tr").find(["td", "th"])
            and t.find("tr").find(["td", "th"]).get_text(strip=True) == "Ngân hàng"
        ]
        today = date.today().strftime("%Y-%m-%d")
        records: list[InterestRate] = []
        channels = ["counter", "online"]
        for table, channel in zip(rate_tables[:2], channels):
            records.extend(self._parse_table(table, channel, today))
        return records

    def _parse_table(self, table, channel: str, today: str) -> list[InterestRate]:
        records = []
        for row in table.find("tbody").find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 8:
                continue
            if cells[0].name == "th":
                continue
            bank = cells[0].get_text(strip=True)
            if bank in _SKIP_BANK_NAMES:
                continue
            records.append(InterestRate(
                date=today,
                bank=bank,
                channel=channel,
                rate_1m=_parse_rate(cells[1].get_text(strip=True)),
                rate_3m=_parse_rate(cells[2].get_text(strip=True)),
                rate_6m=_parse_rate(cells[3].get_text(strip=True)),
                rate_12m=_parse_rate(cells[4].get_text(strip=True)),
                rate_18m=_parse_rate(cells[5].get_text(strip=True)),
                rate_24m=_parse_rate(cells[6].get_text(strip=True)),
                rate_36m=_parse_rate(cells[7].get_text(strip=True)),
            ))
        return records
```

Delete `interest/scrapers/techcombank.py`.

- [ ] **Step 2: Update test file**

Delete `tests/interest/scrapers/test_techcombank.py`. Create `tests/interest/scrapers/test_multi_rate.py` — identical content but with updated import and mock patch path:

```python
# tests/interest/scrapers/test_multi_rate.py
import os
import pytest
from unittest.mock import patch, MagicMock
from interest.scrapers.multi_rate import MultiRateScraper

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "..", "fixtures", "techcombank_sample.html")


@pytest.fixture
def mock_response():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        html = f.read()
    mock = MagicMock()
    mock.text = html
    mock.raise_for_status = MagicMock()
    return mock


def test_scrape_returns_list(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    assert isinstance(records, list)


def test_scrape_returns_both_channels(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    channels = {r.channel for r in records}
    assert channels == {"counter", "online"}


def test_counter_techcombank_rates(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    tcb_counter = next(r for r in records if r.bank == "Techcombank" and r.channel == "counter")
    assert tcb_counter.rate_1m == 3.5
    assert tcb_counter.rate_3m == 4.0
    assert tcb_counter.rate_12m == 5.5
    assert tcb_counter.rate_18m is None


def test_online_techcombank_rates(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    tcb_online = next(r for r in records if r.bank == "Techcombank" and r.channel == "online")
    assert tcb_online.rate_1m == 3.7
    assert tcb_online.rate_18m is None


def test_dash_value_becomes_none(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    for r in records:
        assert r.rate_18m is None


def test_date_matches_today(mock_response):
    from datetime import date
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    assert all(r.date == date.today().strftime("%Y-%m-%d") for r in records)


def test_multiple_banks_parsed(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    counter_banks = [r.bank for r in records if r.channel == "counter"]
    assert "Techcombank" in counter_banks
    assert "Vietcombank" in counter_banks


def test_scrape_calls_raise_for_status(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        MultiRateScraper().scrape()
    mock_response.raise_for_status.assert_called_once()


_NO_THEAD_HTML = """<html><body>
<table>
  <tbody>
    <tr>
      <th>Ngân hàng</th><th>1 tháng</th><th>3 tháng</th>
      <th>6 tháng</th><th>12 tháng</th><th>18 tháng</th>
      <th>24 tháng</th><th>36 tháng</th>
    </tr>
    <tr>
      <td>Techcombank</td><td>3.5%/năm</td><td>4.0%/năm</td>
      <td>5.0%/năm</td><td>5.5%/năm</td><td>-</td>
      <td>5.8%/năm</td><td>6.0%/năm</td>
    </tr>
  </tbody>
</table>
<table>
  <tbody>
    <tr>
      <th>Ngân hàng</th><th>1 tháng</th><th>3 tháng</th>
      <th>6 tháng</th><th>12 tháng</th><th>18 tháng</th>
      <th>24 tháng</th><th>36 tháng</th>
    </tr>
    <tr>
      <td>Techcombank</td><td>3.7%/năm</td><td>4.2%/năm</td>
      <td>5.2%/năm</td><td>5.7%/năm</td><td>-</td>
      <td>6.0%/năm</td><td>6.2%/năm</td>
    </tr>
  </tbody>
</table>
</body></html>"""


def test_header_row_in_tbody_is_skipped():
    scraper = MultiRateScraper.__new__(MultiRateScraper)
    records = scraper._parse(_NO_THEAD_HTML)
    bank_names = [r.bank for r in records]
    assert "Ngân hàng" not in bank_names
    assert "Techcombank" in bank_names


def test_header_row_in_tbody_exact_record_count():
    scraper = MultiRateScraper.__new__(MultiRateScraper)
    records = scraper._parse(_NO_THEAD_HTML)
    assert len(records) == 2


_NGAN_HANG_TD_HTML = """<html><body>
<table>
  <tbody>
    <tr>
      <td>Ngân hàng</td><td>1 tháng</td><td>3 tháng</td>
      <td>6 tháng</td><td>12 tháng</td><td>18 tháng</td>
      <td>24 tháng</td><td>36 tháng</td>
    </tr>
    <tr>
      <td>Techcombank</td><td>3.5%/năm</td><td>4.0%/năm</td>
      <td>5.0%/năm</td><td>5.5%/năm</td><td>-</td>
      <td>5.8%/năm</td><td>6.0%/năm</td>
    </tr>
  </tbody>
</table>
<table>
  <tbody>
    <tr>
      <td>Ngân hàng</td><td>1 tháng</td><td>3 tháng</td>
      <td>6 tháng</td><td>12 tháng</td><td>18 tháng</td>
      <td>24 tháng</td><td>36 tháng</td>
    </tr>
    <tr>
      <td>Techcombank</td><td>3.7%/năm</td><td>4.2%/năm</td>
      <td>5.2%/năm</td><td>5.7%/năm</td><td>-</td>
      <td>6.0%/năm</td><td>6.2%/năm</td>
    </tr>
  </tbody>
</table>
</body></html>"""


def test_ngan_hang_td_row_is_skipped():
    scraper = MultiRateScraper.__new__(MultiRateScraper)
    records = scraper._parse(_NGAN_HANG_TD_HTML)
    bank_names = [r.bank for r in records]
    assert "Ngân hàng" not in bank_names
    assert "Techcombank" in bank_names
    assert len(records) == 2


_NOISY_RATES_HTML = """<html><body>
<table>
  <tbody>
    <tr>
      <td>Ngân hàng</td><td>1 tháng</td><td>3 tháng</td>
      <td>6 tháng</td><td>12 tháng</td><td>18 tháng</td>
      <td>24 tháng</td><td>36 tháng</td>
    </tr>
    <tr>
      <td>Techcombank</td>
      <td>4.40 Tham khảo: Biểu phí, lãi suất</td>
      <td>5.00 Tham khảo: Biểu phí, lãi suất</td>
      <td>5.50%/năm</td><td>6.00%/năm</td><td>-</td>
      <td>6.20%/năm</td><td>6.50%/năm</td>
    </tr>
  </tbody>
</table>
<table>
  <tbody>
    <tr>
      <td>Ngân hàng</td><td>1 tháng</td><td>3 tháng</td>
      <td>6 tháng</td><td>12 tháng</td><td>18 tháng</td>
      <td>24 tháng</td><td>36 tháng</td>
    </tr>
  </tbody>
</table>
</body></html>"""


def test_noisy_rate_extracts_leading_number():
    scraper = MultiRateScraper.__new__(MultiRateScraper)
    records = scraper._parse(_NOISY_RATES_HTML)
    assert len(records) == 1
    assert records[0].rate_1m == 4.40
    assert records[0].rate_3m == 5.00
    assert records[0].rate_6m == 5.50
```

- [ ] **Step 3: Run tests — must pass**

```bash
source venv/bin/activate && python -m pytest tests/interest/ -q
```

Expected: all interest tests pass (same count as before).

- [ ] **Step 4: Update `main.py` import**

Change line:
```python
from interest.scrapers.techcombank import TechcombankScraper
```
to:
```python
from interest.scrapers.multi_rate import MultiRateScraper
```

And update the `CrawlRunner` instantiation:
```python
CrawlRunner(
    [MultiRateScraper()],
    CSVRepository(data_dir=os.path.join(DATA_DIR, "interest")),
).run()
```

- [ ] **Step 5: Add bank rate bar chart to `app.py`**

Inside the `with tab1:` block, after the `st.dataframe(...)` call, append:

```python
        st.subheader("Rate Comparison Chart")
        chart_channel = st.radio(
            "Channel", ["counter", "online"], horizontal=True, key="interest_chart_channel"
        )
        chart_df = load_interest(date)
        chart_df = chart_df[chart_df["channel"] == chart_channel][
            ["bank", "rate_3m", "rate_6m", "rate_12m", "rate_24m"]
        ].set_index("bank").rename(columns={
            "rate_3m": "3m %", "rate_6m": "6m %",
            "rate_12m": "12m %", "rate_24m": "24m %",
        })
        st.bar_chart(chart_df)
```

- [ ] **Step 6: Run full suite and commit**

```bash
source venv/bin/activate && python -m pytest tests/ -q
```

Expected: 80+ passing, 0 failures.

```bash
git add interest/scrapers/multi_rate.py main.py app.py \
    tests/interest/scrapers/test_multi_rate.py && \
git rm interest/scrapers/techcombank.py \
    tests/interest/scrapers/test_techcombank.py && \
git commit -m "feat: rename TechcombankScraper to MultiRateScraper, add bank rate chart"
```

---

## Task 2: Shared Constants + Intraday Scraper

**Files:**
- Create: `stock/scrapers/_common.py`
- Modify: `stock/scrapers/vnstock.py` (import from `_common`)
- Create: `stock/scrapers/intraday.py`
- Create: `tests/stock/scrapers/test_intraday.py`

**Interfaces:**
- Produces:
  - `stock.scrapers.intraday.is_market_open() -> bool`
  - `stock.scrapers.intraday.fetch_intraday_prices(symbols: list[str]) -> dict[str, int]`

- [ ] **Step 1: Create `stock/scrapers/_common.py`**

```python
# stock/scrapers/_common.py
_OHLC_URL = "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _to_vnd(raw: float) -> int:
    return int(round(raw * 1000))
```

- [ ] **Step 2: Update `stock/scrapers/vnstock.py` to import from `_common`**

Replace the three local definitions at the top of `vnstock.py`:
```python
_OHLC_URL = "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
_HEADERS = { ... }
...
def _to_vnd(raw: float) -> int:
    return int(round(raw * 1000))
```
with a single import line (keep `_LISTING_URL` and `_MAX_WORKERS` in `vnstock.py`):
```python
from stock.scrapers._common import _OHLC_URL, _HEADERS, _to_vnd
```

The rest of `vnstock.py` is unchanged.

- [ ] **Step 3: Run existing stock scraper tests to confirm no regression**

```bash
source venv/bin/activate && python -m pytest tests/stock/scrapers/test_vnstock.py -q
```

Expected: all pass.

- [ ] **Step 4: Write failing tests for `intraday.py`**

Create `tests/stock/scrapers/test_intraday.py`:

```python
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from stock.scrapers.intraday import is_market_open, fetch_intraday_prices

_VN_TZ = timezone(timedelta(hours=7))


def _make_dt(weekday: int, hour: int) -> datetime:
    # weekday: 0=Mon … 4=Fri, 5=Sat, 6=Sun
    # Find next date with that weekday from a fixed base
    from datetime import date, timedelta as td
    base = date(2026, 6, 22)  # Monday
    delta = (weekday - base.weekday()) % 7
    d = base + td(days=delta)
    return datetime(d.year, d.month, d.day, hour, 0, tzinfo=_VN_TZ)


def test_is_market_open_weekday_morning():
    with patch("stock.scrapers.intraday.datetime") as mock_dt:
        mock_dt.now.return_value = _make_dt(0, 10)  # Monday 10:00
        assert is_market_open() is True


def test_is_market_open_weekday_before_open():
    with patch("stock.scrapers.intraday.datetime") as mock_dt:
        mock_dt.now.return_value = _make_dt(0, 8)  # Monday 08:00
        assert is_market_open() is False


def test_is_market_open_weekday_after_close():
    with patch("stock.scrapers.intraday.datetime") as mock_dt:
        mock_dt.now.return_value = _make_dt(0, 15)  # Monday 15:00
        assert is_market_open() is False


def test_is_market_open_saturday():
    with patch("stock.scrapers.intraday.datetime") as mock_dt:
        mock_dt.now.return_value = _make_dt(5, 10)  # Saturday 10:00
        assert is_market_open() is False


def test_fetch_intraday_prices_returns_vnd():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "t": [1782190000],
        "o": [32.0], "h": [32.1], "l": [31.9],
        "c": [32.05],
        "v": [100000],
    }
    with patch("stock.scrapers.intraday.requests.get", return_value=mock_resp):
        result = fetch_intraday_prices(["TCB"])
    assert result == {"TCB": 32050}


def test_fetch_intraday_prices_skips_empty_symbol():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"t": [], "c": []}
    with patch("stock.scrapers.intraday.requests.get", return_value=mock_resp):
        result = fetch_intraday_prices(["XXX"])
    assert result == {}


def test_fetch_intraday_prices_skips_on_exception():
    with patch("stock.scrapers.intraday.requests.get", side_effect=Exception("timeout")):
        result = fetch_intraday_prices(["TCB"])
    assert result == {}


def test_fetch_intraday_prices_multiple_symbols():
    def _side_effect(url, params, headers, timeout):
        sym = params["symbol"]
        mock = MagicMock()
        mock.raise_for_status = MagicMock()
        if sym == "TCB":
            mock.json.return_value = {"t": [1], "c": [32.05], "o": [32.0], "h": [32.1], "l": [31.9], "v": [100]}
        else:
            mock.json.return_value = {"t": [1], "c": [100.0], "o": [99.0], "h": [101.0], "l": [98.0], "v": [200]}
        return mock

    with patch("stock.scrapers.intraday.requests.get", side_effect=_side_effect):
        result = fetch_intraday_prices(["TCB", "VCB"])
    assert result["TCB"] == 32050
    assert result["VCB"] == 100000
```

- [ ] **Step 5: Run tests to confirm they fail**

```bash
source venv/bin/activate && python -m pytest tests/stock/scrapers/test_intraday.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'stock.scrapers.intraday'`

- [ ] **Step 6: Implement `stock/scrapers/intraday.py`**

```python
# stock/scrapers/intraday.py
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
```

- [ ] **Step 7: Run tests — must pass**

```bash
source venv/bin/activate && python -m pytest tests/stock/scrapers/test_intraday.py -q
```

Expected: all 8 pass.

- [ ] **Step 8: Run full suite and commit**

```bash
source venv/bin/activate && python -m pytest tests/ -q
```

Expected: 80+ passing.

```bash
git add stock/scrapers/_common.py stock/scrapers/intraday.py \
    stock/scrapers/vnstock.py tests/stock/scrapers/test_intraday.py && \
git commit -m "feat: extract _common.py, add intraday price scraper"
```

---

## Task 3: Portfolio Config + Data Loaders

**Files:**
- Create: `portfolio.json.example`
- Modify: `.gitignore`
- Modify: `web/data_loader.py` (add `load_portfolio`, `load_intraday_prices`)
- Modify: `tests/web/test_data_loader.py`

**Interfaces:**
- Consumes: `stock.scrapers.intraday.fetch_intraday_prices`, `stock.scrapers.intraday.is_market_open` (from Task 2)
- Produces:
  - `load_portfolio() -> dict` — `{"watchlist": list[str], "holdings": list[dict]}`
  - `load_intraday_prices(symbols: tuple) -> dict[str, int]`

- [ ] **Step 1: Create `portfolio.json.example`**

```json
{
  "watchlist": ["TCB", "VCB", "HPG"],
  "holdings": [
    {"symbol": "TCB", "quantity": 1000, "buy_price": 28500},
    {"symbol": "VCB", "quantity": 500, "buy_price": 95000}
  ]
}
```

- [ ] **Step 2: Add `portfolio.json` to `.gitignore`**

Append to `.gitignore`:
```
portfolio.json
```

- [ ] **Step 3: Write failing tests for `load_portfolio` and `load_intraday_prices`**

Append to `tests/web/test_data_loader.py`:

```python
import json
from unittest.mock import patch
from web.data_loader import load_portfolio, load_intraday_prices

_PORTFOLIO = {
    "watchlist": ["TCB", "VCB"],
    "holdings": [{"symbol": "TCB", "quantity": 1000, "buy_price": 28500}],
}


def test_load_portfolio_returns_data(tmp_path, monkeypatch):
    p = tmp_path / "portfolio.json"
    p.write_text(json.dumps(_PORTFOLIO), encoding="utf-8")
    monkeypatch.setattr("web.data_loader._PORTFOLIO_PATH", str(p))
    result = load_portfolio()
    assert result["watchlist"] == ["TCB", "VCB"]
    assert len(result["holdings"]) == 1
    assert result["holdings"][0]["symbol"] == "TCB"


def test_load_portfolio_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("web.data_loader._PORTFOLIO_PATH", str(tmp_path / "missing.json"))
    result = load_portfolio()
    assert result == {"watchlist": [], "holdings": []}


def test_load_intraday_prices_skips_when_market_closed():
    with patch("web.data_loader.is_market_open", return_value=False):
        result = load_intraday_prices(("TCB", "VCB"))
    assert result == {}


def test_load_intraday_prices_fetches_when_market_open():
    with patch("web.data_loader.is_market_open", return_value=True), \
         patch("web.data_loader.fetch_intraday_prices", return_value={"TCB": 32050}) as mock_fetch:
        result = load_intraday_prices(("TCB",))
    mock_fetch.assert_called_once_with(["TCB"])
    assert result == {"TCB": 32050}
```

- [ ] **Step 4: Run tests to confirm they fail**

```bash
source venv/bin/activate && python -m pytest tests/web/test_data_loader.py -q
```

Expected: FAIL — `ImportError: cannot import name 'load_portfolio'`

- [ ] **Step 5: Implement in `web/data_loader.py`**

Add at the top with the other imports:
```python
import json
```

After the existing `DATA_DIR` line, add:
```python
_PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "..", "portfolio.json")
```

Append the two new functions to the end of `web/data_loader.py`:

```python
@st.cache_data(ttl=300)
def load_portfolio() -> dict:
    if not os.path.exists(_PORTFOLIO_PATH):
        return {"watchlist": [], "holdings": []}
    with open(_PORTFOLIO_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {
        "watchlist": data.get("watchlist", []),
        "holdings": data.get("holdings", []),
    }


@st.cache_data(ttl=60)
def load_intraday_prices(symbols: tuple) -> dict:
    from stock.scrapers.intraday import fetch_intraday_prices, is_market_open
    if not is_market_open():
        return {}
    return fetch_intraday_prices(list(symbols))
```

- [ ] **Step 6: Run tests — must pass**

```bash
source venv/bin/activate && python -m pytest tests/web/test_data_loader.py -q
```

Expected: all pass (4 new tests + existing tests).

- [ ] **Step 7: Run full suite and commit**

```bash
source venv/bin/activate && python -m pytest tests/ -q
```

```bash
git add portfolio.json.example .gitignore web/data_loader.py \
    tests/web/test_data_loader.py && \
git commit -m "feat: add portfolio config, load_portfolio and load_intraday_prices loaders"
```

---

## Task 4: Portfolio Dashboard Tab

**Files:**
- Modify: `app.py` (add tab4)

**Interfaces:**
- Consumes (from Task 3): `load_portfolio()`, `load_intraday_prices(symbols: tuple)`
- Consumes (existing): `load_stock(date: str)`, `available_dates(domain: str)`

- [ ] **Step 1: Update tab declaration in `app.py`**

Change:
```python
tab1, tab2, tab3 = st.tabs(["💰 Interest Rates", "📈 Stock Prices", "📰 News"])
```
to:
```python
tab1, tab2, tab3, tab4 = st.tabs(["💰 Interest Rates", "📈 Stock Prices", "📰 News", "💼 Portfolio"])
```

Also update the imports at the top of `app.py`:
```python
from web.data_loader import (
    available_dates,
    available_news_dates,
    load_interest,
    load_intraday_prices,
    load_news,
    load_portfolio,
    load_stock,
)
```

- [ ] **Step 2: Add the Portfolio tab block at the end of `app.py`**

```python
# ── Portfolio ─────────────────────────────────────────────────────────────────
with tab4:
    portfolio = load_portfolio()
    watchlist = portfolio["watchlist"]
    holdings = portfolio["holdings"]
    all_symbols = list({sym for sym in watchlist} | {h["symbol"] for h in holdings})

    if not all_symbols:
        st.info("Create portfolio.json to track your positions. See portfolio.json.example.")
    else:
        stock_dates = available_dates("stock")
        if not stock_dates:
            st.info("No stock data yet. Run main.py first.")
        else:
            today_date = stock_dates[0]
            df_today = load_stock(today_date)
            df_yest = load_stock(stock_dates[1]) if len(stock_dates) > 1 else pd.DataFrame(columns=["symbol", "close"])

            intraday = load_intraday_prices(tuple(all_symbols))

            eod_map = dict(zip(df_today["symbol"], df_today["close"]))
            yest_map = dict(zip(df_yest["symbol"], df_yest["close"])) if not df_yest.empty else {}
            vol_map = dict(zip(df_today["symbol"], df_today["volume"]))

            def _current_price(sym):
                if sym in intraday:
                    return intraday[sym], "🟡 live"
                return eod_map.get(sym), "📅 T-1"

            # ── Watchlist ──
            st.subheader("Watchlist")
            wl_rows = []
            for sym in sorted(all_symbols):
                price, source = _current_price(sym)
                yest = yest_map.get(sym)
                change = round((price - yest) / yest * 100, 2) if price and yest else None
                wl_rows.append({
                    "Symbol": sym,
                    "Price": price,
                    "Source": source,
                    "Change %": change,
                    "Volume": vol_map.get(sym),
                })
            wl_df = pd.DataFrame(wl_rows)

            def _highlight_change(row):
                if row["Change %"] is not None and abs(row["Change %"]) >= 3:
                    return ["background-color:#fff9c4"] * len(row)
                return [""] * len(row)

            st.dataframe(
                wl_df.style.apply(_highlight_change, axis=1),
                use_container_width=True,
                hide_index=True,
            )

            # ── Holdings ──
            if holdings:
                st.subheader("Holdings")
                h_rows = []
                total_invested = 0
                total_current = 0
                for h in holdings:
                    sym = h["symbol"]
                    qty = h["quantity"]
                    buy_p = h["buy_price"]
                    price, _ = _current_price(sym)
                    if price:
                        pnl_vnd = (price - buy_p) * qty
                        pnl_pct = round((price - buy_p) / buy_p * 100, 2)
                        total_invested += buy_p * qty
                        total_current += price * qty
                    else:
                        pnl_vnd = None
                        pnl_pct = None
                    h_rows.append({
                        "Symbol": sym,
                        "Qty": qty,
                        "Buy Price": buy_p,
                        "Current Price": price,
                        "P&L (VND)": pnl_vnd,
                        "P&L %": pnl_pct,
                    })
                st.dataframe(pd.DataFrame(h_rows), use_container_width=True, hide_index=True)

                if total_invested:
                    total_pnl = total_current - total_invested
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Invested", f"₫{total_invested:,.0f}")
                    c2.metric("Current Value", f"₫{total_current:,.0f}")
                    c3.metric("Total P&L", f"₫{total_pnl:,.0f}",
                              delta=f"{total_pnl / total_invested * 100:.2f}%")
```

- [ ] **Step 3: Run full suite**

```bash
source venv/bin/activate && python -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add app.py && git commit -m "feat: add Portfolio tab with watchlist, holdings, P&L, and intraday prices"
```

---

## Task 5: Alerts Package

**Files:**
- Create: `alerts/__init__.py`
- Create: `alerts/checker.py`
- Create: `alerts/notifier.py`
- Create: `tests/alerts/__init__.py`
- Create: `tests/alerts/test_checker.py`
- Create: `tests/alerts/test_notifier.py`

**Interfaces:**
- Produces:
  - `alerts.checker.check_price_alerts(watchlist, df_today, df_yesterday, threshold_pct=3.0, intraday=None) -> list[dict]`
  - `alerts.checker.check_news_alerts(watchlist, articles) -> list[dict]`
  - `alerts.notifier.notify(title, body) -> None`

- [ ] **Step 1: Write failing tests for `checker.py`**

Create `tests/alerts/__init__.py` (empty) and `tests/alerts/test_checker.py`:

```python
import pytest
import pandas as pd
from news.model import NewsArticle
from alerts.checker import check_price_alerts, check_news_alerts


def _df(rows):
    return pd.DataFrame(rows, columns=["symbol", "close"])


def _article(title, description="", source="vnexpress"):
    return NewsArticle(
        source=source, title=title, url="https://example.com",
        published_at="2026-06-23T10:00:00+07:00", description=description,
    )


def test_price_alert_above_threshold():
    df_today = _df([("TCB", 32050)])
    df_yest = _df([("TCB", 30000)])
    results = check_price_alerts(["TCB"], df_today, df_yest)
    assert len(results) == 1
    assert results[0]["symbol"] == "TCB"
    assert results[0]["change_pct"] == pytest.approx(6.83, abs=0.01)


def test_price_alert_below_threshold():
    df_today = _df([("TCB", 30500)])
    df_yest = _df([("TCB", 30000)])
    results = check_price_alerts(["TCB"], df_today, df_yest)
    assert results == []


def test_price_alert_negative_move():
    df_today = _df([("HPG", 28000)])
    df_yest = _df([("HPG", 30000)])
    results = check_price_alerts(["HPG"], df_today, df_yest)
    assert len(results) == 1
    assert results[0]["change_pct"] < 0


def test_price_alert_symbol_missing_today():
    df_today = _df([])
    df_yest = _df([("TCB", 30000)])
    results = check_price_alerts(["TCB"], df_today, df_yest)
    assert results == []


def test_price_alert_symbol_missing_yesterday():
    df_today = _df([("TCB", 32050)])
    df_yest = _df([])
    results = check_price_alerts(["TCB"], df_today, df_yest)
    assert results == []


def test_price_alert_uses_intraday_when_provided():
    df_today = _df([("TCB", 30100)])   # EOD: +0.3%, under threshold
    df_yest = _df([("TCB", 30000)])
    intraday = {"TCB": 32050}          # intraday: +6.8%, over threshold
    results = check_price_alerts(["TCB"], df_today, df_yest, intraday=intraday)
    assert len(results) == 1
    assert results[0]["change_pct"] == pytest.approx(6.83, abs=0.01)


def test_news_alert_title_match():
    articles = [_article("TCB tăng mạnh hôm nay")]
    results = check_news_alerts(["TCB"], articles)
    assert len(results) == 1
    assert results[0]["symbol"] == "TCB"


def test_news_alert_description_match():
    articles = [_article("Thị trường hôm nay", description="Cổ phiếu HPG tăng 5%")]
    results = check_news_alerts(["HPG"], articles)
    assert len(results) == 1


def test_news_alert_no_match():
    articles = [_article("Thị trường ổn định")]
    results = check_news_alerts(["TCB", "VCB"], articles)
    assert results == []


def test_news_alert_case_insensitive():
    articles = [_article("tcb hôm nay")]
    results = check_news_alerts(["TCB"], articles)
    assert len(results) == 1
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
source venv/bin/activate && python -m pytest tests/alerts/test_checker.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'alerts'`

- [ ] **Step 3: Implement `alerts/__init__.py` and `alerts/checker.py`**

Create empty `alerts/__init__.py`.

Create `alerts/checker.py`:

```python
# alerts/checker.py
from typing import Optional

import pandas as pd

from news.model import NewsArticle


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
```

- [ ] **Step 4: Run checker tests — must pass**

```bash
source venv/bin/activate && python -m pytest tests/alerts/test_checker.py -q
```

Expected: all 10 pass.

- [ ] **Step 5: Write failing tests for `notifier.py`**

Create `tests/alerts/test_notifier.py`:

```python
import sys
from unittest.mock import patch, call
from alerts.notifier import notify


def test_notify_calls_osascript_on_darwin():
    with patch("alerts.notifier.sys") as mock_sys, \
         patch("alerts.notifier.subprocess.run") as mock_run:
        mock_sys.platform = "darwin"
        notify("Test Title", "Test Body")
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == "osascript"
    assert "Test Title" in args[2]
    assert "Test Body" in args[2]


def test_notify_noop_on_non_darwin():
    with patch("alerts.notifier.sys") as mock_sys, \
         patch("alerts.notifier.subprocess.run") as mock_run:
        mock_sys.platform = "linux"
        notify("Title", "Body")
    mock_run.assert_not_called()


def test_notify_silently_ignores_exception():
    with patch("alerts.notifier.sys") as mock_sys, \
         patch("alerts.notifier.subprocess.run", side_effect=Exception("fail")):
        mock_sys.platform = "darwin"
        notify("Title", "Body")  # must not raise
```

- [ ] **Step 6: Run notifier tests to confirm they fail**

```bash
source venv/bin/activate && python -m pytest tests/alerts/test_notifier.py -q
```

Expected: FAIL.

- [ ] **Step 7: Implement `alerts/notifier.py`**

```python
# alerts/notifier.py
import subprocess
import sys


def notify(title: str, body: str) -> None:
    if sys.platform != "darwin":
        return
    try:
        script = f'display notification "{body}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=False, timeout=5)
    except Exception:
        pass
```

- [ ] **Step 8: Run full suite and commit**

```bash
source venv/bin/activate && python -m pytest tests/ -q
```

Expected: all pass.

```bash
git add alerts/__init__.py alerts/checker.py alerts/notifier.py \
    tests/alerts/__init__.py tests/alerts/test_checker.py tests/alerts/test_notifier.py && \
git commit -m "feat: add alerts package — price checker, news checker, macOS notifier"
```

---

## Task 6: Wire Alerts into `main.py`

**Files:**
- Modify: `main.py`

**Interfaces:**
- Consumes (Task 2): `stock.scrapers.intraday.fetch_intraday_prices`, `stock.scrapers.intraday.is_market_open`
- Consumes (Task 5): `alerts.checker.check_price_alerts`, `alerts.checker.check_news_alerts`, `alerts.notifier.notify`

- [ ] **Step 1: Replace `main.py` with the wired version**

```python
# main.py
import json
import os
import pandas as pd
from datetime import date, timedelta

from interest.runner import CrawlRunner
from interest.scrapers.multi_rate import MultiRateScraper
from interest.repositories.csv import CSVRepository
from stock.runner import StockCrawlRunner
from stock.scrapers.vnstock import VnstockScraper
from stock.repositories.csv import StockCSVRepository

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def _load_stock_csv(date_str: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "stock", f"stock_{date_str}.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["symbol", "close"])
    return pd.read_csv(path)


def main():
    CrawlRunner(
        [MultiRateScraper()],
        CSVRepository(data_dir=os.path.join(DATA_DIR, "interest")),
    ).run()

    StockCrawlRunner(
        [VnstockScraper()],
        StockCSVRepository(data_dir=os.path.join(DATA_DIR, "stock")),
    ).run()

    from news.repositories.json_repo import JSONNewsRepository
    from news.runner import NewsRunner
    from news.scrapers.cafef import CafefScraper
    from news.scrapers.vnexpress import VnExpressScraper
    from news.scrapers.vietstock import VietstockScraper
    news_repo = JSONNewsRepository(data_dir=os.path.join(DATA_DIR, "news"))
    NewsRunner(
        [VnExpressScraper(), CafefScraper(), VietstockScraper()],
        news_repo,
    ).run()

    portfolio_path = os.path.join(BASE_DIR, "portfolio.json")
    if not os.path.exists(portfolio_path):
        return

    with open(portfolio_path, encoding="utf-8") as f:
        portfolio = json.load(f)

    watchlist = list(
        {sym for sym in portfolio.get("watchlist", [])} |
        {h["symbol"] for h in portfolio.get("holdings", [])}
    )
    if not watchlist:
        return

    from alerts.checker import check_price_alerts, check_news_alerts
    from alerts.notifier import notify
    from stock.scrapers.intraday import fetch_intraday_prices, is_market_open

    today_str = date.today().strftime("%Y-%m-%d")
    yest_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    df_today = _load_stock_csv(today_str)
    df_yest = _load_stock_csv(yest_str)

    intraday = fetch_intraday_prices(watchlist) if is_market_open() else {}

    for hit in check_price_alerts(watchlist, df_today, df_yest, intraday=intraday):
        sign = "+" if hit["change_pct"] > 0 else ""
        notify(f"📈 {hit['symbol']}", f"{sign}{hit['change_pct']:.1f}%")

    articles = news_repo.load(today_str)
    seen = set()
    for hit in check_news_alerts(watchlist, articles):
        key = (hit["symbol"], hit["title"])
        if key not in seen:
            seen.add(key)
            notify(f"📰 {hit['symbol']}", hit["title"][:80])


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run full suite**

```bash
source venv/bin/activate && python -m pytest tests/ -q
```

Expected: all pass (no tests directly test `main()` — integration is verified by running the app).

- [ ] **Step 3: Smoke-test `main.py` import**

```bash
source venv/bin/activate && python -c "import main; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit and push**

```bash
git add main.py && \
git commit -m "feat: wire alerts into main.py — price moves and news mentions notify macOS" && \
git push
```
