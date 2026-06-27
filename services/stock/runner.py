from services.stock.model import StockPrice
from services.stock.scrapers.base import BaseStockScraper
from services.stock.repositories.base import BaseStockRepository


class StockCrawlRunner:
    def __init__(self, scrapers: list[BaseStockScraper], repository: BaseStockRepository):
        self._scrapers = scrapers
        self._repository = repository

    def run(self) -> None:
        records: list[StockPrice] = []
        for scraper in self._scrapers:
            records.extend(scraper.scrape())
        self._repository.save(records)
