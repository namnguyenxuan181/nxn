# News Monitoring — Design Spec

## Goal
Scrape Vietnamese finance news from 3 RSS sources, enrich each article with a Claude-generated summary and market sentiment score, store as daily JSON, and display in a new dashboard tab with keyword highlighting and sentiment badges.

## Audience
Personal / local use only.

## Tech Stack
- `requests` + `xml.etree.ElementTree` (RSS parsing — already installed)
- `anthropic` Python SDK (Claude Haiku for summarization + sentiment)
- `concurrent.futures.ThreadPoolExecutor` (parallel API calls)
- Streamlit (dashboard tab — existing)
- JSON files (storage — no database)

## RSS Sources

| Source     | Feed URL                                        |
|------------|------------------------------------------------|
| vnexpress  | https://vnexpress.net/rss/kinh-doanh.rss       |
| cafef      | https://cafef.vn/home.rss                      |
| vietstock  | https://vietstock.vn/144/chung-khoan.rss       |

## Data Model

```python
@dataclass
class NewsArticle:
    source: str        # "vnexpress" | "cafef" | "vietstock"
    title: str
    url: str
    published_at: str  # ISO 8601 e.g. "2026-06-21T08:30:00+07:00"
    description: str   # plain text, HTML stripped
    summary: str       # Claude-generated 1-2 sentence Vietnamese summary
    sentiment: str     # "positive" | "negative" | "neutral"
```

## File Structure

```
news/
  __init__.py
  model.py              ← NewsArticle dataclass
  keywords.py           ← KEYWORDS list of strings
  analyzer.py           ← Claude API: analyze_article() → (summary, sentiment)
  runner.py             ← NewsRunner: scrape → analyze → save
  scrapers/
    __init__.py
    base.py             ← BaseNewsScraper ABC
    vnexpress.py        ← RSS scraper
    cafef.py            ← RSS scraper
    vietstock.py        ← RSS scraper
  repositories/
    __init__.py
    base.py             ← BaseNewsRepository ABC
    json_repo.py        ← saves to data/news/news_YYYY-MM-DD.json
tests/
  news/
    __init__.py
    test_model.py
    scrapers/
      __init__.py
      test_vnexpress.py
      test_cafef.py
      test_vietstock.py
    test_analyzer.py
    repositories/
      __init__.py
      test_json_repo.py
    test_runner.py
```

## Storage

- Path: `data/news/news_YYYY-MM-DD.json`
- Format: JSON array of NewsArticle dicts, sorted newest-first
- Deduplicated by `url` — re-running on same day merges new articles in
- Added to `.gitignore`: `data/news/`

## news/keywords.py

```python
KEYWORDS = [
    "lãi suất", "ngân hàng", "chứng khoán", "VN-Index", "HNX-Index",
    "Techcombank", "Vietcombank", "BIDV", "VPBank", "MB Bank",
    "cổ phiếu", "tăng trưởng", "lạm phát", "tỷ giá",
]
```

User edits this file to change the watchlist.

## news/analyzer.py

Calls `claude-haiku-4-5-20251001` (cheapest, fastest):

```
System: You are a Vietnamese financial news analyst.
User: Analyze this article.
Title: {title}
Content: {description}

Respond with JSON only:
{"summary": "1-2 sentence summary in Vietnamese", "sentiment": "positive|negative|neutral"}

sentiment = market impact on Vietnamese stocks and banking sector.
```

- `analyze_article(title, description) -> tuple[str, str]` returns `(summary, sentiment)`
- Falls back to `("", "neutral")` on API error
- Requires `ANTHROPIC_API_KEY` environment variable

## news/runner.py

```python
class NewsRunner:
    def __init__(self, scrapers, repository, max_workers=10):
        ...
    def run(self) -> None:
        # 1. Scrape all sources → list[NewsArticle] (without summary/sentiment)
        # 2. Deduplicate by url against existing JSON for today
        # 3. Analyze new articles in parallel via ThreadPoolExecutor
        # 4. Merge with existing, sort newest-first, save
```

## Dashboard — News Tab

Added to `app.py` as `st.tabs(["💰 Interest Rates", "📈 Stock Prices", "📰 News"])`.

### Controls
- Date selectbox (defaults to today)
- "🔄 Fetch & Analyze" button — runs `NewsRunner`, clears cache, reruns

### Table columns
- Source, Title (as clickable link), Sentiment (🟢/🔴/⚪), Time

### Keyword highlighting
- Rows where title or description contains any keyword (case-insensitive) float to top and get yellow background via pandas Styler

### Summary expansion
- `st.expander` below the table listing matched-keyword articles with their Claude summary

### web/data_loader.py additions
```python
@st.cache_data(ttl=300)
def available_news_dates() -> list[str]:
    # scans data/news/news_*.json, returns dates sorted desc

@st.cache_data(ttl=300)
def load_news(date: str) -> pd.DataFrame:
    # reads data/news/news_{date}.json, returns DataFrame
```

`available_news_dates()` is separate from `available_dates()` because news uses `.json` not `.csv`.

## main.py

`NewsRunner` added alongside existing `CrawlRunner` and `StockCrawlRunner` — runs at 8am cron to pre-fetch the day's news.

## Error Handling
- Missing `ANTHROPIC_API_KEY`: show `st.error("Set ANTHROPIC_API_KEY env var to enable AI analysis.")`
- Empty JSON file or no file: show `st.info("No news yet. Click Fetch & Analyze.")`
- Per-article API errors: fall back to `summary=""`, `sentiment="neutral"`

## Dependencies to Add
```
anthropic>=0.40.0
```
