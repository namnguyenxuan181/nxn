# Bank Interest Rate Crawler — Design Spec

**Date:** 2026-06-19

## Overview

A Python crawler that daily scrapes Vietnamese bank savings interest rates from
`https://techcombank.com/thong-tin/blog/lai-suat-tiet-kiem`, saves results as a
dated CSV file, and runs automatically via crontab.

---

## Architecture

**Pattern:** Strategy + Repository

- `BaseScraper` (Strategy): abstract contract for scraping; each source = one concrete class
- `BaseRepository` (Repository): abstract contract for persistence; swap CSV → DB without touching scrapers
- `CrawlRunner`: orchestrates pipeline — collect → aggregate → save
- `main.py`: wires components and executes runner

Adding a new bank website = one new file in `scrapers/`, zero changes to existing code.

---

## Project Structure

```
nxn/
├── main.py                    # Entry point
├── runner.py                  # CrawlRunner
├── models/
│   ├── __init__.py
│   └── interest_rate.py       # InterestRate dataclass
├── scrapers/
│   ├── __init__.py
│   ├── base.py                # BaseScraper ABC
│   └── techcombank.py         # TechcombankScraper
├── repositories/
│   ├── __init__.py
│   ├── base.py                # BaseRepository ABC
│   └── csv_repository.py      # CSVRepository
├── data/                      # Output CSVs (git-ignored)
├── requirements.txt
└── setup_cron.sh              # Installs daily crontab entry
```

---

## Data Model

```python
@dataclass
class InterestRate:
    date: str                  # YYYY-MM-DD (crawl date)
    bank: str                  # Bank name as shown on page
    channel: str               # "counter" | "online"
    rate_1m: Optional[float]   # %/year e.g. 3.5; None if N/A
    rate_3m: Optional[float]
    rate_6m: Optional[float]
    rate_12m: Optional[float]
    rate_18m: Optional[float]
    rate_24m: Optional[float]
    rate_36m: Optional[float]
```

Rate parsing: strip `%`, `/năm`, whitespace → `float`. Values `-`, `N/A`, empty → `None`.

---

## Components

### `BaseScraper` (scrapers/base.py)
```python
class BaseScraper(ABC):
    @abstractmethod
    def scrape(self) -> list[InterestRate]: ...
```

### `TechcombankScraper` (scrapers/techcombank.py)
- Fetches `https://techcombank.com/thong-tin/blog/lai-suat-tiet-kiem` with `requests`
- Parses HTML with `BeautifulSoup`
- Extracts two tables: counter rates and online rates
- Returns `list[InterestRate]` for all 30+ banks × 2 channels

### `BaseRepository` (repositories/base.py)
```python
class BaseRepository(ABC):
    @abstractmethod
    def save(self, records: list[InterestRate]) -> None: ...
```

### `CSVRepository` (repositories/csv_repository.py)
- Writes to `data/interest_YYYY-MM-DD.csv`
- Creates `data/` directory if it doesn't exist
- Overwrites file if it already exists for today
- Empty rate → empty CSV cell (not "None" string)

### `CrawlRunner` (runner.py)
- Accepts `list[BaseScraper]` and one `BaseRepository`
- Calls each scraper's `scrape()`, aggregates results, calls `repository.save()`

### `main.py`
- Replaces existing placeholder content entirely
- Instantiates `TechcombankScraper`, `CSVRepository`, `CrawlRunner`
- Calls `runner.run()`

---

## CSV Output

File: `data/interest_YYYY-MM-DD.csv`

Columns:
```
date, bank, channel, rate_1m, rate_3m, rate_6m, rate_12m, rate_18m, rate_24m, rate_36m
```

Example rows:
```
2026-06-19,Techcombank,counter,3.5,4.0,5.0,5.5,,5.8,6.0
2026-06-19,Techcombank,online,3.7,4.2,5.2,5.7,,6.0,6.2
2026-06-19,Vietcombank,counter,3.2,3.8,4.5,5.0,,5.5,5.8
```

---

## Cron Setup

`setup_cron.sh` adds a crontab entry to run daily at 08:00:

```bash
0 8 * * * /usr/bin/python3 /path/to/nxn/main.py >> /path/to/nxn/data/cron.log 2>&1
```

The script uses the absolute path of the current directory so it works without manual editing.

---

## Dependencies

```
requests
beautifulsoup4
```

---

## Error Handling

- Network errors: exception propagates and is logged to stderr (cron captures to `cron.log`)
- Missing rate cell: parsed as `None`
- Table structure change: `IndexError`/`AttributeError` will surface clearly in `cron.log`