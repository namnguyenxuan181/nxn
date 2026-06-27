from dataclasses import dataclass
from typing import Optional


@dataclass
class InterestRate:
    date: str
    bank: str
    channel: str
    rate_1m: Optional[float]
    rate_3m: Optional[float]
    rate_6m: Optional[float]
    rate_12m: Optional[float]
    rate_18m: Optional[float]
    rate_24m: Optional[float]
    rate_36m: Optional[float]
