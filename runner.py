from scrapers.base import BaseScraper
from scrapers.base_stock import BaseStockScraper
from repositories.base import BaseRepository
from repositories.base_stock import BaseStockRepository
from models.interest_rate import InterestRate
from models.stock_price import StockPrice


class CrawlRunner:
    def __init__(self, scrapers: list[BaseScraper], repository: BaseRepository):
        self._scrapers = scrapers
        self._repository = repository

    def run(self) -> None:
        records: list[InterestRate] = []
        for scraper in self._scrapers:
            records.extend(scraper.scrape())
        self._repository.save(records)


class StockCrawlRunner:
    def __init__(self, scrapers: list[BaseStockScraper], repository: BaseStockRepository):
        self._scrapers = scrapers
        self._repository = repository

    def run(self) -> None:
        records: list[StockPrice] = []
        for scraper in self._scrapers:
            records.extend(scraper.scrape())
        self._repository.save(records)
