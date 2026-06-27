from unittest.mock import patch, MagicMock
from services.news.scrapers.vnexpress import VnExpressScraper

_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Kinh doanh - VnExpress RSS</title>
    <item>
      <title>MSCI nâng hạng thị trường Việt Nam</title>
      <description><![CDATA[<a href="https://vnexpress.net/a.html"><img src="x.jpg"></a></br>Mô tả ngắn.]]></description>
      <pubDate>Sat, 21 Jun 2026 08:30:00 +0700</pubDate>
      <link>https://vnexpress.net/a.html</link>
      <guid>https://vnexpress.net/a.html</guid>
    </item>
    <item>
      <title></title>
      <link></link>
      <description></description>
      <pubDate>Sat, 21 Jun 2026 07:00:00 +0700</pubDate>
    </item>
  </channel>
</rss>""".encode("utf-8")


def _mock_response(content: bytes) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


def test_vnexpress_scrape_returns_articles():
    with patch("services.news.scrapers.vnexpress.requests.get", return_value=_mock_response(_RSS)):
        articles = VnExpressScraper().scrape()
    assert len(articles) == 1
    assert articles[0].source == "vnexpress"
    assert articles[0].title == "MSCI nâng hạng thị trường Việt Nam"
    assert articles[0].url == "https://vnexpress.net/a.html"
    assert "Mô tả ngắn" in articles[0].description
    assert "<" not in articles[0].description
    assert articles[0].summary == ""
    assert articles[0].sentiment == "neutral"


def test_vnexpress_scrape_skips_empty_items():
    with patch("services.news.scrapers.vnexpress.requests.get", return_value=_mock_response(_RSS)):
        articles = VnExpressScraper().scrape()
    assert all(a.title and a.url for a in articles)
