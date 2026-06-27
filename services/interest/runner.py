from services.interest.model import InterestRate
from services.interest.scrapers.base import BaseScraper
from services.interest.repositories.base import BaseRepository


class CrawlRunner:
    def __init__(self, scrapers: list[BaseScraper], repository: BaseRepository):
        self._scrapers = scrapers
        self._repository = repository

    def run(self) -> None:
        records: list[InterestRate] = []
        for scraper in self._scrapers:
            records.extend(scraper.scrape())
        self._repository.save(records)
