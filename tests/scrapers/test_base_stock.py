import pytest
from scrapers.base_stock import BaseStockScraper
from models.stock_price import StockPrice


def test_base_stock_scraper_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseStockScraper()


def test_concrete_stock_scraper_must_implement_scrape():
    class IncompleteStockScraper(BaseStockScraper):
        pass

    with pytest.raises(TypeError):
        IncompleteStockScraper()


def test_concrete_stock_scraper_works_when_scrape_implemented():
    class OkStockScraper(BaseStockScraper):
        def scrape(self) -> list[StockPrice]:
            return []

    assert OkStockScraper().scrape() == []
