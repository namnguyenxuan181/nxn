from unittest.mock import MagicMock
from services.interest.runner import CrawlRunner
from services.interest.model import InterestRate


def _make_record(bank: str) -> InterestRate:
    return InterestRate("2026-06-19", bank, "counter", 3.5, 4.0, 5.0, 5.5, None, 5.8, 6.0)


def test_run_calls_all_scrapers():
    scraper_a = MagicMock()
    scraper_a.scrape.return_value = [_make_record("BankA")]
    scraper_b = MagicMock()
    scraper_b.scrape.return_value = [_make_record("BankB")]
    repo = MagicMock()

    CrawlRunner([scraper_a, scraper_b], repo).run()

    scraper_a.scrape.assert_called_once()
    scraper_b.scrape.assert_called_once()


def test_run_saves_aggregated_results():
    scraper_a = MagicMock()
    scraper_a.scrape.return_value = [_make_record("BankA")]
    scraper_b = MagicMock()
    scraper_b.scrape.return_value = [_make_record("BankB")]
    repo = MagicMock()

    CrawlRunner([scraper_a, scraper_b], repo).run()

    saved = repo.save.call_args[0][0]
    assert len(saved) == 2
    assert {r.bank for r in saved} == {"BankA", "BankB"}


def test_run_calls_save_once():
    scraper = MagicMock()
    scraper.scrape.return_value = [_make_record("BankA")]
    repo = MagicMock()

    CrawlRunner([scraper], repo).run()

    repo.save.assert_called_once()


def test_run_with_empty_scraper_list_saves_empty():
    repo = MagicMock()
    CrawlRunner([], repo).run()
    repo.save.assert_called_once_with([])
