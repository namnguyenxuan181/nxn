2# NXN Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Streamlit web app with two tabs — Interest Rates and Stock Prices — reading from existing daily CSV files.

**Architecture:** `web/data_loader.py` handles CSV discovery and loading (cached). `app.py` is the Streamlit entry point with two `st.tabs()`. No database, no server — run locally with `streamlit run app.py`.

**Tech Stack:** Python 3.9, Streamlit ≥1.35.0, Pandas (already installed)

## Global Constraints

- Python 3.9 — no walrus operator or `match` statements
- Data dirs: `data/interest/interest_YYYY-MM-DD.csv` and `data/stock/stock_YYYY-MM-DD.csv`
- Interest CSV columns: date, bank, channel, rate_1m, rate_3m, rate_6m, rate_12m, rate_18m, rate_24m, rate_36m
- Stock CSV columns: date, symbol, open, high, low, close, volume
- No new top-level packages beyond `web/` and `app.py`
- `streamlit>=1.35.0` added to `requirements.txt`

---

## Files

| File | Action | Responsibility |
|------|--------|----------------|
| `requirements.txt` | Modify | Add `streamlit>=1.35.0` |
| `web/__init__.py` | Create | Package marker |
| `web/data_loader.py` | Create | CSV discovery + loading, cached |
| `tests/web/__init__.py` | Create | Package marker |
| `tests/web/conftest.py` | Create | Mock `st.cache_data` for tests |
| `tests/web/test_data_loader.py` | Create | Unit tests for data_loader |
| `app.py` | Create | Streamlit UI — two tabs |

---

### Task 1: data_loader + tests

**Files:**
- Create: `web/__init__.py`
- Create: `web/data_loader.py`
- Create: `tests/web/__init__.py`
- Create: `tests/web/conftest.py`
- Create: `tests/web/test_data_loader.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces:
  - `available_dates(domain: str) -> list[str]` — sorted descending
  - `load_interest(date: str) -> pd.DataFrame`
  - `load_stock(date: str) -> pd.DataFrame`

- [ ] **Step 1: Add streamlit to requirements.txt**

```text
requests==2.31.0
beautifulsoup4==4.12.3
streamlit>=1.35.0
```

Install: `pip install streamlit`

- [ ] **Step 2: Create `web/__init__.py` and `tests/web/__init__.py`**

Both files are empty.

- [ ] **Step 3: Create `tests/web/conftest.py` — mock st.cache_data**

```python
# tests/web/conftest.py
import sys
from unittest.mock import MagicMock

mock_st = MagicMock()
mock_st.cache_data = lambda f: f  # no-op decorator
sys.modules["streamlit"] = mock_st
```

- [ ] **Step 4: Write failing tests in `tests/web/test_data_loader.py`**

```python
import os
import pytest
import pandas as pd
from web.data_loader import available_dates, load_interest, load_stock


def _write_csv(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


_INTEREST_CSV = (
    "date,bank,channel,rate_1m,rate_3m,rate_6m,rate_12m,rate_18m,rate_24m,rate_36m\n"
    "2026-06-19,Techcombank,counter,4.4,4.7,6.4,6.6,,5.7,5.7\n"
)

_STOCK_CSV = (
    "date,symbol,open,high,low,close,volume\n"
    "2026-06-18,HPG,24050,24150,23650,23650,18040500\n"
)


def test_available_dates_returns_sorted_desc(tmp_path, monkeypatch):
    monkeypatch.setattr("web.data_loader.DATA_DIR", str(tmp_path))
    _write_csv(str(tmp_path / "interest" / "interest_2026-06-17.csv"), _INTEREST_CSV)
    _write_csv(str(tmp_path / "interest" / "interest_2026-06-19.csv"), _INTEREST_CSV)
    dates = available_dates("interest")
    assert dates == ["2026-06-19", "2026-06-17"]


def test_available_dates_returns_empty_when_no_files(tmp_path, monkeypatch):
    monkeypatch.setattr("web.data_loader.DATA_DIR", str(tmp_path))
    (tmp_path / "interest").mkdir()
    assert available_dates("interest") == []


def test_load_interest_returns_dataframe(tmp_path, monkeypatch):
    monkeypatch.setattr("web.data_loader.DATA_DIR", str(tmp_path))
    _write_csv(str(tmp_path / "interest" / "interest_2026-06-19.csv"), _INTEREST_CSV)
    df = load_interest("2026-06-19")
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == [
        "date", "bank", "channel",
        "rate_1m", "rate_3m", "rate_6m", "rate_12m",
        "rate_18m", "rate_24m", "rate_36m",
    ]
    assert len(df) == 1
    assert df.iloc[0]["bank"] == "Techcombank"


def test_load_stock_returns_dataframe(tmp_path, monkeypatch):
    monkeypatch.setattr("web.data_loader.DATA_DIR", str(tmp_path))
    _write_csv(str(tmp_path / "stock" / "stock_2026-06-18.csv"), _STOCK_CSV)
    df = load_stock("2026-06-18")
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["date", "symbol", "open", "high", "low", "close", "volume"]
    assert len(df) == 1
    assert df.iloc[0]["symbol"] == "HPG"
    assert df.iloc[0]["close"] == 23650
```

- [ ] **Step 5: Run tests — verify they fail**

```bash
source venv/bin/activate
pytest tests/web/test_data_loader.py -v
```

Expected: `ModuleNotFoundError: No module named 'web.data_loader'`

- [ ] **Step 6: Implement `web/data_loader.py`**

```python
import glob
import os
import re

import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@st.cache_data
def available_dates(domain: str) -> list[str]:
    pattern = os.path.join(DATA_DIR, domain, f"{domain}_*.csv")
    files = glob.glob(pattern)
    dates = []
    for f in files:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(f))
        if m:
            dates.append(m.group(1))
    return sorted(dates, reverse=True)


@st.cache_data
def load_interest(date: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "interest", f"interest_{date}.csv")
    return pd.read_csv(path)


@st.cache_data
def load_stock(date: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "stock", f"stock_{date}.csv")
    return pd.read_csv(path)
```

- [ ] **Step 7: Run tests — verify they pass**

```bash
pytest tests/web/test_data_loader.py -v
```

Expected: 4 passed

- [ ] **Step 8: Run full suite to check for regressions**

```bash
pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 9: Commit**

```bash
git add web/__init__.py web/data_loader.py \
        tests/web/__init__.py tests/web/conftest.py tests/web/test_data_loader.py \
        requirements.txt
git commit -m "feat: add web/data_loader for CSV discovery and loading"
```

---

### Task 2: app.py — full Streamlit UI

**Files:**
- Create: `app.py`

**Interfaces:**
- Consumes:
  - `available_dates(domain: str) -> list[str]` from `web.data_loader`
  - `load_interest(date: str) -> pd.DataFrame` from `web.data_loader`
  - `load_stock(date: str) -> pd.DataFrame` from `web.data_loader`

No unit tests for the UI — verified by running Streamlit and checking both tabs manually.

- [ ] **Step 1: Create `app.py`**

```python
import streamlit as st
from web.data_loader import available_dates, load_interest, load_stock

st.set_page_config(page_title="NXN Dashboard", layout="wide")
st.title("📊 NXN Dashboard")

tab1, tab2 = st.tabs(["💰 Interest Rates", "📈 Stock Prices"])

# ── Interest Rates ────────────────────────────────────────────────────────────
with tab1:
    dates = available_dates("interest")
    if not dates:
        st.info("No data available yet. Run main.py first.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            date = st.selectbox("Date", dates, key="interest_date")
        with col2:
            channel = st.selectbox("Channel", ["All", "counter", "online"], key="interest_channel")

        df = load_interest(date)
        if channel != "All":
            df = df[df["channel"] == channel]

        display = df.drop(columns=["date"]).rename(columns={
            "bank": "Bank", "channel": "Channel",
            "rate_1m": "1m %", "rate_3m": "3m %", "rate_6m": "6m %",
            "rate_12m": "12m %", "rate_18m": "18m %",
            "rate_24m": "24m %", "rate_36m": "36m %",
        })

        rate_cols = ["1m %", "3m %", "6m %", "12m %", "18m %", "24m %", "36m %"]
        st.dataframe(
            display.style.background_gradient(subset=rate_cols, cmap="RdYlGn"),
            use_container_width=True,
            hide_index=True,
        )

# ── Stock Prices ──────────────────────────────────────────────────────────────
with tab2:
    dates = available_dates("stock")
    if not dates:
        st.info("No data available yet. Run main.py first.")
    else:
        col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
        with col1:
            date = st.selectbox("Date", dates, key="stock_date")
        with col2:
            search = st.text_input("Search symbol", key="stock_search")
        with col3:
            sort_col = st.selectbox(
                "Sort by", ["symbol", "open", "high", "low", "close", "volume"],
                key="stock_sort",
            )
        with col4:
            order = st.selectbox("Order", ["Descending", "Ascending"], key="stock_order")

        df = load_stock(date)
        if search:
            df = df[df["symbol"].str.contains(search.upper(), na=False)]

        df = df.sort_values(sort_col, ascending=(order == "Ascending"))

        display = df.drop(columns=["date"]).rename(columns={
            "symbol": "Symbol", "open": "Open", "high": "High",
            "low": "Low", "close": "Close", "volume": "Volume",
        })

        st.dataframe(
            display.style.format({
                "Open": "{:,.0f}", "High": "{:,.0f}",
                "Low": "{:,.0f}", "Close": "{:,.0f}",
                "Volume": "{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
```

- [ ] **Step 2: Launch and verify Interest Rates tab**

```bash
source venv/bin/activate
streamlit run app.py
```

Open http://localhost:8501. Check:
- "💰 Interest Rates" tab active by default
- Date selectbox shows available dates
- Channel filter works (All / counter / online)
- Table renders with green/red colour gradient on rate columns

- [ ] **Step 3: Verify Stock Prices tab**

Click "📈 Stock Prices" tab. Check:
- Date selectbox shows available dates
- Typing a symbol in the search box filters rows (e.g. "HPG")
- Sort by Close descending shows highest-priced stocks first
- Prices display with comma separators (e.g. 24,050)

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add Streamlit dashboard with interest rates and stock prices tabs"
```
