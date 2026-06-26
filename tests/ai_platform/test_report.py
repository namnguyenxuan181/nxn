import os
from unittest.mock import MagicMock, patch

from stock.model import StockPrice


def _make_stock(date_str: str, close: int) -> StockPrice:
    return StockPrice(date=date_str, symbol="TCB", open=close - 500, high=close + 500, low=close - 500, close=close, volume=500000)


def test_generate_report_returns_none_for_unknown_symbol():
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
    from fastapi.testclient import TestClient
    from ai_platform.main import app
    with patch("ai_platform.report.get_stock_history", return_value=[]):
        client = TestClient(app)
        resp = client.get("/api/report/UNKNOWN")
    assert resp.status_code == 404


def test_report_endpoint_returns_report(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Báo cáo.")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("ai_platform.report._CLIENT", mock_client), \
         patch("ai_platform.report.get_stock_history", return_value=[_make_stock("2026-06-25", 31500)]), \
         patch("ai_platform.report.get_recent_news", return_value=[]), \
         patch("ai_platform.report.get_interest_rates", return_value=[]):
        from fastapi.testclient import TestClient
        from ai_platform.main import app
        client = TestClient(app)
        resp = client.get("/api/report/TCB")

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "TCB"
    assert data["report"] == "Báo cáo."
