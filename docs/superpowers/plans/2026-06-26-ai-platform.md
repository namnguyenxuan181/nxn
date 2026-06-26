# AI Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI + vanilla-HTML AI platform with Chat/Q&A, Analysis Report, and Stock Screener features, reading data from the existing NXN `data/` CSV/JSON files.

**Architecture:** A new `ai_platform/` package in the NXN repo. FastAPI serves both a REST API and a single `static/index.html` page. All AI calls use `claude-haiku-4-5-20251001`. Data is read from `data/stock/*.csv`, `data/news/*.json`, and `data/interest/*.csv` via a shared `data_access.py` layer.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, anthropic SDK (already installed), Bootstrap 5 (CDN), vanilla JS with SSE for streaming.

## Global Constraints

- AI model: `claude-haiku-4-5-20251001` — exact string, no substitutions
- API key env var: `ANTHROPIC_API_KEY` — all AI endpoints return an error message (not HTTP 503) if absent
- Data dir env var: `DATA_DIR` — defaults to `./data` (relative to CWD, not to the module)
- App port: **8000** (`uvicorn ai_platform.main:app --reload --port 8000`)
- No new scraping — reads only from files the NXN scraper already writes
- Domain models imported directly: `stock.model.StockPrice`, `news.model.NewsArticle`, `interest.model.InterestRate`
- No npm, no build step — single `index.html` with Bootstrap 5 from CDN
- `fastapi` and `uvicorn[standard]` added to `requirements.txt`
- All functions in `data_access.py` return empty list/dict on missing file — never raise

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `requirements.txt` | Modify | Add `fastapi`, `uvicorn[standard]` |
| `ai_platform/__init__.py` | Create | Package marker |
| `ai_platform/data_access.py` | Create | Pure functions reading NXN CSV/JSON |
| `ai_platform/chat.py` | Create | RAG chat handler + symbol extractor |
| `ai_platform/report.py` | Create | Analysis report generator |
| `ai_platform/screener.py` | Create | NL → filter → matching symbols |
| `ai_platform/main.py` | Create | FastAPI app, routes, static serving |
| `ai_platform/static/index.html` | Create | Single-page UI, 3 tabs |
| `tests/ai_platform/__init__.py` | Create | Package marker |
| `tests/ai_platform/test_data_access.py` | Create | Unit tests with tmp_path |
| `tests/ai_platform/test_chat.py` | Create | Mocked chat tests |
| `tests/ai_platform/test_report.py` | Create | Mocked report tests |
| `tests/ai_platform/test_screener.py` | Create | Mocked screener tests |

---

## Task 1: Scaffolding + Data Access Layer

**Files:**
- Create: `ai_platform/__init__.py`
- Create: `ai_platform/data_access.py`
- Create: `tests/ai_platform/__init__.py`
- Create: `tests/ai_platform/test_data_access.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces:
  - `get_all_symbols() -> list[str]`
  - `get_latest_stock(symbols: list[str]) -> dict[str, StockPrice]`
  - `get_previous_stock(symbols: list[str]) -> dict[str, StockPrice]`
  - `get_stock_history(symbol: str, days: int = 10) -> list[StockPrice]`
  - `get_recent_news(symbols: list[str], days: int = 7) -> list[NewsArticle]`
  - `get_interest_rates() -> list[InterestRate]`

- [ ] **Step 1: Add dependencies to requirements.txt**

```
fastapi
uvicorn[standard]
```

Append those two lines to `requirements.txt`, then run:
```bash
pip install fastapi "uvicorn[standard]"
```
Expected: no errors.

- [ ] **Step 2: Create package markers**

`ai_platform/__init__.py` — empty file.
`tests/ai_platform/__init__.py` — empty file.

- [ ] **Step 3: Write failing tests**

Create `tests/ai_platform/test_data_access.py`:

```python
import csv
import json
from datetime import date
from pathlib import Path

import pytest


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    (tmp_path / "stock").mkdir()
    (tmp_path / "news").mkdir()
    (tmp_path / "interest").mkdir()
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return tmp_path


def _write_stock(directory: Path, date_str: str, rows: list[dict]):
    path = directory / f"stock_{date_str}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date","symbol","open","high","low","close","volume"])
        w.writeheader()
        w.writerows(rows)


def _write_news(directory: Path, date_str: str, articles: list[dict]):
    (directory / f"news_{date_str}.json").write_text(json.dumps(articles), encoding="utf-8")


def _write_interest(directory: Path, date_str: str, rows: list[dict]):
    path = directory / f"interest_{date_str}.csv"
    fields = ["date","bank","channel","rate_1m","rate_3m","rate_6m","rate_12m","rate_18m","rate_24m","rate_36m"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def test_get_all_symbols_returns_sorted(data_dir):
    _write_stock(data_dir / "stock", "2026-06-25", [
        {"date":"2026-06-25","symbol":"VCB","open":80000,"high":81000,"low":79000,"close":80500,"volume":1000000},
        {"date":"2026-06-25","symbol":"TCB","open":31000,"high":32000,"low":30000,"close":31500,"volume":500000},
    ])
    from ai_platform.data_access import get_all_symbols
    assert get_all_symbols() == ["TCB", "VCB"]


def test_get_all_symbols_empty_when_no_file(data_dir):
    from ai_platform.data_access import get_all_symbols
    assert get_all_symbols() == []


def test_get_latest_stock_filters_by_symbol(data_dir):
    _write_stock(data_dir / "stock", "2026-06-25", [
        {"date":"2026-06-25","symbol":"TCB","open":31000,"high":32000,"low":30000,"close":31500,"volume":500000},
        {"date":"2026-06-25","symbol":"VCB","open":80000,"high":81000,"low":79000,"close":80500,"volume":1000000},
    ])
    from ai_platform.data_access import get_latest_stock
    result = get_latest_stock(["TCB"])
    assert "TCB" in result
    assert result["TCB"].close == 31500
    assert "VCB" not in result


def test_get_previous_stock_reads_second_csv(data_dir):
    _write_stock(data_dir / "stock", "2026-06-24", [
        {"date":"2026-06-24","symbol":"TCB","open":30000,"high":31000,"low":29000,"close":30500,"volume":400000},
    ])
    _write_stock(data_dir / "stock", "2026-06-25", [
        {"date":"2026-06-25","symbol":"TCB","open":31000,"high":32000,"low":30000,"close":31500,"volume":500000},
    ])
    from ai_platform.data_access import get_previous_stock
    result = get_previous_stock(["TCB"])
    assert result["TCB"].close == 30500


def test_get_previous_stock_empty_when_only_one_csv(data_dir):
    _write_stock(data_dir / "stock", "2026-06-25", [
        {"date":"2026-06-25","symbol":"TCB","open":31000,"high":32000,"low":30000,"close":31500,"volume":500000},
    ])
    from ai_platform.data_access import get_previous_stock
    assert get_previous_stock(["TCB"]) == {}


def test_get_stock_history_ordered_oldest_first(data_dir):
    _write_stock(data_dir / "stock", "2026-06-24", [
        {"date":"2026-06-24","symbol":"TCB","open":30000,"high":31000,"low":29000,"close":30500,"volume":400000},
    ])
    _write_stock(data_dir / "stock", "2026-06-25", [
        {"date":"2026-06-25","symbol":"TCB","open":31000,"high":32000,"low":30000,"close":31500,"volume":500000},
    ])
    from ai_platform.data_access import get_stock_history
    result = get_stock_history("TCB", days=10)
    assert len(result) == 2
    assert result[0].date == "2026-06-24"
    assert result[1].date == "2026-06-25"


def test_get_stock_history_empty_for_unknown_symbol(data_dir):
    _write_stock(data_dir / "stock", "2026-06-25", [
        {"date":"2026-06-25","symbol":"TCB","open":31000,"high":32000,"low":30000,"close":31500,"volume":500000},
    ])
    from ai_platform.data_access import get_stock_history
    assert get_stock_history("UNKNOWN", days=10) == []


def test_get_recent_news_filters_by_symbol(data_dir):
    today = date.today().strftime("%Y-%m-%d")
    _write_news(data_dir / "news", today, [
        {"source":"VnExpress","title":"TCB tăng mạnh","url":"http://a.com","published_at":"2026-06-25T10:00:00+07:00","description":"Techcombank","summary":"","sentiment":"positive"},
        {"source":"CafeF","title":"VN-Index hôm nay","url":"http://b.com","published_at":"2026-06-25T11:00:00+07:00","description":"Thị trường","summary":"","sentiment":"neutral"},
    ])
    from ai_platform.data_access import get_recent_news
    result = get_recent_news(["TCB"], days=1)
    assert len(result) == 1
    assert result[0].title == "TCB tăng mạnh"


def test_get_recent_news_returns_all_when_no_symbols(data_dir):
    today = date.today().strftime("%Y-%m-%d")
    _write_news(data_dir / "news", today, [
        {"source":"VnExpress","title":"Tin 1","url":"http://a.com","published_at":"2026-06-25T10:00:00","description":"","summary":"","sentiment":"neutral"},
        {"source":"CafeF","title":"Tin 2","url":"http://b.com","published_at":"2026-06-25T11:00:00","description":"","summary":"","sentiment":"neutral"},
    ])
    from ai_platform.data_access import get_recent_news
    assert len(get_recent_news([], days=1)) == 2


def test_get_interest_rates_parses_csv(data_dir):
    _write_interest(data_dir / "interest", "2026-06-25", [
        {"date":"2026-06-25","bank":"Techcombank","channel":"online","rate_1m":"3.5","rate_3m":"4.0","rate_6m":"5.0","rate_12m":"6.0","rate_18m":"","rate_24m":"6.5","rate_36m":""},
    ])
    from ai_platform.data_access import get_interest_rates
    result = get_interest_rates()
    assert len(result) == 1
    assert result[0].bank == "Techcombank"
    assert result[0].rate_3m == 4.0
    assert result[0].rate_18m is None


def test_get_interest_rates_empty_when_no_file(data_dir):
    from ai_platform.data_access import get_interest_rates
    assert get_interest_rates() == []
```

- [ ] **Step 4: Run tests — verify they fail**

```bash
pytest tests/ai_platform/test_data_access.py -v
```
Expected: `ModuleNotFoundError: No module named 'ai_platform'`

- [ ] **Step 5: Implement data_access.py**

Create `ai_platform/data_access.py`:

```python
import csv
import glob
import json
import os
from datetime import date, timedelta

from interest.model import InterestRate
from news.model import NewsArticle
from stock.model import StockPrice


def _data_dir() -> str:
    return os.environ.get("DATA_DIR", "./data")


def _int_or_none(val: str) -> int | None:
    return int(val) if val and val.strip() else None


def _float_or_none(val: str) -> float | None:
    return float(val) if val and val.strip() else None


def _read_stock_csv(path: str) -> list[StockPrice]:
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


def _sorted_stock_csvs() -> list[str]:
    pattern = os.path.join(_data_dir(), "stock", "stock_*.csv")
    return sorted(glob.glob(pattern), reverse=True)


def _get_stock_by_index(index: int, symbols: list[str]) -> dict[str, StockPrice]:
    files = _sorted_stock_csvs()
    if len(files) <= index:
        return {}
    sym_set = set(symbols)
    result = {}
    for row in _read_stock_csv(files[index]):
        if not sym_set or row.symbol in sym_set:
            result[row.symbol] = row
    return result


def get_all_symbols() -> list[str]:
    files = _sorted_stock_csvs()
    if not files:
        return []
    return sorted({row.symbol for row in _read_stock_csv(files[0])})


def get_latest_stock(symbols: list[str]) -> dict[str, StockPrice]:
    return _get_stock_by_index(0, symbols)


def get_previous_stock(symbols: list[str]) -> dict[str, StockPrice]:
    return _get_stock_by_index(1, symbols)


def get_stock_history(symbol: str, days: int = 10) -> list[StockPrice]:
    files = _sorted_stock_csvs()[:days]
    result = []
    for path in reversed(files):
        for row in _read_stock_csv(path):
            if row.symbol == symbol:
                result.append(row)
                break
    return result


def get_recent_news(symbols: list[str], days: int = 7) -> list[NewsArticle]:
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


def get_interest_rates() -> list[InterestRate]:
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
```

No extra imports needed — `open()` is used throughout, consistent with the other functions.

- [ ] **Step 6: Run tests — verify they pass**

```bash
pytest tests/ai_platform/test_data_access.py -v
```
Expected: all 10 tests PASS.

- [ ] **Step 7: Run full suite — verify no regressions**

```bash
pytest --tb=short -q
```
Expected: all existing tests still pass.

- [ ] **Step 8: Commit**

```bash
git add ai_platform/__init__.py ai_platform/data_access.py tests/ai_platform/__init__.py tests/ai_platform/test_data_access.py requirements.txt
git commit -m "feat: add ai_platform package scaffold and data access layer"
```

---

## Task 2: Chat Handler + Initial FastAPI App

**Files:**
- Create: `ai_platform/chat.py`
- Create: `ai_platform/main.py`
- Create: `tests/ai_platform/test_chat.py`

**Interfaces:**
- Consumes: `get_all_symbols()`, `get_stock_history()`, `get_recent_news()` from `ai_platform.data_access`
- Produces:
  - `extract_symbols(message: str, known_symbols: list[str]) -> list[str]`
  - `stream_chat(message: str, history: list[dict]) -> Generator[str, None, None]`
  - FastAPI app at `ai_platform.main:app`
  - `GET /api/symbols` → `list[str]`
  - `POST /api/chat` → SSE stream (`text/event-stream`)

- [ ] **Step 1: Write failing tests**

Create `tests/ai_platform/test_chat.py`:

```python
from unittest.mock import MagicMock, patch

import pytest


def test_extract_symbols_finds_match():
    from ai_platform.chat import extract_symbols
    assert extract_symbols("Cổ phiếu TCB hôm nay?", ["TCB", "VCB"]) == ["TCB"]


def test_extract_symbols_case_insensitive():
    from ai_platform.chat import extract_symbols
    assert extract_symbols("tcb tăng mạnh", ["TCB", "VCB"]) == ["TCB"]


def test_extract_symbols_multiple():
    from ai_platform.chat import extract_symbols
    result = extract_symbols("So sánh TCB và VCB", ["TCB", "VCB", "HPG"])
    assert set(result) == {"TCB", "VCB"}


def test_extract_symbols_no_match():
    from ai_platform.chat import extract_symbols
    assert extract_symbols("Thị trường hôm nay?", ["TCB", "VCB"]) == []


def test_stream_chat_no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from ai_platform.chat import stream_chat
    chunks = list(stream_chat("Hỏi gì đó", []))
    assert any("ANTHROPIC_API_KEY" in c for c in chunks)


def test_stream_chat_calls_claude_and_streams(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_stream_ctx.text_stream = iter(["TCB ", "đang tăng"])

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream_ctx

    with patch("ai_platform.chat._CLIENT", mock_client), \
         patch("ai_platform.chat.get_all_symbols", return_value=["TCB"]), \
         patch("ai_platform.chat.get_stock_history", return_value=[]), \
         patch("ai_platform.chat.get_recent_news", return_value=[]):
        from ai_platform.chat import stream_chat
        chunks = list(stream_chat("TCB hôm nay?", []))

    assert mock_client.messages.stream.called
    assert "TCB " in chunks
    assert "đang tăng" in chunks


def test_symbols_endpoint():
    from fastapi.testclient import TestClient
    from ai_platform.main import app
    with patch("ai_platform.main.get_all_symbols", return_value=["HPG", "TCB", "VCB"]):
        client = TestClient(app)
        resp = client.get("/api/symbols")
    assert resp.status_code == 200
    assert resp.json() == ["HPG", "TCB", "VCB"]


def test_chat_endpoint_streams_sse():
    from fastapi.testclient import TestClient
    from ai_platform.main import app

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_stream_ctx.text_stream = iter(["Xin chào"])

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream_ctx

    with patch("ai_platform.chat._CLIENT", mock_client), \
         patch("ai_platform.chat.get_all_symbols", return_value=[]), \
         patch("ai_platform.chat.get_recent_news", return_value=[]):
        import os
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        client = TestClient(app)
        resp = client.post("/api/chat", json={"message": "Xin chào", "history": []})

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "Xin chào" in resp.text
    assert "[DONE]" in resp.text
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/ai_platform/test_chat.py -v
```
Expected: `ModuleNotFoundError: No module named 'ai_platform.chat'`

- [ ] **Step 3: Implement chat.py**

Create `ai_platform/chat.py`:

```python
import os
import re
from typing import Generator

import anthropic

from ai_platform.data_access import get_all_symbols, get_recent_news, get_stock_history
from news.model import NewsArticle
from stock.model import StockPrice

_CLIENT = anthropic.Anthropic()

_SYSTEM = (
    "Bạn là trợ lý phân tích thị trường chứng khoán Việt Nam. "
    "Trả lời bằng tiếng Việt, ngắn gọn và chính xác. "
    "Dựa vào dữ liệu được cung cấp."
)

_known_symbols: list[str] = []


def _ensure_symbols() -> list[str]:
    global _known_symbols
    if not _known_symbols:
        _known_symbols = get_all_symbols()
    return _known_symbols


def extract_symbols(message: str, known_symbols: list[str]) -> list[str]:
    upper = message.upper()
    return [s for s in known_symbols if re.search(r"\b" + re.escape(s) + r"\b", upper)]


def _build_context(symbols: list[str]) -> str:
    parts: list[str] = []
    if symbols:
        parts.append("=== Giá cổ phiếu ===")
        for sym in symbols:
            history = get_stock_history(sym, days=5)
            if history:
                lines: list[str] = []
                prev: int | None = None
                for row in history:
                    if row.close and prev:
                        pct = (row.close - prev) / prev * 100
                        lines.append(f"{row.date} close={row.close:,} ({pct:+.1f}%)")
                    elif row.close:
                        lines.append(f"{row.date} close={row.close:,}")
                    prev = row.close
                parts.append(f"{sym}: " + " | ".join(lines))
        news = get_recent_news(symbols, days=3)
    else:
        news = get_recent_news([], days=1)

    if news:
        parts.append("\n=== Tin tức liên quan ===")
        for article in news[:10]:
            parts.append(f"[{article.source} {article.published_at[:10]}] {article.title}")

    return "\n".join(parts)


def stream_chat(message: str, history: list[dict]) -> Generator[str, None, None]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        yield "Lỗi: ANTHROPIC_API_KEY chưa được cấu hình."
        return

    symbols = extract_symbols(message, _ensure_symbols())
    context = _build_context(symbols)
    messages = list(history[-10:])
    user_content = (context + "\n\nCâu hỏi: " + message) if context else message
    messages.append({"role": "user", "content": user_content})

    with _CLIENT.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=_SYSTEM,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
```

- [ ] **Step 4: Implement main.py (initial — chat + symbols only)**

Create `ai_platform/main.py`:

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from ai_platform.chat import stream_chat
from ai_platform.data_access import get_all_symbols

app = FastAPI(title="NXN AI Platform")

_STATIC = Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.get("/api/symbols")
def symbols():
    return get_all_symbols()


@app.post("/api/chat")
def chat(req: ChatRequest):
    def generate():
        for chunk in stream_chat(req.message, req.history):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
def index():
    path = _STATIC / "index.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "<h1>NXN AI Platform — frontend not yet built</h1>"
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest tests/ai_platform/test_chat.py -v
```
Expected: all 7 tests PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest --tb=short -q
```
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add ai_platform/chat.py ai_platform/main.py tests/ai_platform/test_chat.py
git commit -m "feat: add chat handler and initial FastAPI app with /api/chat and /api/symbols"
```

---

## Task 3: Analysis Report Handler + Endpoint

**Files:**
- Create: `ai_platform/report.py`
- Modify: `ai_platform/main.py`
- Create: `tests/ai_platform/test_report.py`

**Interfaces:**
- Consumes: `get_stock_history()`, `get_recent_news()`, `get_interest_rates()` from `ai_platform.data_access`
- Produces:
  - `generate_report(symbol: str) -> dict | None` — returns `None` when symbol has no data (caller raises 404)
  - `GET /api/report/{symbol}` → `{"symbol", "report", "generated_at"}` or HTTP 404

- [ ] **Step 1: Write failing tests**

Create `tests/ai_platform/test_report.py`:

```python
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from stock.model import StockPrice
from interest.model import InterestRate


def _make_stock(date_str: str, close: int) -> StockPrice:
    return StockPrice(date=date_str, symbol="TCB", open=close-500, high=close+500, low=close-500, close=close, volume=500000)


def test_generate_report_returns_none_for_unknown_symbol(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("ai_platform.report.get_stock_history", return_value=[]):
        from ai_platform.report import generate_report
        assert generate_report("UNKNOWN") is None


def test_generate_report_returns_dict_with_expected_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Báo cáo TCB: tăng tốt.")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("ai_platform.report._CLIENT", mock_client), \
         patch("ai_platform.report.get_stock_history", return_value=[_make_stock("2026-06-25", 31500)]), \
         patch("ai_platform.report.get_recent_news", return_value=[]), \
         patch("ai_platform.report.get_interest_rates", return_value=[]):
        from ai_platform.report import generate_report
        result = generate_report("TCB")

    assert result is not None
    assert result["symbol"] == "TCB"
    assert result["report"] == "Báo cáo TCB: tăng tốt."
    assert "generated_at" in result


def test_generate_report_no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("ai_platform.report.get_stock_history", return_value=[_make_stock("2026-06-25", 31500)]):
        from ai_platform.report import generate_report
        result = generate_report("TCB")
    assert "error" in result


def test_report_endpoint_404_for_unknown():
    from ai_platform.main import app
    client = TestClient(app)
    with patch("ai_platform.report.get_stock_history", return_value=[]):
        resp = client.get("/api/report/UNKNOWN")
    assert resp.status_code == 404


def test_report_endpoint_returns_report():
    from ai_platform.main import app
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test-key"

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Báo cáo.")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("ai_platform.report._CLIENT", mock_client), \
         patch("ai_platform.report.get_stock_history", return_value=[_make_stock("2026-06-25", 31500)]), \
         patch("ai_platform.report.get_recent_news", return_value=[]), \
         patch("ai_platform.report.get_interest_rates", return_value=[]):
        client = TestClient(app)
        resp = client.get("/api/report/TCB")

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "TCB"
    assert data["report"] == "Báo cáo."
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/ai_platform/test_report.py -v
```
Expected: `ModuleNotFoundError: No module named 'ai_platform.report'`

- [ ] **Step 3: Implement report.py**

Create `ai_platform/report.py`:

```python
import os
from datetime import datetime

import anthropic

from ai_platform.data_access import get_interest_rates, get_recent_news, get_stock_history

_CLIENT = anthropic.Anthropic()


def _build_context(symbol: str) -> str:
    parts: list[str] = []

    history = get_stock_history(symbol, days=10)
    if history:
        parts.append(f"=== Giá cổ phiếu {symbol} (10 ngày) ===")
        prev: int | None = None
        for row in history:
            if row.close and prev:
                pct = (row.close - prev) / prev * 100
                parts.append(
                    f"{row.date}: open={row.open:,} high={row.high:,} low={row.low:,} "
                    f"close={row.close:,} vol={row.volume:,} ({pct:+.1f}%)"
                )
            elif row.close:
                parts.append(
                    f"{row.date}: open={row.open:,} high={row.high:,} low={row.low:,} "
                    f"close={row.close:,} vol={row.volume:,}"
                )
            prev = row.close

    news = get_recent_news([symbol], days=7)
    if news:
        parts.append(f"\n=== Tin tức về {symbol} (7 ngày) ===")
        labels = {"positive": "tích cực", "negative": "tiêu cực"}
        for article in news[:15]:
            label = labels.get(article.sentiment, "trung lập")
            parts.append(f"[{article.source} {article.published_at[:10]}] [{label}] {article.title}")

    rates = get_interest_rates()
    if rates:
        parts.append("\n=== Lãi suất ngân hàng (mới nhất) ===")
        for r in rates[:4]:
            parts.append(f"{r.bank} ({r.channel}): 3m={r.rate_3m}% 6m={r.rate_6m}% 12m={r.rate_12m}%")

    return "\n".join(parts)


def generate_report(symbol: str) -> dict | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {"error": "ANTHROPIC_API_KEY not configured", "symbol": symbol}

    history = get_stock_history(symbol, days=10)
    if not history:
        return None

    context = _build_context(symbol)
    prompt = (
        f"Phân tích cổ phiếu {symbol} dựa trên dữ liệu sau:\n\n{context}\n\n"
        "Viết báo cáo phân tích ngắn gồm:\n"
        "1. Xu hướng giá (10 ngày gần nhất)\n"
        "2. Tóm tắt tin tức và cảm xúc thị trường\n"
        "3. Rủi ro chính cần lưu ý\n"
        "4. Nhận định ngắn (1-2 câu)\n\n"
        "Trả lời bằng tiếng Việt, súc tích."
    )

    response = _CLIENT.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return {
        "symbol": symbol,
        "report": response.content[0].text,
        "generated_at": datetime.utcnow().isoformat(),
    }
```

- [ ] **Step 4: Wire /api/report/{symbol} into main.py**

Add to `ai_platform/main.py` (after the existing imports and before the `index` route):

```python
from fastapi import HTTPException
from ai_platform.report import generate_report

@app.get("/api/report/{symbol}")
def report(symbol: str):
    result = generate_report(symbol.upper())
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data available for {symbol.upper()}")
    return result
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest tests/ai_platform/test_report.py -v
```
Expected: all 5 tests PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest --tb=short -q
```
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add ai_platform/report.py ai_platform/main.py tests/ai_platform/test_report.py
git commit -m "feat: add analysis report handler and GET /api/report/{symbol} endpoint"
```

---

## Task 4: Stock Screener Handler + Endpoint

**Files:**
- Create: `ai_platform/screener.py`
- Modify: `ai_platform/main.py`
- Create: `tests/ai_platform/test_screener.py`

**Interfaces:**
- Consumes: `get_all_symbols()`, `get_latest_stock()`, `get_previous_stock()`, `get_recent_news()` from `ai_platform.data_access`
- Produces:
  - `screen_stocks(query: str) -> dict` — returns `{"filter": {...}, "results": [...]}` or `{"error": "..."}`
  - `POST /api/screen` → same shape, HTTP 400 on unparseable query

- [ ] **Step 1: Write failing tests**

Create `tests/ai_platform/test_screener.py`:

```python
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from stock.model import StockPrice
from news.model import NewsArticle


def _stock(symbol: str, close: int) -> StockPrice:
    return StockPrice(date="2026-06-25", symbol=symbol, open=close, high=close, low=close, close=close, volume=100000)


def _prev_stock(symbol: str, close: int) -> StockPrice:
    return StockPrice(date="2026-06-24", symbol=symbol, open=close, high=close, low=close, close=close, volume=80000)


def _news(title: str, sentiment: str = "positive") -> NewsArticle:
    return NewsArticle(source="VnExpress", title=title, url="http://x.com", published_at="2026-06-25T10:00:00", description=title, sentiment=sentiment)


def _mock_client_filter(spec: dict) -> MagicMock:
    import json
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps(spec))]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_resp
    return mock_client


def test_screen_stocks_no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from ai_platform.screener import screen_stocks
    result = screen_stocks("cổ phiếu tăng 3%")
    assert "error" in result


def test_screen_stocks_invalid_json_from_claude(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="not json at all")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_resp
    with patch("ai_platform.screener._CLIENT", mock_client):
        from ai_platform.screener import screen_stocks
        result = screen_stocks("gibberish query")
    assert result == {"error": "Could not parse query"}


def test_screen_stocks_filters_by_min_change(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_client = _mock_client_filter({"price_change_pct_min": 3.0, "price_change_pct_max": None, "sentiment": None, "min_volume": None})
    with patch("ai_platform.screener._CLIENT", mock_client), \
         patch("ai_platform.screener.get_all_symbols", return_value=["TCB", "VCB"]), \
         patch("ai_platform.screener.get_latest_stock", return_value={"TCB": _stock("TCB", 31500), "VCB": _stock("VCB", 80000)}), \
         patch("ai_platform.screener.get_previous_stock", return_value={"TCB": _prev_stock("TCB", 30000), "VCB": _prev_stock("VCB", 79000)}), \
         patch("ai_platform.screener.get_recent_news", return_value=[]):
        from ai_platform.screener import screen_stocks
        result = screen_stocks("tăng hơn 3%")

    symbols = [r["symbol"] for r in result["results"]]
    assert "TCB" in symbols   # 31500/30000 - 1 = 5%
    assert "VCB" not in symbols  # 80000/79000 - 1 = 1.27%


def test_screen_stocks_filters_by_sentiment(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_client = _mock_client_filter({"price_change_pct_min": None, "price_change_pct_max": None, "sentiment": "positive", "min_volume": None})
    with patch("ai_platform.screener._CLIENT", mock_client), \
         patch("ai_platform.screener.get_all_symbols", return_value=["TCB", "VCB"]), \
         patch("ai_platform.screener.get_latest_stock", return_value={"TCB": _stock("TCB", 31500), "VCB": _stock("VCB", 80000)}), \
         patch("ai_platform.screener.get_previous_stock", return_value={}), \
         patch("ai_platform.screener.get_recent_news", return_value=[_news("TCB tăng mạnh", "positive")]):
        from ai_platform.screener import screen_stocks
        result = screen_stocks("có tin tích cực")

    symbols = [r["symbol"] for r in result["results"]]
    assert "TCB" in symbols
    assert "VCB" not in symbols


def test_screen_endpoint_returns_400_on_unparseable(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="not json")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_resp
    with patch("ai_platform.screener._CLIENT", mock_client):
        from ai_platform.main import app
        client = TestClient(app)
        resp = client.post("/api/screen", json={"query": "????"})
    assert resp.status_code == 400


def test_screen_endpoint_returns_results(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_client = _mock_client_filter({"price_change_pct_min": None, "price_change_pct_max": None, "sentiment": None, "min_volume": None})
    with patch("ai_platform.screener._CLIENT", mock_client), \
         patch("ai_platform.screener.get_all_symbols", return_value=["TCB"]), \
         patch("ai_platform.screener.get_latest_stock", return_value={"TCB": _stock("TCB", 31500)}), \
         patch("ai_platform.screener.get_previous_stock", return_value={}), \
         patch("ai_platform.screener.get_recent_news", return_value=[]):
        from ai_platform.main import app
        client = TestClient(app)
        resp = client.post("/api/screen", json={"query": "tất cả cổ phiếu"})
    assert resp.status_code == 200
    data = resp.json()
    assert "filter" in data
    assert "results" in data
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/ai_platform/test_screener.py -v
```
Expected: `ModuleNotFoundError: No module named 'ai_platform.screener'`

- [ ] **Step 3: Implement screener.py**

Create `ai_platform/screener.py`:

```python
import json
import os
import re

import anthropic

from ai_platform.data_access import (
    get_all_symbols,
    get_latest_stock,
    get_previous_stock,
    get_recent_news,
)

_CLIENT = anthropic.Anthropic()

_FILTER_PROMPT = (
    'Convert this Vietnamese stock screening query to a JSON filter spec.\n'
    'Query: "{query}"\n\n'
    "Respond with JSON only, using these optional fields:\n"
    '{{\n'
    '  "price_change_pct_min": <float or null>,\n'
    '  "price_change_pct_max": <float or null>,\n'
    '  "sentiment": <"positive"|"negative"|"neutral"|null>,\n'
    '  "min_volume": <int or null>\n'
    '}}'
)


def _parse_filter(query: str) -> dict | None:
    response = _CLIENT.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": _FILTER_PROMPT.format(query=query)}],
    )
    text = response.content[0].text.strip()
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def screen_stocks(query: str) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {"error": "ANTHROPIC_API_KEY not configured"}

    spec = _parse_filter(query)
    if spec is None:
        return {"error": "Could not parse query"}

    symbols = get_all_symbols()
    if not symbols:
        return {"filter": spec, "results": []}

    latest = get_latest_stock(symbols)
    previous = get_previous_stock(symbols)
    news = get_recent_news([], days=1)

    news_sentiment: dict[str, str] = {}
    news_headline: dict[str, str] = {}
    for article in news:
        for sym in symbols:
            if sym in article.title.upper() or sym in article.description.upper():
                if sym not in news_sentiment:
                    news_sentiment[sym] = article.sentiment
                    news_headline[sym] = article.title

    results = []
    for sym, stock in latest.items():
        if stock.close is None:
            continue

        change_pct: float | None = None
        prev = previous.get(sym)
        if prev and prev.close:
            change_pct = (stock.close - prev.close) / prev.close * 100

        if spec.get("price_change_pct_min") is not None:
            if change_pct is None or change_pct < spec["price_change_pct_min"]:
                continue
        if spec.get("price_change_pct_max") is not None:
            if change_pct is None or change_pct > spec["price_change_pct_max"]:
                continue
        if spec.get("sentiment") is not None:
            if news_sentiment.get(sym) != spec["sentiment"]:
                continue
        if spec.get("min_volume") is not None:
            if stock.volume is None or stock.volume < spec["min_volume"]:
                continue

        results.append({
            "symbol": sym,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "price": stock.close,
            "news_headline": news_headline.get(sym),
        })

    results.sort(
        key=lambda r: r["change_pct"] if r["change_pct"] is not None else float("-inf"),
        reverse=True,
    )
    return {"filter": spec, "results": results[:50]}
```

- [ ] **Step 4: Wire /api/screen into main.py**

Add to `ai_platform/main.py` (before the `index` route):

```python
from ai_platform.screener import screen_stocks

class ScreenRequest(BaseModel):
    query: str

@app.post("/api/screen")
def screen(req: ScreenRequest):
    result = screen_stocks(req.query)
    if result.get("error") == "Could not parse query":
        raise HTTPException(status_code=400, detail=result["error"])
    return result
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest tests/ai_platform/test_screener.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest --tb=short -q
```
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add ai_platform/screener.py ai_platform/main.py tests/ai_platform/test_screener.py
git commit -m "feat: add stock screener handler and POST /api/screen endpoint"
```

---

## Task 5: Frontend HTML + Static File Serving

**Files:**
- Create: `ai_platform/static/index.html`
- Modify: `ai_platform/main.py`

No automated tests — manual verification required.

- [ ] **Step 1: Create static directory and index.html**

```bash
mkdir -p ai_platform/static
```

Create `ai_platform/static/index.html`:

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NXN AI Platform</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    #chat-messages { height: 420px; overflow-y: auto; background: #fafafa; border-radius: 8px; padding: 12px; }
    .msg-row { display: flex; margin-bottom: 8px; }
    .msg-row.user { justify-content: flex-end; }
    .msg-row.assistant { justify-content: flex-start; }
    .bubble { max-width: 75%; padding: 8px 14px; border-radius: 16px; font-size: 0.95em; white-space: pre-wrap; word-break: break-word; }
    .bubble.user { background: #0d6efd; color: #fff; border-bottom-right-radius: 4px; }
    .bubble.assistant { background: #e9ecef; color: #212529; border-bottom-left-radius: 4px; }
  </style>
</head>
<body>
<div class="container py-4" style="max-width:900px">
  <h2 class="mb-3">🤖 NXN AI Platform</h2>
  <ul class="nav nav-tabs mb-3" id="tabs" role="tablist">
    <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#pane-chat">💬 Chat</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#pane-report">📊 Báo cáo</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#pane-screener">🔍 Screener</button></li>
  </ul>

  <div class="tab-content">

    <!-- Chat -->
    <div class="tab-pane fade show active" id="pane-chat">
      <div id="chat-messages" class="border mb-2"></div>
      <div class="input-group">
        <input id="chat-input" type="text" class="form-control" placeholder="Hỏi về cổ phiếu bằng tiếng Việt...">
        <button id="chat-send" class="btn btn-primary">Gửi</button>
        <button id="chat-clear" class="btn btn-outline-secondary">Xoá</button>
      </div>
    </div>

    <!-- Report -->
    <div class="tab-pane fade" id="pane-report">
      <div class="d-flex gap-2 mb-3">
        <input id="report-symbol" type="text" class="form-control" placeholder="Nhập mã cổ phiếu (VD: TCB)" style="max-width:240px">
        <button id="report-btn" class="btn btn-success">Phân tích</button>
      </div>
      <div id="report-spinner" class="d-none text-success mb-2">
        <div class="spinner-border spinner-border-sm"></div> Đang phân tích...
      </div>
      <div id="report-card" class="d-none card p-3">
        <div class="d-flex justify-content-between mb-2">
          <strong id="report-title"></strong>
          <small id="report-time" class="text-muted"></small>
        </div>
        <pre id="report-body" style="white-space:pre-wrap;margin:0;font-family:inherit"></pre>
      </div>
    </div>

    <!-- Screener -->
    <div class="tab-pane fade" id="pane-screener">
      <div class="d-flex gap-2 mb-3">
        <input id="screen-input" type="text" class="form-control" placeholder="VD: cổ phiếu tăng hơn 3% có tin tức tích cực">
        <button id="screen-btn" class="btn btn-warning">Lọc</button>
      </div>
      <div id="screen-spinner" class="d-none text-warning mb-2">
        <div class="spinner-border spinner-border-sm"></div> Đang lọc...
      </div>
      <div id="screen-filter-row" class="mb-2"></div>
      <div id="screen-empty" class="d-none text-muted">Không tìm thấy kết quả phù hợp.</div>
      <table class="table table-hover d-none" id="screen-table">
        <thead class="table-light">
          <tr><th>Mã</th><th>Giá (VND)</th><th>Thay đổi %</th><th>Tin tức</th></tr>
        </thead>
        <tbody id="screen-body"></tbody>
      </table>
    </div>

  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
// ── Chat ──────────────────────────────────────────────────────────────────────
const chatMsgs = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatSend = document.getElementById('chat-send');
let chatHistory = [];

function addBubble(role, text) {
  const row = document.createElement('div');
  row.className = `msg-row ${role}`;
  const bubble = document.createElement('div');
  bubble.className = `bubble ${role}`;
  bubble.textContent = text;
  row.appendChild(bubble);
  chatMsgs.appendChild(row);
  chatMsgs.scrollTop = chatMsgs.scrollHeight;
  return bubble;
}

chatSend.addEventListener('click', async () => {
  const msg = chatInput.value.trim();
  if (!msg) return;
  chatInput.value = '';
  addBubble('user', msg);
  const assistantBubble = addBubble('assistant', '…');
  chatSend.disabled = true;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, history: chatHistory }),
    });
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let full = '';
    assistantBubble.textContent = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const line of dec.decode(value).split('\n')) {
        if (!line.startsWith('data: ')) continue;
        const d = line.slice(6);
        if (d === '[DONE]') break;
        full += d;
        assistantBubble.textContent = full;
        chatMsgs.scrollTop = chatMsgs.scrollHeight;
      }
    }
    chatHistory.push({ role: 'user', content: msg }, { role: 'assistant', content: full });
    if (chatHistory.length > 10) chatHistory = chatHistory.slice(-10);
  } catch {
    assistantBubble.textContent = 'Lỗi kết nối.';
  }
  chatSend.disabled = false;
});

chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') chatSend.click(); });
document.getElementById('chat-clear').addEventListener('click', () => {
  chatMsgs.innerHTML = '';
  chatHistory = [];
});

// ── Report ────────────────────────────────────────────────────────────────────
document.getElementById('report-btn').addEventListener('click', async () => {
  const sym = document.getElementById('report-symbol').value.trim().toUpperCase();
  if (!sym) return;
  document.getElementById('report-spinner').classList.remove('d-none');
  document.getElementById('report-card').classList.add('d-none');

  try {
    const res = await fetch(`/api/report/${sym}`);
    const data = await res.json();
    if (!res.ok) { alert(data.detail || 'Lỗi'); return; }
    document.getElementById('report-title').textContent = `Báo cáo: ${data.symbol}`;
    document.getElementById('report-time').textContent =
      data.generated_at ? new Date(data.generated_at + 'Z').toLocaleString('vi-VN') : '';
    document.getElementById('report-body').textContent = data.report;
    document.getElementById('report-card').classList.remove('d-none');
  } catch { alert('Lỗi kết nối.'); }
  finally { document.getElementById('report-spinner').classList.add('d-none'); }
});

// ── Screener ──────────────────────────────────────────────────────────────────
document.getElementById('screen-btn').addEventListener('click', async () => {
  const query = document.getElementById('screen-input').value.trim();
  if (!query) return;
  document.getElementById('screen-spinner').classList.remove('d-none');
  document.getElementById('screen-table').classList.add('d-none');
  document.getElementById('screen-empty').classList.add('d-none');
  document.getElementById('screen-filter-row').innerHTML = '';

  try {
    const res = await fetch('/api/screen', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();
    if (!res.ok) { alert(data.detail || 'Không thể phân tích câu truy vấn.'); return; }

    const filterRow = document.getElementById('screen-filter-row');
    for (const [k, v] of Object.entries(data.filter || {})) {
      if (v !== null && v !== undefined) {
        const b = document.createElement('span');
        b.className = 'badge bg-secondary me-1';
        b.textContent = `${k}: ${v}`;
        filterRow.appendChild(b);
      }
    }

    const tbody = document.getElementById('screen-body');
    tbody.innerHTML = '';
    if (!data.results?.length) {
      document.getElementById('screen-empty').classList.remove('d-none');
    } else {
      for (const row of data.results) {
        const cls = row.change_pct > 0 ? 'text-success fw-bold' : row.change_pct < 0 ? 'text-danger' : '';
        const pct = row.change_pct !== null
          ? `<span class="${cls}">${row.change_pct > 0 ? '+' : ''}${row.change_pct.toFixed(2)}%</span>`
          : '-';
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${row.symbol}</strong></td>
          <td>${row.price ? row.price.toLocaleString('vi-VN') : '-'}</td>
          <td>${pct}</td>
          <td style="font-size:0.85em;color:#555">${row.news_headline || '-'}</td>`;
        tbody.appendChild(tr);
      }
      document.getElementById('screen-table').classList.remove('d-none');
    }
  } catch { alert('Lỗi kết nối.'); }
  finally { document.getElementById('screen-spinner').classList.add('d-none'); }
});
</script>
</body>
</html>
```

- [ ] **Step 2: Update main.py to serve static files properly**

The `GET /` route already serves `index.html` from `_STATIC`. Verify the route exists; if it does, no change needed. If `StaticFiles` mounting is needed for any future static assets, add it:

Final `ai_platform/main.py` should look like this (complete, replacing the existing file):

```python
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from ai_platform.chat import stream_chat
from ai_platform.data_access import get_all_symbols
from ai_platform.report import generate_report
from ai_platform.screener import screen_stocks

app = FastAPI(title="NXN AI Platform")

_STATIC = Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ScreenRequest(BaseModel):
    query: str


@app.get("/api/symbols")
def symbols():
    return get_all_symbols()


@app.post("/api/chat")
def chat(req: ChatRequest):
    def generate():
        for chunk in stream_chat(req.message, req.history):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/report/{symbol}")
def report(symbol: str):
    result = generate_report(symbol.upper())
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data available for {symbol.upper()}")
    return result


@app.post("/api/screen")
def screen(req: ScreenRequest):
    result = screen_stocks(req.query)
    if result.get("error") == "Could not parse query":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/", response_class=HTMLResponse)
def index():
    return (_STATIC / "index.html").read_text(encoding="utf-8")
```

- [ ] **Step 3: Run full test suite**

```bash
pytest --tb=short -q
```
Expected: all tests pass.

- [ ] **Step 4: Start the app and verify manually**

```bash
uvicorn ai_platform.main:app --reload --port 8000
```

Open `http://localhost:8000` in a browser. Verify:
- Three tabs render correctly (Chat, Báo cáo, Screener)
- Chat tab: type "Thị trường hôm nay thế nào?" → response streams in word-by-word
- Report tab: enter `TCB` → click Phân tích → spinner shows then report appears
- Screener tab: enter "cổ phiếu tăng hơn 2%" → click Lọc → filter badge + results table appear

- [ ] **Step 5: Commit**

```bash
git add ai_platform/static/index.html ai_platform/main.py
git commit -m "feat: add frontend HTML and complete AI platform — chat, report, screener"
```
