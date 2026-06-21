import json
from unittest.mock import patch, MagicMock
from news.analyzer import analyze_article


def _mock_client(summary: str, sentiment: str) -> MagicMock:
    content_block = MagicMock()
    content_block.text = json.dumps({"summary": summary, "sentiment": sentiment})
    message = MagicMock()
    message.content = [content_block]
    client = MagicMock()
    client.messages.create.return_value = message
    return client


def test_analyze_article_returns_summary_and_sentiment():
    with patch("news.analyzer.anthropic.Anthropic", return_value=_mock_client(
        "Thị trường chứng khoán tăng điểm.", "positive"
    )):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            summary, sentiment = analyze_article("VN-Index tăng mạnh", "Mô tả bài báo")
    assert summary == "Thị trường chứng khoán tăng điểm."
    assert sentiment == "positive"


def test_analyze_article_returns_neutral_on_error():
    with patch("news.analyzer.anthropic.Anthropic", side_effect=Exception("API error")):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            summary, sentiment = analyze_article("Title", "Desc")
    assert summary == ""
    assert sentiment == "neutral"


def test_analyze_article_handles_invalid_json():
    content_block = MagicMock()
    content_block.text = "not valid json"
    message = MagicMock()
    message.content = [content_block]
    client = MagicMock()
    client.messages.create.return_value = message
    with patch("news.analyzer.anthropic.Anthropic", return_value=client):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            summary, sentiment = analyze_article("Title", "Desc")
    assert summary == ""
    assert sentiment == "neutral"
