from abc import ABC, abstractmethod
from models.stock_price import StockPrice


class BaseStockRepository(ABC):
    @abstractmethod
    def save(self, records: list[StockPrice]) -> None:
        pass
