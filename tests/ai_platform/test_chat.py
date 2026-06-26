import os
from unittest.mock import MagicMock, patch


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


def test_chat_endpoint_streams_sse(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_stream_ctx.text_stream = iter(["Xin chào"])

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream_ctx

    with patch("ai_platform.chat._CLIENT", mock_client), \
         patch("ai_platform.chat.get_all_symbols", return_value=[]), \
         patch("ai_platform.chat.get_recent_news", return_value=[]):
        from fastapi.testclient import TestClient
        from ai_platform.main import app
        client = TestClient(app)
        resp = client.post("/api/chat", json={"message": "Xin chào", "history": []})

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "Xin chào" in resp.text
    assert "[DONE]" in resp.text
