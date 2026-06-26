# AI Platform Design Spec

**Date:** 2026-06-26
**Features:** Chat/Q&A · AI Analysis Report · AI Stock Screener

---

## Overview

A new standalone AI platform (`ai_platform/`) inside the NXN repo. FastAPI serves a REST API and a single static HTML page. The HTML page has three tabs: **Chat**, **Report**, and **Screener**. All AI calls use `claude-haiku-4-5-20251001` via the Anthropic SDK. Data is read from the existing `data/` CSV/JSON files that the NXN scraper already writes — no new scraping.

The platform is started separately from the NXN dashboard (`python -m ai_platform.main` or `uvicorn ai_platform.main:app`), listening on port 8000.

---

## Folder Structure

```
ai_platform/
  __init__.py
  main.py          # FastAPI app: mounts API routers + serves static/index.html
  data_access.py   # reads NXN CSV/JSON files, returns domain objects
  chat.py          # RAG chat handler
  report.py        # analysis report generator
  screener.py      # NL → filter → matching symbols
  static/
    index.html     # single-page UI with 3 tabs, vanilla JS + SSE for streaming
tests/
  ai_platform/
    __init__.py
    test_data_access.py
    test_chat.py
    test_report.py
    test_screener.py
```

NXN domain models (`stock.model.StockPrice`, `news.model.NewsArticle`, `interest.model.InterestRate`) are imported directly — no duplication.

---

## Sub-project 1 — Data Access Layer

**File:** `ai_platform/data_access.py`

Five pure functions. All read from the `DATA_DIR` environment variable (defaults to `./data`).

```python
def get_all_symbols() -> list[str]:
    # reads latest stock CSV, returns sorted list of all symbols

def get_latest_stock(symbols: list[str]) -> dict[str, StockPrice]:
    # reads latest available stock CSV, returns {symbol: StockPrice} for requested symbols

def get_stock_history(symbol: str, days: int = 10) -> list[StockPrice]:
    # reads last `days` available stock CSVs, returns list sorted oldest→newest
    # skips dates where the symbol has no data

def get_recent_news(symbols: list[str], days: int = 7) -> list[NewsArticle]:
    # reads news JSON files for last `days` days
    # returns articles whose title or description contains any symbol (case-insensitive)
    # returns [] if no symbols provided (returns all recent news)

def get_interest_rates() -> list[InterestRate]:
    # reads the latest interest CSV, returns all rows
```

**Error behaviour:** if a file does not exist, the function returns an empty list/dict — never raises. Callers handle empty data gracefully.

---

## Sub-project 2 — Chat / Q&A

**File:** `ai_platform/chat.py`

**API:** `POST /api/chat`

Request body:
```json
{
  "message": "TCB hôm nay thế nào?",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

Response: Server-Sent Events stream (`text/event-stream`). Each event is `data: <chunk>\n\n`. Client appends chunks to the current assistant message. Final event: `data: [DONE]\n\n`.

**RAG flow (inside `chat.py`):**

1. **Symbol extraction** — scan `message` for known symbols (loaded once at startup via `get_all_symbols()`). Case-insensitive. Returns list of matched symbols.
2. **Context fetch** — if symbols found: `get_stock_history(sym, days=5)` for each + `get_recent_news(symbols, days=3)`. If no symbols found: `get_recent_news([], days=1)` (today's news as general context).
3. **Context string** — compact plaintext:
   ```
   === Giá cổ phiếu ===
   TCB: 2026-06-25 close=32050 (+1.2%) | 2026-06-24 close=31670 ...

   === Tin tức liên quan ===
   [VnExpress 2026-06-25] TCB tăng mạnh nhờ kết quả kinh doanh tốt
   ```
4. **Claude call** — `client.messages.stream(...)` with:
   - System: `"Bạn là trợ lý phân tích thị trường chứng khoán Việt Nam. Trả lời bằng tiếng Việt, ngắn gọn và chính xác. Dựa vào dữ liệu được cung cấp."`
   - Messages: history + `{"role": "user", "content": context_string + "\n\nCâu hỏi: " + message}`
   - Model: `claude-haiku-4-5-20251001`, `max_tokens=1024`
5. **Stream** — yield each text delta as `data: <chunk>\n\n`, then `data: [DONE]\n\n`.

**History limit:** keep last 10 messages (5 turns) to avoid token explosion.

---

## Sub-project 3 — AI Analysis Report

**File:** `ai_platform/report.py`

**API:** `GET /api/report/{symbol}`

Response: `{"symbol": "TCB", "report": "...", "generated_at": "2026-06-26T10:00:00"}`

**Flow:**

1. Fetch `get_stock_history(symbol, days=10)` — price trend data
2. Fetch `get_recent_news([symbol], days=7)` — relevant news
3. Fetch `get_interest_rates()` — macro context
4. Build context string with all three data sets
5. Call Claude (non-streaming) with prompt:

```
Phân tích cổ phiếu {symbol} dựa trên dữ liệu sau:

{context}

Viết báo cáo phân tích ngắn gồm:
1. Xu hướng giá (10 ngày gần nhất)
2. Tóm tắt tin tức và cảm xúc thị trường
3. Rủi ro chính cần lưu ý
4. Nhận định ngắn (1-2 câu)

Trả lời bằng tiếng Việt, súc tích.
```

6. Return report text + timestamp.

If symbol has no data, return `{"error": "No data available for {symbol}"}` with HTTP 404.

---

## Sub-project 4 — AI Stock Screener

**File:** `ai_platform/screener.py`

**API:** `POST /api/screen`

Request: `{"query": "cổ phiếu tăng hơn 3% hôm nay có tin tức tích cực"}`

Response:
```json
{
  "filter": {"price_change_pct_min": 3.0, "sentiment": "positive"},
  "results": [
    {"symbol": "TCB", "change_pct": 4.2, "price": 32050, "news_headline": "..."}
  ]
}
```

**Flow:**

1. **NL → filter spec** — call Claude (non-streaming) with:
```
Convert this Vietnamese stock screening query to a JSON filter spec.
Query: "{query}"

Respond with JSON only, using these optional fields:
{
  "price_change_pct_min": <float or null>,
  "price_change_pct_max": <float or null>,
  "sentiment": <"positive"|"negative"|"neutral"|null>,
  "min_volume": <int or null>
}
```

2. **Load data** — `get_latest_stock(get_all_symbols())` for all prices + yesterday's CSV for change % calculation + `get_recent_news([], days=1)` for today's news.

3. **Apply filter** — iterate all symbols:
   - `price_change_pct_min/max`: compare `(close_today - close_yesterday) / close_yesterday * 100`
   - `sentiment`: check if any today's news article for this symbol has matching sentiment field
   - `min_volume`: compare volume

4. Return up to 50 matching symbols sorted by `change_pct` descending.

If Claude returns invalid JSON, return `{"error": "Could not parse query"}` with HTTP 400.

---

## Frontend — `ai_platform/static/index.html`

Single HTML file, no build step, no npm. Uses:
- Bootstrap 5 (CDN) for layout and styling
- Vanilla JS for API calls and SSE streaming

**Three tabs:**

**Chat tab:**
- Message input + Send button
- Message history rendered as Bootstrap cards (user = right-aligned blue, assistant = left-aligned gray)
- Streams assistant responses word-by-word via SSE
- "Clear" button resets history

**Report tab:**
- Symbol text input + "Generate Report" button
- Loading spinner while waiting
- Report displayed as pre-formatted text in a card
- Shows timestamp of report

**Screener tab:**
- Natural language query input + "Screen" button
- Shows the interpreted filter spec as a badge row
- Results in a Bootstrap table: Symbol | Price | Change % | News Headline
- Max 50 rows

---

## API summary

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Serves `static/index.html` |
| `POST` | `/api/chat` | Streaming chat (SSE) |
| `GET` | `/api/report/{symbol}` | Analysis report |
| `POST` | `/api/screen` | Stock screener |
| `GET` | `/api/symbols` | List all known symbols (used by frontend autocomplete) |

---

## Environment

- `ANTHROPIC_API_KEY` — required; all three AI features return HTTP 503 if absent
- `DATA_DIR` — path to the NXN `data/` folder; defaults to `./data`
- App runs on port **8000** (`uvicorn ai_platform.main:app --reload --port 8000`)

---

## Dependencies (additions to `requirements.txt`)

```
fastapi
uvicorn[standard]
```

`anthropic` is already in `requirements.txt` from the NXN project.

---

## Testing

- **`test_data_access.py`** — unit tests with `tmp_path`: write sample CSVs/JSONs, assert each function returns correct domain objects; test missing-file returns empty
- **`test_chat.py`** — mock `anthropic.Anthropic` and `data_access` functions; assert context string is built correctly; assert symbol extraction finds known symbols
- **`test_report.py`** — mock `anthropic.Anthropic` and data functions; assert report endpoint returns 404 for unknown symbol; assert response shape
- **`test_screener.py`** — mock Claude to return a fixed filter JSON; mock data functions; assert filter logic correctly includes/excludes symbols based on price change and sentiment

No integration tests against the live Anthropic API or live market data.
