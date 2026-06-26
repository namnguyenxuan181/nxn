import json
from unittest.mock import patch

from news.model import NewsArticle
from stock.model import StockPrice


def _stock(symbol: str, close: int) -> StockPrice:
    return StockPrice(date="2026-06-25", symbol=symbol, open=close, high=close, low=close, close=close, volume=100000)


def _prev_stock(symbol: str, close: int) -> StockPrice:
    return StockPrice(date="2026-06-24", symbol=symbol, open=close, high=close, low=close, close=close, volume=80000)


def _news(title: str, sentiment: str = "positive") -> NewsArticle:
    return NewsArticle(
        source="VnExpress", title=title, url="http://x.com",
        published_at="2026-06-25T10:00:00", description=title, sentiment=sentiment,
    )


def test_screen_stocks_no_llm(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("ai_platform.llm._ollama_running", return_value=False):
        from ai_platform.screener import screen_stocks
        result = screen_stocks("cổ phiếu tăng 3%")
    assert "error" in result


def test_screen_stocks_invalid_json_from_llm(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("ai_platform.screener.complete", return_value="not json at all"):
        from ai_platform.screener import screen_stocks
        result = screen_stocks("gibberish")
    assert result == {"error": "Could not parse query"}


def test_screen_stocks_filters_by_min_change(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    spec = {"price_change_pct_min": 3.0, "price_change_pct_max": None, "sentiment": None, "min_volume": None}
    with patch("ai_platform.screener.complete", return_value=json.dumps(spec)), \
         patch("ai_platform.screener.get_all_symbols", return_value=["TCB", "VCB"]), \
         patch("ai_platform.screener.get_latest_stock", return_value={"TCB": _stock("TCB", 31500), "VCB": _stock("VCB", 80000)}), \
         patch("ai_platform.screener.get_previous_stock", return_value={"TCB": _prev_stock("TCB", 30000), "VCB": _prev_stock("VCB", 79000)}), \
         patch("ai_platform.screener.get_recent_news", return_value=[]):
        from ai_platform.screener import screen_stocks
        result = screen_stocks("tăng hơn 3%")
    symbols = [r["symbol"] for r in result["results"]]
    assert "TCB" in symbols    # (31500-30000)/30000*100 = 5%
    assert "VCB" not in symbols  # (80000-79000)/79000*100 ≈ 1.27%


def test_screen_stocks_filters_by_sentiment(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    spec = {"price_change_pct_min": None, "price_change_pct_max": None, "sentiment": "positive", "min_volume": None}
    with patch("ai_platform.screener.complete", return_value=json.dumps(spec)), \
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
    with patch("ai_platform.screener.complete", return_value="not json"):
        from fastapi.testclient import TestClient
        from ai_platform.main import app
        client = TestClient(app)
        resp = client.post("/api/screen", json={"query": "????"})
    assert resp.status_code == 400


def test_screen_endpoint_returns_results(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    spec = {"price_change_pct_min": None, "price_change_pct_max": None, "sentiment": None, "min_volume": None}
    with patch("ai_platform.screener.complete", return_value=json.dumps(spec)), \
         patch("ai_platform.screener.get_all_symbols", return_value=["TCB"]), \
         patch("ai_platform.screener.get_latest_stock", return_value={"TCB": _stock("TCB", 31500)}), \
         patch("ai_platform.screener.get_previous_stock", return_value={}), \
         patch("ai_platform.screener.get_recent_news", return_value=[]):
        from fastapi.testclient import TestClient
        from ai_platform.main import app
        client = TestClient(app)
        resp = client.post("/api/screen", json={"query": "tất cả cổ phiếu"})
    assert resp.status_code == 200
    data = resp.json()
    assert "filter" in data
    assert "results" in data
