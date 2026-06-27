from unittest.mock import MagicMock
from services.stock.runner import StockCrawlRunner
from services.stock.model import StockPrice


def _make_stock(symbol: str) -> StockPrice:
    return StockPrice("2026-06-18", symbol, 24050, 24150, 23650, 23650, 18040500)


def test_stock_run_calls_all_scrapers():
    scraper_a = MagicMock()
    scraper_a.scrape.return_value = [_make_stock("HPG")]
    scraper_b = MagicMock()
    scraper_b.scrape.return_value = [_make_stock("VNM")]
    repo = MagicMock()

    StockCrawlRunner([scraper_a, scraper_b], repo).run()

    scraper_a.scrape.assert_called_once()
    scraper_b.scrape.assert_called_once()


def test_stock_run_saves_aggregated_results():
    scraper_a = MagicMock()
    scraper_a.scrape.return_value = [_make_stock("HPG")]
    scraper_b = MagicMock()
    scraper_b.scrape.return_value = [_make_stock("VNM")]
    repo = MagicMock()

    StockCrawlRunner([scraper_a, scraper_b], repo).run()

    saved = repo.save.call_args[0][0]
    assert len(saved) == 2
    assert {r.symbol for r in saved} == {"HPG", "VNM"}


def test_stock_run_calls_save_once():
    scraper = MagicMock()
    scraper.scrape.return_value = [_make_stock("HPG")]
    repo = MagicMock()

    StockCrawlRunner([scraper], repo).run()

    repo.save.assert_called_once()


def test_stock_run_with_empty_scraper_list_saves_empty():
    repo = MagicMock()
    StockCrawlRunner([], repo).run()
    repo.save.assert_called_once_with([])
