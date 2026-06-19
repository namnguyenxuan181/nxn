from abc import ABC, abstractmethod
from models.stock_price import StockPrice


class BaseStockScraper(ABC):
    @abstractmethod
    def scrape(self) -> list[StockPrice]:
        pass
