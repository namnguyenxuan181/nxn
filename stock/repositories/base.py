from abc import ABC, abstractmethod
from stock.model import StockPrice


class BaseStockRepository(ABC):
    @abstractmethod
    def save(self, records: list[StockPrice]) -> None:
        pass
