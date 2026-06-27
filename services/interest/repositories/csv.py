import csv
import os

from services.interest.model import InterestRate
from services.interest.repositories.base import BaseRepository

_HEADERS = ["date", "bank", "channel", "rate_1m", "rate_3m", "rate_6m",
            "rate_12m", "rate_18m", "rate_24m", "rate_36m"]


class CSVRepository(BaseRepository):
    def __init__(self, data_dir: str = "data/interest"):
        self._data_dir = data_dir

    def save(self, records: list[InterestRate]) -> None:
        if not records:
            return
        os.makedirs(self._data_dir, exist_ok=True)
        filename = os.path.join(self._data_dir, f"interest_{records[0].date}.csv")
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(_HEADERS)
            for r in records:
                writer.writerow([
                    r.date, r.bank, r.channel,
                    "" if r.rate_1m is None else r.rate_1m,
                    "" if r.rate_3m is None else r.rate_3m,
                    "" if r.rate_6m is None else r.rate_6m,
                    "" if r.rate_12m is None else r.rate_12m,
                    "" if r.rate_18m is None else r.rate_18m,
                    "" if r.rate_24m is None else r.rate_24m,
                    "" if r.rate_36m is None else r.rate_36m,
                ])
