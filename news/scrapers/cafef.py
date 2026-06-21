import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup

from news.model import NewsArticle
from news.scrapers.base import BaseNewsScraper

_URL = "https://cafef.vn/home.rss"
_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _strip_html(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(separator=" ").strip()


def _parse_date(pub_date: str) -> str:
    try:
        return parsedate_to_datetime(pub_date).isoformat()
    except Exception:
        return ""


class CafefScraper(BaseNewsScraper):
    def scrape(self) -> list[NewsArticle]:
        resp = requests.get(_URL, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            url = (item.findtext("link") or "").strip()
            if not title or not url:
                continue
            description = _strip_html(item.findtext("description") or "")
            published_at = _parse_date(item.findtext("pubDate") or "")
            articles.append(NewsArticle(
                source="cafef",
                title=title,
                url=url,
                published_at=published_at,
                description=description,
            ))
        return articles
