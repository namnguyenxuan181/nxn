# NXN Dashboard — Design Spec

## Goal
Local Streamlit web app presenting two data domains: bank interest rates and Vietnamese stock prices, each in its own tab.

## Audience
Personal / local use only. No auth, no hosting required.

## Tech Stack
- Streamlit (UI framework)
- Pandas (data loading and filtering)
- Python 3.9+

## File Structure

```
app.py              ← streamlit entry point (`streamlit run app.py`)
web/
  __init__.py
  data_loader.py    ← CSV discovery, loading, caching
```

## Data Sources
- `data/interest/interest_YYYY-MM-DD.csv` — columns: date, bank, channel, rate_1m … rate_36m (float %)
- `data/stock/stock_YYYY-MM-DD.csv` — columns: date, symbol, open, high, low, close, volume (int VND)

## data_loader.py

Two public functions:

```python
def available_dates(domain: str) -> list[str]
    # scans data/{domain}/ for YYYY-MM-DD in filenames, returns sorted desc

def load_interest(date: str) -> pd.DataFrame
    # reads data/interest/interest_{date}.csv, cached

def load_stock(date: str) -> pd.DataFrame
    # reads data/stock/stock_{date}.csv, cached
```

All three functions decorated with `@st.cache_data`.

## app.py — Layout

```
st.title("📊 NXN Dashboard")
tab1, tab2 = st.tabs(["💰 Interest Rates", "📈 Stock Prices"])
```

### Tab 1 — Interest Rates

Controls (sidebar-style row):
- Date selectbox (latest date pre-selected)
- Channel selectbox: All / counter / online

Table:
- One row per bank, columns: Bank, 1m, 3m, 6m, 12m, 18m, 24m, 36m
- Pivoted so channel appears as a sub-header or separate view when "All" selected
- Background gradient per column (green = high rate, red = low / empty)

### Tab 2 — Stock Prices

Controls (row):
- Date selectbox (latest date pre-selected)
- Symbol search text input (filters rows by prefix/contains)
- Sort-by selectbox: Symbol / Open / High / Low / Close / Volume
- Order toggle: Descending / Ascending

Table:
- Columns: Symbol, Open, High, Low, Close, Volume
- Prices formatted with thousands separator (e.g. 24,050)
- Volume formatted with thousands separator

## Error Handling
- If no CSV files exist for a domain, show `st.info("No data available yet. Run main.py first.")`

## Dependencies to Add
```
streamlit>=1.35.0
```
(pandas already in requirements.txt from stock scraper work)
