import csv
import os

from models.stock_price import StockPrice
from repositories.base_stock import BaseStockRepository

_HEADERS = ["date", "symbol", "open", "high", "low", "close", "volume"]


class StockCSVRepository(BaseStockRepository):
    def __init__(self, data_dir: str = "data"):
        self._data_dir = data_dir

    def save(self, records: list[StockPrice]) -> None:
        if not records:
            return
        os.makedirs(self._data_dir, exist_ok=True)
        filename = os.path.join(self._data_dir, f"stock_{records[0].date}.csv")
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(_HEADERS)
            for r in records:
                writer.writerow([
                    r.date,
                    r.symbol,
                    "" if r.open is None else r.open,
                    "" if r.high is None else r.high,
                    "" if r.low is None else r.low,
                    "" if r.close is None else r.close,
                    "" if r.volume is None else r.volume,
                ])
