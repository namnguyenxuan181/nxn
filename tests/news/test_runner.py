from unittest.mock import MagicMock, patch
import pytest
from news.model import NewsArticle
from news.runner import NewsRunner

_WITH_KEY = {"ANTHROPIC_API_KEY": "test-key"}


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
        with patch.dict("os.environ", _WITH_KEY):
            NewsRunner([scraper_a, scraper_b], repo).run(target_date="2026-06-21")

    scraper_a.scrape.assert_called_once()
    scraper_b.scrape.assert_called_once()


def test_runner_deduplicates_by_url():
    existing = [_make_article("https://a.com/1")]
    scraper = MagicMock()
    scraper.scrape.return_value = [
        _make_article("https://a.com/1"),
        _make_article("https://a.com/2"),
    ]
    repo = MagicMock()
    repo.load.return_value = existing

    with patch("news.runner.analyze_article", return_value=("s", "neutral")) as mock_analyze:
        with patch.dict("os.environ", _WITH_KEY):
            NewsRunner([scraper], repo).run(target_date="2026-06-21")

    assert mock_analyze.call_count == 1


def test_runner_saves_merged_results():
    existing = [_make_article("https://a.com/1")]
    scraper = MagicMock()
    scraper.scrape.return_value = [_make_article("https://a.com/2")]
    repo = MagicMock()
    repo.load.return_value = existing

    with patch("news.runner.analyze_article", return_value=("s", "positive")):
        with patch.dict("os.environ", _WITH_KEY):
            NewsRunner([scraper], repo).run(target_date="2026-06-21")

    saved_articles = repo.save.call_args[0][0]
    assert len(saved_articles) == 2


def test_runner_save_called_once():
    scraper = MagicMock()
    scraper.scrape.return_value = [_make_article("https://a.com/1")]
    repo = MagicMock()
    repo.load.return_value = []

    with patch("news.runner.analyze_article", return_value=("s", "neutral")):
        with patch.dict("os.environ", _WITH_KEY):
            NewsRunner([scraper], repo).run(target_date="2026-06-21")

    repo.save.assert_called_once()


def test_runner_skips_analysis_without_api_key():
    scraper = MagicMock()
    scraper.scrape.return_value = [_make_article("https://a.com/1")]
    repo = MagicMock()
    repo.load.return_value = []

    with patch("news.runner.analyze_article") as mock_analyze:
        with patch.dict("os.environ", {}, clear=True):
            NewsRunner([scraper], repo).run(target_date="2026-06-21")

    mock_analyze.assert_not_called()
    saved = repo.save.call_args[0][0]
    assert saved[0].summary == ""
    assert saved[0].sentiment == "neutral"
