import re
from datetime import date
from typing import Optional

import requests
from bs4 import BeautifulSoup

from models.interest_rate import InterestRate
from scrapers.base import BaseScraper

_URL = "https://techcombank.com/thong-tin/blog/lai-suat-tiet-kiem"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _parse_rate(text: str) -> Optional[float]:
    text = text.strip()
    if not text or text in ("-", "—", "N/A", "n/a"):
        return None
    text = re.sub(r"[%/\s]|năm", "", text)
    try:
        return float(text)
    except ValueError:
        return None


class TechcombankScraper(BaseScraper):
    def scrape(self) -> list[InterestRate]:
        response = requests.get(_URL, headers=_HEADERS, timeout=30)
        response.raise_for_status()
        return self._parse(response.text)

    def _parse(self, html: str) -> list[InterestRate]:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        today = date.today().strftime("%Y-%m-%d")
        records: list[InterestRate] = []
        channels = ["counter", "online"]
        for table, channel in zip(tables[:2], channels):
            records.extend(self._parse_table(table, channel, today))
        return records

    def _parse_table(self, table, channel: str, today: str) -> list[InterestRate]:
        records = []
        for row in table.find("tbody").find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 8:
                continue
            bank = cells[0].get_text(strip=True)
            if not bank:
                continue
            records.append(InterestRate(
                date=today,
                bank=bank,
                channel=channel,
                rate_1m=_parse_rate(cells[1].get_text(strip=True)),
                rate_3m=_parse_rate(cells[2].get_text(strip=True)),
                rate_6m=_parse_rate(cells[3].get_text(strip=True)),
                rate_12m=_parse_rate(cells[4].get_text(strip=True)),
                rate_18m=_parse_rate(cells[5].get_text(strip=True)),
                rate_24m=_parse_rate(cells[6].get_text(strip=True)),
                rate_36m=_parse_rate(cells[7].get_text(strip=True)),
            ))
        return records
