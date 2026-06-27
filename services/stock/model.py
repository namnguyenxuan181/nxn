from dataclasses import dataclass
from typing import Optional


@dataclass
class StockPrice:
    date: str
    symbol: str
    open: Optional[int]
    high: Optional[int]
    low: Optional[int]
    close: Optional[int]
    volume: Optional[int]
