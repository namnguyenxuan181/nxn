# News Monitoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scrape RSS news from 3 Vietnamese finance sites, enrich each article with a Claude-generated summary and market sentiment score, store as daily JSON, and display in a new "📰 News" dashboard tab with keyword highlighting.

**Architecture:** New `news/` domain mirrors the existing `interest/` and `stock/` pattern. `news/analyzer.py` calls Claude Haiku per article via `ThreadPoolExecutor(10)`. `news/runner.py` scrapes → deduplicates → analyzes → saves. Dashboard gets a third tab with a "🔄 Fetch & Analyze" button that runs the runner on demand.

**Tech Stack:** Python 3.9, requests (existing), xml.etree.ElementTree (stdlib), BeautifulSoup4 (existing), anthropic SDK ≥0.40.0, concurrent.futures (stdlib), Streamlit (existing)

## Global Constraints

- Python 3.9 — no walrus operator or `match` statements
- Claude model ID (exact): `claude-haiku-4-5-20251001`
- `anthropic>=0.40.0` added to `requirements.txt`
- Data path pattern: `data/news/news_YYYY-MM-DD.json`
- Source name strings (exact): `"vnexpress"`, `"cafef"`, `"vietstock"`
- Sentiment strings (exact): `"positive"`, `"negative"`, `"neutral"`
- `ANTHROPIC_API_KEY` env var required for analysis; absence must be handled gracefully
- New domain lives in `news/`; tests in `tests/news/`
- `.gitignore` must include `data/news/`

---

## Files

| File | Action | Responsibility |
|------|--------|----------------|
| `news/__init__.py` | Create | Package marker |
| `news/model.py` | Create | NewsArticle dataclass |
| `news/keywords.py` | Create | KEYWORDS watchlist |
| `news/scrapers/__init__.py` | Create | Package marker |
| `news/scrapers/base.py` | Create | BaseNewsScraper ABC |
| `news/scrapers/vnexpress.py` | Create | VnExpress RSS scraper |
| `news/scrapers/cafef.py` | Create | CafeF RSS scraper |
| `news/scrapers/vietstock.py` | Create | Vietstock RSS scraper |
| `news/repositories/__init__.py` | Create | Package marker |
| `news/repositories/base.py` | Create | BaseNewsRepository ABC |
| `news/repositories/json_repo.py` | Create | JSON file storage |
| `news/analyzer.py` | Create | Claude API: summary + sentiment |
| `news/runner.py` | Create | Orchestrate scrape→analyze→save |
| `tests/news/__init__.py` | Create | Package marker |
| `tests/news/scrapers/__init__.py` | Create | Package marker |
| `tests/news/repositories/__init__.py` | Create | Package marker |
| `tests/news/test_model.py` | Create | NewsArticle tests |
| `tests/news/scrapers/test_vnexpress.py` | Create | VnExpress scraper tests |
| `tests/news/scrapers/test_cafef.py` | Create | CafeF scraper tests |
| `tests/news/scrapers/test_vietstock.py` | Create | Vietstock scraper tests |
| `tests/news/test_analyzer.py` | Create | Analyzer tests (mocked) |
| `tests/news/repositories/test_json_repo.py` | Create | JSON repo tests |
| `tests/news/test_runner.py` | Create | Runner tests |
| `web/data_loader.py` | Modify | Add available_news_dates(), load_news() |
| `app.py` | Modify | Add 📰 News tab |
| `main.py` | Modify | Add NewsRunner call |
| `requirements.txt` | Modify | Add anthropic>=0.40.0 |
| `.gitignore` | Modify | Add data/news/ |

---

### Task 1: news domain — model, keywords, scrapers

**Files:**
- Create: `news/__init__.py`, `news/model.py`, `news/keywords.py`
- Create: `news/scrapers/__init__.py`, `news/scrapers/base.py`
- Create: `news/scrapers/vnexpress.py`, `news/scrapers/cafef.py`, `news/scrapers/vietstock.py`
- Create: `tests/news/__init__.py`, `tests/news/scrapers/__init__.py`
- Create: `tests/news/test_model.py`, `tests/news/scrapers/test_vnexpress.py`
- Create: `tests/news/scrapers/test_cafef.py`, `tests/news/scrapers/test_vietstock.py`

**Interfaces:**
- Produces:
  - `NewsArticle(source, title, url, published_at, description, summary="", sentiment="neutral")`
  - `KEYWORDS: list[str]`
  - `BaseNewsScraper.scrape() -> list[NewsArticle]`
  - `VnExpressScraper().scrape() -> list[NewsArticle]`
  - `CafefScraper().scrape() -> list[NewsArticle]`
  - `VietstockScraper().scrape() -> list[NewsArticle]`

- [ ] **Step 1: Create package markers**

Create these 3 empty files:
- `news/__init__.py`
- `news/scrapers/__init__.py`
- `tests/news/__init__.py`
- `tests/news/scrapers/__init__.py`

- [ ] **Step 2: Create `news/model.py`**

```python
from dataclasses import dataclass


@dataclass
class NewsArticle:
    source: str
    title: str
    url: str
    published_at: str
    description: str
    summary: str = ""
    sentiment: str = "neutral"
```

- [ ] **Step 3: Create `news/keywords.py`**

```python
KEYWORDS = [
    "lãi suất", "ngân hàng", "chứng khoán", "VN-Index", "HNX-Index",
    "Techcombank", "Vietcombank", "BIDV", "VPBank", "MB Bank",
    "cổ phiếu", "tăng trưởng", "lạm phát", "tỷ giá", "Fed",
    "tín dụng", "trái phiếu", "ngoại tệ", "USD",
]
```

- [ ] **Step 4: Create `news/scrapers/base.py`**

```python
from abc import ABC, abstractmethod
from news.model import NewsArticle


class BaseNewsScraper(ABC):
    @abstractmethod
    def scrape(self) -> list[NewsArticle]:
        pass
```

- [ ] **Step 5: Write failing tests for model**

`tests/news/test_model.py`:
```python
from news.model import NewsArticle


def test_news_article_defaults():
    a = NewsArticle(
        source="vnexpress",
        title="Test",
        url="https://example.com",
        published_at="2026-06-21T08:00:00+07:00",
        description="desc",
    )
    assert a.summary == ""
    assert a.sentiment == "neutral"


def test_news_article_with_all_fields():
    a = NewsArticle(
        source="cafef",
        title="Title",
        url="https://cafef.vn/1.html",
        published_at="2026-06-21T09:00:00+07:00",
        description="desc",
        summary="Tóm tắt.",
        sentiment="positive",
    )
    assert a.sentiment == "positive"
    assert a.summary == "Tóm tắt."
```

Run: `pytest tests/news/test_model.py -v`
Expected: PASS (dataclass is simple)

- [ ] **Step 6: Write failing tests for VnExpress scraper**

`tests/news/scrapers/test_vnexpress.py`:
```python
from unittest.mock import patch, MagicMock
from news.scrapers.vnexpress import VnExpressScraper

_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
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
</rss>"""


def _mock_response(content: bytes) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


def test_vnexpress_scrape_returns_articles():
    with patch("news.scrapers.vnexpress.requests.get", return_value=_mock_response(_RSS)):
        articles = VnExpressScraper().scrape()
    assert len(articles) == 1
    assert articles[0].source == "vnexpress"
    assert articles[0].title == "MSCI nâng hạng thị trường Việt Nam"
    assert articles[0].url == "https://vnexpress.net/a.html"
    assert "Mô tả ngắn" in articles[0].description
    assert "<" not in articles[0].description  # HTML stripped
    assert articles[0].summary == ""
    assert articles[0].sentiment == "neutral"


def test_vnexpress_scrape_skips_empty_items():
    with patch("news.scrapers.vnexpress.requests.get", return_value=_mock_response(_RSS)):
        articles = VnExpressScraper().scrape()
    assert all(a.title and a.url for a in articles)
```

Run: `pytest tests/news/scrapers/test_vnexpress.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 7: Implement `news/scrapers/vnexpress.py`**

```python
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup

from news.model import NewsArticle
from news.scrapers.base import BaseNewsScraper

_URL = "https://vnexpress.net/rss/kinh-doanh.rss"
_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _strip_html(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(separator=" ").strip()


def _parse_date(pub_date: str) -> str:
    try:
        return parsedate_to_datetime(pub_date).isoformat()
    except Exception:
        return ""


class VnExpressScraper(BaseNewsScraper):
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
                source="vnexpress",
                title=title,
                url=url,
                published_at=published_at,
                description=description,
            ))
        return articles
```

- [ ] **Step 8: Run VnExpress tests — verify they pass**

```bash
pytest tests/news/scrapers/test_vnexpress.py -v
```
Expected: 2 passed

- [ ] **Step 9: Write failing tests for CafeF scraper**

`tests/news/scrapers/test_cafef.py`:
```python
from unittest.mock import patch, MagicMock
from news.scrapers.cafef import CafefScraper

_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
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
</rss>"""


def _mock_response(content: bytes) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


def test_cafef_scrape_returns_articles():
    with patch("news.scrapers.cafef.requests.get", return_value=_mock_response(_RSS)):
        articles = CafefScraper().scrape()
    assert len(articles) == 1
    assert articles[0].source == "cafef"
    assert articles[0].title == "Lãi suất ngân hàng tăng mạnh"
    assert articles[0].url == "https://cafef.vn/lai-suat-tang.chn"
    assert "Nội dung" in articles[0].description
    assert "<" not in articles[0].description
```

Run: `pytest tests/news/scrapers/test_cafef.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 10: Implement `news/scrapers/cafef.py`**

```python
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
```

- [ ] **Step 11: Write failing tests for Vietstock scraper**

`tests/news/scrapers/test_vietstock.py`:
```python
from unittest.mock import patch, MagicMock
from news.scrapers.vietstock import VietstockScraper

_RSS = b"""<?xml version="1.0" encoding="utf-8"?>
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
</rss>"""


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
```

Run: `pytest tests/news/scrapers/test_vietstock.py -v`
Expected: FAIL

- [ ] **Step 12: Implement `news/scrapers/vietstock.py`**

```python
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup

from news.model import NewsArticle
from news.scrapers.base import BaseNewsScraper

_URL = "https://vietstock.vn/144/chung-khoan.rss"
_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _strip_html(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(separator=" ").strip()


def _parse_date(pub_date: str) -> str:
    try:
        return parsedate_to_datetime(pub_date).isoformat()
    except Exception:
        return ""


class VietstockScraper(BaseNewsScraper):
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
                source="vietstock",
                title=title,
                url=url,
                published_at=published_at,
                description=description,
            ))
        return articles
```

- [ ] **Step 13: Run all scraper tests**

```bash
pytest tests/news/ -v
```
Expected: all pass

- [ ] **Step 14: Run full suite for regressions**

```bash
pytest tests/ -v
```
Expected: all pass

- [ ] **Step 15: Commit**

```bash
git add news/ tests/news/ && git commit -m "feat: add news domain — model, keywords, and RSS scrapers"
```

---

### Task 2: news/analyzer.py — Claude API integration

**Files:**
- Create: `news/analyzer.py`
- Create: `tests/news/test_analyzer.py`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: nothing from earlier tasks directly (standalone function)
- Produces:
  - `analyze_article(title: str, description: str) -> tuple[str, str]`
    returns `(summary, sentiment)` where sentiment ∈ `{"positive", "negative", "neutral"}`

- [ ] **Step 1: Add anthropic to requirements.txt**

```text
requests==2.31.0
beautifulsoup4==4.12.3
streamlit>=1.35.0
matplotlib>=3.7.0
anthropic>=0.40.0
```

Install: `pip install anthropic`

- [ ] **Step 2: Write failing tests**

`tests/news/test_analyzer.py`:
```python
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
```

Run: `pytest tests/news/test_analyzer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `news/analyzer.py`**

```python
import json
import os

import anthropic

_MODEL = "claude-haiku-4-5-20251001"
_PROMPT = (
    "Analyze this Vietnamese finance news article.\n"
    "Title: {title}\n"
    "Content: {description}\n\n"
    'Respond with JSON only: {{"summary": "1-2 sentence summary in Vietnamese", '
    '"sentiment": "positive|negative|neutral"}}\n'
    "sentiment = market impact on Vietnamese stocks and banking sector."
)


def analyze_article(title: str, description: str) -> tuple:
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        message = client.messages.create(
            model=_MODEL,
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": _PROMPT.format(title=title, description=description[:500]),
            }],
        )
        result = json.loads(message.content[0].text)
        return result.get("summary", ""), result.get("sentiment", "neutral")
    except Exception:
        return "", "neutral"
```

- [ ] **Step 4: Run analyzer tests — verify they pass**

```bash
pytest tests/news/test_analyzer.py -v
```
Expected: 3 passed

- [ ] **Step 5: Run full suite**

```bash
pytest tests/ -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add news/analyzer.py tests/news/test_analyzer.py requirements.txt
git commit -m "feat: add news analyzer with Claude Haiku for summary and sentiment"
```

---

### Task 3: news/repositories + news/runner.py

**Files:**
- Create: `news/repositories/__init__.py`, `news/repositories/base.py`, `news/repositories/json_repo.py`
- Create: `news/runner.py`
- Create: `tests/news/repositories/__init__.py`, `tests/news/repositories/test_json_repo.py`
- Create: `tests/news/test_runner.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes:
  - `NewsArticle` from `news.model`
  - `analyze_article(title, description) -> tuple[str, str]` from `news.analyzer`
  - `BaseNewsScraper.scrape() -> list[NewsArticle]` from `news.scrapers.base`
- Produces:
  - `BaseNewsRepository.load(date: str) -> list[NewsArticle]`
  - `BaseNewsRepository.save(articles: list[NewsArticle], date: str) -> None`
  - `JSONNewsRepository(data_dir="data/news")` implementing above
  - `NewsRunner(scrapers, repository, max_workers=10).run(target_date=None) -> None`

- [ ] **Step 1: Add data/news/ to .gitignore**

Append `data/news/` to `.gitignore`. Full file after edit:
```
venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.egg-info/
data/interest/
data/stock/
data/news/
data/cron.log
.idea/
.DS_Store
```

- [ ] **Step 2: Create package markers**

Create empty files:
- `news/repositories/__init__.py`
- `tests/news/repositories/__init__.py`

- [ ] **Step 3: Create `news/repositories/base.py`**

```python
from abc import ABC, abstractmethod
from news.model import NewsArticle


class BaseNewsRepository(ABC):
    @abstractmethod
    def load(self, date: str) -> list[NewsArticle]:
        pass

    @abstractmethod
    def save(self, articles: list[NewsArticle], date: str) -> None:
        pass
```

- [ ] **Step 4: Write failing tests for JSONNewsRepository**

`tests/news/repositories/test_json_repo.py`:
```python
import json
import os
from news.model import NewsArticle
from news.repositories.json_repo import JSONNewsRepository


def _make_article(source: str, title: str, url: str) -> NewsArticle:
    return NewsArticle(
        source=source,
        title=title,
        url=url,
        published_at="2026-06-21T08:00:00+07:00",
        description="desc",
        summary="Tóm tắt.",
        sentiment="positive",
    )


def test_save_creates_json_file(tmp_path):
    repo = JSONNewsRepository(data_dir=str(tmp_path))
    repo.save([_make_article("vnexpress", "Title", "https://vnexpress.net/1.html")], "2026-06-21")
    assert (tmp_path / "news_2026-06-21.json").exists()


def test_save_writes_correct_fields(tmp_path):
    repo = JSONNewsRepository(data_dir=str(tmp_path))
    repo.save([_make_article("cafef", "Lãi suất", "https://cafef.vn/1.html")], "2026-06-21")
    with open(tmp_path / "news_2026-06-21.json", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["source"] == "cafef"
    assert data[0]["title"] == "Lãi suất"
    assert data[0]["sentiment"] == "positive"


def test_load_returns_articles(tmp_path):
    repo = JSONNewsRepository(data_dir=str(tmp_path))
    articles = [_make_article("vietstock", "MSCI", "https://vietstock.vn/1.htm")]
    repo.save(articles, "2026-06-21")
    loaded = repo.load("2026-06-21")
    assert len(loaded) == 1
    assert loaded[0].source == "vietstock"
    assert loaded[0].sentiment == "positive"


def test_load_returns_empty_when_no_file(tmp_path):
    repo = JSONNewsRepository(data_dir=str(tmp_path))
    assert repo.load("2026-06-21") == []


def test_save_does_nothing_for_empty_list(tmp_path):
    repo = JSONNewsRepository(data_dir=str(tmp_path))
    repo.save([], "2026-06-21")
    assert not any(tmp_path.iterdir())


def test_save_creates_data_dir_if_missing(tmp_path):
    data_dir = str(tmp_path / "news")
    repo = JSONNewsRepository(data_dir=data_dir)
    repo.save([_make_article("vnexpress", "T", "https://v.net/1.html")], "2026-06-21")
    assert os.path.isdir(data_dir)
```

Run: `pytest tests/news/repositories/test_json_repo.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 5: Implement `news/repositories/json_repo.py`**

```python
import dataclasses
import json
import os

from news.model import NewsArticle
from news.repositories.base import BaseNewsRepository


class JSONNewsRepository(BaseNewsRepository):
    def __init__(self, data_dir: str = "data/news"):
        self._data_dir = data_dir

    def _path(self, date: str) -> str:
        return os.path.join(self._data_dir, f"news_{date}.json")

    def load(self, date: str) -> list[NewsArticle]:
        path = self._path(date)
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [NewsArticle(**d) for d in data]

    def save(self, articles: list[NewsArticle], date: str) -> None:
        if not articles:
            return
        os.makedirs(self._data_dir, exist_ok=True)
        with open(self._path(date), "w", encoding="utf-8") as f:
            json.dump([dataclasses.asdict(a) for a in articles], f, ensure_ascii=False, indent=2)
```

- [ ] **Step 6: Run repository tests — verify they pass**

```bash
pytest tests/news/repositories/test_json_repo.py -v
```
Expected: 6 passed

- [ ] **Step 7: Write failing tests for NewsRunner**

`tests/news/test_runner.py`:
```python
from unittest.mock import MagicMock, patch
from news.model import NewsArticle
from news.runner import NewsRunner


def _make_article(url: str, source: str = "vnexpress") -> NewsArticle:
    return NewsArticle(
        source=source, title="Title", url=url,
        published_at="2026-06-21T08:00:00+07:00", description="desc",
    )


def test_runner_scrapes_all_sources():
    scraper_a = MagicMock()
    scraper_a.scrape.return_value = [_make_article("https://a.com/1")]
    scraper_b = MagicMock()
    scraper_b.scrape.return_value = [_make_article("https://b.com/1", "cafef")]
    repo = MagicMock()
    repo.load.return_value = []

    with patch("news.runner.analyze_article", return_value=("summary", "positive")):
        NewsRunner([scraper_a, scraper_b], repo).run(target_date="2026-06-21")

    scraper_a.scrape.assert_called_once()
    scraper_b.scrape.assert_called_once()


def test_runner_deduplicates_by_url():
    existing = [_make_article("https://a.com/1")]
    scraper = MagicMock()
    scraper.scrape.return_value = [
        _make_article("https://a.com/1"),   # duplicate
        _make_article("https://a.com/2"),   # new
    ]
    repo = MagicMock()
    repo.load.return_value = existing

    with patch("news.runner.analyze_article", return_value=("s", "neutral")) as mock_analyze:
        NewsRunner([scraper], repo).run(target_date="2026-06-21")

    # Only the new article should be analyzed
    assert mock_analyze.call_count == 1


def test_runner_saves_merged_results():
    existing = [_make_article("https://a.com/1")]
    scraper = MagicMock()
    scraper.scrape.return_value = [_make_article("https://a.com/2")]
    repo = MagicMock()
    repo.load.return_value = existing

    with patch("news.runner.analyze_article", return_value=("s", "positive")):
        NewsRunner([scraper], repo).run(target_date="2026-06-21")

    saved_articles = repo.save.call_args[0][0]
    assert len(saved_articles) == 2


def test_runner_save_called_once():
    scraper = MagicMock()
    scraper.scrape.return_value = [_make_article("https://a.com/1")]
    repo = MagicMock()
    repo.load.return_value = []

    with patch("news.runner.analyze_article", return_value=("s", "neutral")):
        NewsRunner([scraper], repo).run(target_date="2026-06-21")

    repo.save.assert_called_once()
```

Run: `pytest tests/news/test_runner.py -v`
Expected: FAIL

- [ ] **Step 8: Implement `news/runner.py`**

```python
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from news.analyzer import analyze_article
from news.model import NewsArticle
from news.repositories.base import BaseNewsRepository
from news.scrapers.base import BaseNewsScraper

_MAX_WORKERS = 10


class NewsRunner:
    def __init__(self, scrapers: list, repository: BaseNewsRepository, max_workers: int = _MAX_WORKERS):
        self._scrapers = scrapers
        self._repository = repository
        self._max_workers = max_workers

    def run(self, target_date: str = None) -> None:
        if target_date is None:
            target_date = date.today().strftime("%Y-%m-%d")

        raw: list[NewsArticle] = []
        for scraper in self._scrapers:
            raw.extend(scraper.scrape())

        existing = self._repository.load(target_date)
        existing_urls = {a.url for a in existing}
        new_articles = [a for a in raw if a.url not in existing_urls]

        def _analyze(article: NewsArticle) -> NewsArticle:
            summary, sentiment = analyze_article(article.title, article.description)
            article.summary = summary
            article.sentiment = sentiment
            return article

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            analyzed = list(executor.map(_analyze, new_articles))

        all_articles = existing + analyzed
        all_articles.sort(key=lambda a: a.published_at, reverse=True)
        self._repository.save(all_articles, target_date)
```

- [ ] **Step 9: Run runner tests — verify they pass**

```bash
pytest tests/news/test_runner.py -v
```
Expected: 4 passed

- [ ] **Step 10: Run full suite**

```bash
pytest tests/ -v
```
Expected: all pass

- [ ] **Step 11: Commit**

```bash
git add news/repositories/ news/runner.py tests/news/repositories/ tests/news/test_runner.py .gitignore
git commit -m "feat: add news JSON repository and runner with deduplication"
```

---

### Task 4: Dashboard integration

**Files:**
- Modify: `web/data_loader.py`
- Modify: `app.py`
- Modify: `main.py`

**Interfaces:**
- Consumes:
  - `NewsRunner(scrapers, repository, max_workers).run(target_date)` from `news.runner`
  - `VnExpressScraper`, `CafefScraper`, `VietstockScraper` from `news.scrapers.*`
  - `JSONNewsRepository` from `news.repositories.json_repo`
  - `KEYWORDS` from `news.keywords`
- Produces:
  - `available_news_dates() -> list[str]` in `web.data_loader`
  - `load_news(date: str) -> pd.DataFrame` in `web.data_loader`
  - "📰 News" tab in `app.py`

No new unit tests for this task — verified by running the Streamlit app manually.

- [ ] **Step 1: Add available_news_dates() and load_news() to web/data_loader.py**

Full updated `web/data_loader.py`:
```python
import glob
import json
import os
import re

import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@st.cache_data(ttl=300)
def available_dates(domain: str) -> list:
    pattern = os.path.join(DATA_DIR, domain, f"{domain}_*.csv")
    files = glob.glob(pattern)
    dates = []
    for f in files:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(f))
        if m:
            dates.append(m.group(1))
    return sorted(dates, reverse=True)


@st.cache_data
def load_interest(date: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "interest", f"interest_{date}.csv")
    return pd.read_csv(path)


@st.cache_data
def load_stock(date: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "stock", f"stock_{date}.csv")
    return pd.read_csv(path)


@st.cache_data(ttl=300)
def available_news_dates() -> list:
    pattern = os.path.join(DATA_DIR, "news", "news_*.json")
    files = glob.glob(pattern)
    dates = []
    for f in files:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(f))
        if m:
            dates.append(m.group(1))
    return sorted(dates, reverse=True)


@st.cache_data(ttl=300)
def load_news(date: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "news", f"news_{date}.json")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["source", "title", "url", "published_at", "description", "summary", "sentiment"])
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data)
```

- [ ] **Step 2: Run web/data_loader tests to confirm no regressions**

```bash
pytest tests/web/test_data_loader.py -v
```
Expected: 4 passed

- [ ] **Step 3: Update app.py — add News tab**

Full updated `app.py`:
```python
import os

import pandas as pd
import streamlit as st

from web.data_loader import (
    available_dates,
    available_news_dates,
    load_interest,
    load_news,
    load_stock,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

st.set_page_config(page_title="NXN Dashboard", layout="wide")
st.title("📊 NXN Dashboard")

tab1, tab2, tab3 = st.tabs(["💰 Interest Rates", "📈 Stock Prices", "📰 News"])

# ── Interest Rates ────────────────────────────────────────────────────────────
with tab1:
    dates = available_dates("interest")
    if not dates:
        st.info("No data available yet. Run main.py first.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            date = st.selectbox("Date", dates, key="interest_date")
        with col2:
            channel = st.selectbox("Channel", ["All", "counter", "online"], key="interest_channel")

        df = load_interest(date)
        if channel != "All":
            df = df[df["channel"] == channel]

        display = df.drop(columns=["date"]).rename(columns={
            "bank": "Bank", "channel": "Channel",
            "rate_1m": "1m %", "rate_3m": "3m %", "rate_6m": "6m %",
            "rate_12m": "12m %", "rate_18m": "18m %",
            "rate_24m": "24m %", "rate_36m": "36m %",
        })

        rate_cols = ["1m %", "3m %", "6m %", "12m %", "18m %", "24m %", "36m %"]
        col_config = {
            col: st.column_config.ProgressColumn(col, min_value=0, max_value=10, format="%.2f %%")
            for col in rate_cols
        }
        st.dataframe(display, column_config=col_config, use_container_width=True, hide_index=True)

# ── Stock Prices ──────────────────────────────────────────────────────────────
with tab2:
    dates = available_dates("stock")
    if not dates:
        st.info("No data available yet. Run main.py first.")
    else:
        col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
        with col1:
            date = st.selectbox("Date", dates, key="stock_date")
        with col2:
            search = st.text_input("Search symbol", key="stock_search")
        with col3:
            sort_col = st.selectbox(
                "Sort by", ["symbol", "open", "high", "low", "close", "volume"],
                key="stock_sort",
            )
        with col4:
            order = st.selectbox("Order", ["Descending", "Ascending"], key="stock_order")

        df = load_stock(date)
        if search:
            df = df[df["symbol"].str.contains(search.upper(), na=False)]
        df = df.sort_values(sort_col, ascending=(order == "Ascending"))

        display = df.drop(columns=["date"]).rename(columns={
            "symbol": "Symbol", "open": "Open", "high": "High",
            "low": "Low", "close": "Close", "volume": "Volume",
        })
        st.dataframe(
            display.style.format({
                "Open": "{:,.0f}", "High": "{:,.0f}",
                "Low": "{:,.0f}", "Close": "{:,.0f}", "Volume": "{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

# ── News ──────────────────────────────────────────────────────────────────────
with tab3:
    from datetime import date as _date
    from news.keywords import KEYWORDS

    news_dates = available_news_dates()
    col1, col2 = st.columns([3, 1])
    with col1:
        if news_dates:
            news_date = st.selectbox("Date", news_dates, key="news_date")
        else:
            news_date = _date.today().strftime("%Y-%m-%d")
            st.info("No news yet. Click Fetch & Analyze.")
    with col2:
        st.write("")
        fetch_btn = st.button("🔄 Fetch & Analyze", key="news_fetch")

    if fetch_btn:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.error("Set ANTHROPIC_API_KEY environment variable to enable AI analysis.")
        else:
            with st.spinner("Fetching and analyzing news…"):
                from news.runner import NewsRunner
                from news.scrapers.cafef import CafefScraper
                from news.scrapers.vnexpress import VnExpressScraper
                from news.scrapers.vietstock import VietstockScraper
                from news.repositories.json_repo import JSONNewsRepository
                NewsRunner(
                    [VnExpressScraper(), CafefScraper(), VietstockScraper()],
                    JSONNewsRepository(data_dir=os.path.join(DATA_DIR, "news")),
                ).run(target_date=news_date)
                st.cache_data.clear()
                st.rerun()

    news_dates = available_news_dates()
    if news_dates:
        df = load_news(news_date)

        if df.empty:
            st.info("No articles for this date.")
        else:
            st.caption(f"Keywords: {', '.join(KEYWORDS[:8])} …")

            def _matches(row: pd.Series) -> bool:
                text = (str(row.get("title", "")) + " " + str(row.get("description", ""))).lower()
                return any(kw.lower() in text for kw in KEYWORDS)

            df["matched"] = df.apply(_matches, axis=1)
            df["📊"] = df["sentiment"].map({"positive": "🟢", "negative": "🔴", "neutral": "⚪"})
            df["Time"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce").dt.tz_convert("Asia/Ho_Chi_Minh").dt.strftime("%H:%M")
            df = df.sort_values(["matched", "published_at"], ascending=[False, False])

            display = df[["source", "title", "url", "📊", "Time"]].rename(columns={
                "source": "Source", "title": "Title", "url": "URL",
            })

            def _highlight(row: pd.Series) -> list:
                if df.loc[row.name, "matched"]:
                    return ["background-color: #fff9c4"] * len(row)
                return [""] * len(row)

            st.dataframe(
                display.style.apply(_highlight, axis=1),
                column_config={"URL": st.column_config.LinkColumn("URL", display_text="🔗")},
                use_container_width=True,
                hide_index=True,
            )

            matched = df[df["matched"]]
            if not matched.empty:
                st.subheader("Matched Articles — AI Summaries")
                for _, row in matched.iterrows():
                    icon = "🟢" if row["sentiment"] == "positive" else "🔴" if row["sentiment"] == "negative" else "⚪"
                    with st.expander(f"{icon} {row['title']}"):
                        st.write(row["summary"] if row["summary"] else "_No summary available._")
                        st.markdown(f"[Read full article]({row['url']})")
```

- [ ] **Step 4: Update main.py to include NewsRunner**

Full updated `main.py`:
```python
import os

from interest.repositories.csv import CSVRepository
from interest.runner import CrawlRunner
from interest.scrapers.techcombank import TechcombankScraper
from stock.repositories.csv import StockCSVRepository
from stock.runner import StockCrawlRunner
from stock.scrapers.vnstock import VnstockScraper

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def main():
    CrawlRunner(
        [TechcombankScraper()],
        CSVRepository(data_dir=os.path.join(DATA_DIR, "interest")),
    ).run()

    StockCrawlRunner(
        [VnstockScraper()],
        StockCSVRepository(data_dir=os.path.join(DATA_DIR, "stock")),
    ).run()

    if os.environ.get("ANTHROPIC_API_KEY"):
        from news.repositories.json_repo import JSONNewsRepository
        from news.runner import NewsRunner
        from news.scrapers.cafef import CafefScraper
        from news.scrapers.vnexpress import VnExpressScraper
        from news.scrapers.vietstock import VietstockScraper
        NewsRunner(
            [VnExpressScraper(), CafefScraper(), VietstockScraper()],
            JSONNewsRepository(data_dir=os.path.join(DATA_DIR, "news")),
        ).run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all pass

- [ ] **Step 6: Launch Streamlit and verify News tab**

```bash
ANTHROPIC_API_KEY=<your-key> streamlit run app.py
```

Open http://localhost:8501, click "📰 News" tab. Check:
- Date selectbox and "🔄 Fetch & Analyze" button visible
- Click button → spinner appears, articles load after ~20s
- Table shows Source, Title, URL (🔗), Sentiment emoji, Time
- Rows matching keywords highlighted yellow
- "Matched Articles — AI Summaries" section expands per article

- [ ] **Step 7: Commit**

```bash
git add web/data_loader.py app.py main.py
git commit -m "feat: add News tab to dashboard with AI summaries and keyword highlighting"
```
