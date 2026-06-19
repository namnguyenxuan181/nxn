from abc import ABC, abstractmethod
from stock.model import StockPrice


class BaseStockScraper(ABC):
    @abstractmethod
    def scrape(self) -> list[StockPrice]:
        pass
