#!/usr/bin/env python3
import os
from datetime import date, timedelta

from services.stock.repositories.csv import StockCSVRepository
from services.stock.scrapers.vnstock import VnstockScraper

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "stock")


def backfill(days: int = 30) -> None:
    repo = StockCSVRepository(data_dir=DATA_DIR)
    today = date.today()

    for i in range(1, days + 1):
        target = today - timedelta(days=i)

        if target.weekday() >= 5:  # skip Saturday/Sunday
            continue

        date_str = target.strftime("%Y-%m-%d")
        csv_path = os.path.join(DATA_DIR, f"stock_{date_str}.csv")

        if os.path.exists(csv_path):
            print(f"[skip]  {date_str} — already downloaded")
            continue

        print(f"[fetch] {date_str} …", flush=True)
        records = VnstockScraper(target_date=date_str).scrape()

        if records:
            repo.save(records)
            print(f"[done]  {date_str} — {len(records)} stocks")
        else:
            print(f"[empty] {date_str} — no data (holiday?)")


if __name__ == "__main__":
    backfill(days=30)
