from unittest.mock import patch, MagicMock
from services.news.scrapers.cafef import CafefScraper

_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>cafef</title>
    <item>
      <title><![CDATA[Lãi suất ngân hàng tăng mạnh]]></title>
      <link>https://cafef.vn/lai-suat-tang.chn</link>
      <description><![CDATA[<a href="https://cafef.vn/lai-suat-tang.chn"><img src="x.jpg"></a> Nội dung bài báo.]]></description>
      <pubDate>Sun, 21 Jun 2026 06:30:00 +07</pubDate>
      <guid>https://cafef.vn/lai-suat-tang.chn</guid>
    </item>
  </channel>
</rss>""".encode("utf-8")


def _mock_response(content: bytes) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


def test_cafef_scrape_returns_articles():
    with patch("services.news.scrapers.cafef.requests.get", return_value=_mock_response(_RSS)):
        articles = CafefScraper().scrape()
    assert len(articles) == 1
    assert articles[0].source == "cafef"
    assert articles[0].title == "Lãi suất ngân hàng tăng mạnh"
    assert articles[0].url == "https://cafef.vn/lai-suat-tang.chn"
    assert "Nội dung" in articles[0].description
    assert "<" not in articles[0].description
