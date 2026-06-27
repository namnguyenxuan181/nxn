from abc import ABC, abstractmethod
from services.stock.model import StockPrice


class BaseStockScraper(ABC):
    @abstractmethod
    def scrape(self) -> list[StockPrice]:
        pass
