from unittest.mock import patch, MagicMock
from news.scrapers.vietstock import VietstockScraper

_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>Chung khoan - Vietstock RSS</title>
    <item>
      <guid isPermaLink="true">http://vietstock.vn/2026/06/msci-830-1456651.htm</guid>
      <link>http://vietstock.vn/2026/06/msci-830-1456651.htm</link>
      <title>MSCI đánh giá cao nỗ lực của Việt Nam</title>
      <description>&lt;img alt='' src='x.jpg'/&gt;Tóm tắt bài báo.</description>
      <pubDate>Sat, 20 Jun 2026 21:00:00 +0700</pubDate>
    </item>
  </channel>
</rss>""".encode("utf-8")


def _mock_response(content: bytes) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


def test_vietstock_scrape_returns_articles():
    with patch("news.scrapers.vietstock.requests.get", return_value=_mock_response(_RSS)):
        articles = VietstockScraper().scrape()
    assert len(articles) == 1
    assert articles[0].source == "vietstock"
    assert articles[0].title == "MSCI đánh giá cao nỗ lực của Việt Nam"
    assert articles[0].url == "http://vietstock.vn/2026/06/msci-830-1456651.htm"
    assert "<" not in articles[0].description
    assert "Tóm tắt" in articles[0].description
