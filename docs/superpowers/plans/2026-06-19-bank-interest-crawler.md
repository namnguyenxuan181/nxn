# Bank Interest Rate Crawler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crawl Vietnamese bank savings interest rates from Techcombank's comparison page daily and save to dated CSV files.

**Architecture:** Strategy + Repository pattern. `BaseScraper` defines the scraping contract; `TechcombankScraper` implements it for the target URL. `BaseRepository` defines the persistence contract; `CSVRepository` writes to `data/interest_YYYY-MM-DD.csv`. `CrawlRunner` wires them together.

**Tech Stack:** Python 3.9+, requests, beautifulsoup4, pytest, crontab (system)

## Global Constraints

- Python 3.9+ (available at `/usr/bin/python3`)
- Rate values: `Optional[float]` — strip `%/năm`, cast to float; `-`, `N/A`, empty → `None`
- CSV columns (in order): `date, bank, channel, rate_1m, rate_3m, rate_6m, rate_12m, rate_18m, rate_24m, rate_36m`
- Channel values: exactly `"counter"` or `"online"`
- Output file: `data/interest_YYYY-MM-DD.csv` relative to project root
- None → empty CSV cell (not the string `"None"`)
- Source URL: `https://techcombank.com/thong-tin/blog/lai-suat-tiet-kiem`

---

### Task 1: Project Scaffolding + Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `models/__init__.py`
- Create: `scrapers/__init__.py`
- Create: `repositories/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/fixtures/` (directory)
- Create: `data/.gitkeep`

**Interfaces:**
- Produces: virtualenv at `venv/`, all deps installed, `pytest` runnable

- [ ] **Step 1: Create requirements.txt**

```
requests==2.31.0
beautifulsoup4==4.12.3
```

- [ ] **Step 2: Create requirements-dev.txt**

```
-r requirements.txt
pytest==8.2.0
pytest-mock==3.14.0
```

- [ ] **Step 3: Create virtualenv and install dependencies**

```bash
cd /Users/namnx/Documents/project/nxn
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

Expected output ends with: `Successfully installed ...`

- [ ] **Step 4: Create package init files and data directory**

```bash
touch models/__init__.py scrapers/__init__.py repositories/__init__.py tests/__init__.py
mkdir -p tests/fixtures data
touch data/.gitkeep
```

- [ ] **Step 5: Verify pytest runs**

```bash
source venv/bin/activate
pytest --collect-only
```

Expected: `no tests ran` (zero errors, just no tests yet)

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt requirements-dev.txt models/__init__.py scrapers/__init__.py repositories/__init__.py tests/__init__.py data/.gitkeep
git commit -m "chore: scaffold project structure and dependencies"
```

---

### Task 2: InterestRate Data Model

**Files:**
- Create: `models/interest_rate.py`
- Create: `tests/test_interest_rate.py`

**Interfaces:**
- Produces: `InterestRate` dataclass importable from `models.interest_rate`

- [ ] **Step 1: Write failing tests**

Create `tests/test_interest_rate.py`:

```python
from models.interest_rate import InterestRate


def test_interest_rate_has_all_fields():
    record = InterestRate(
        date="2026-06-19",
        bank="Techcombank",
        channel="counter",
        rate_1m=3.5,
        rate_3m=4.0,
        rate_6m=5.0,
        rate_12m=5.5,
        rate_18m=None,
        rate_24m=5.8,
        rate_36m=6.0,
    )
    assert record.date == "2026-06-19"
    assert record.bank == "Techcombank"
    assert record.channel == "counter"
    assert record.rate_1m == 3.5
    assert record.rate_18m is None


def test_interest_rate_fields_are_typed_correctly():
    record = InterestRate(
        date="2026-06-19",
        bank="VCB",
        channel="online",
        rate_1m=3.2,
        rate_3m=None,
        rate_6m=4.5,
        rate_12m=5.0,
        rate_18m=None,
        rate_24m=5.5,
        rate_36m=5.8,
    )
    assert isinstance(record.rate_1m, float)
    assert record.rate_3m is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source venv/bin/activate
pytest tests/test_interest_rate.py -v
```

Expected: `ModuleNotFoundError: No module named 'models.interest_rate'`

- [ ] **Step 3: Implement the model**

Create `models/interest_rate.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_interest_rate.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add models/interest_rate.py tests/test_interest_rate.py
git commit -m "feat: add InterestRate dataclass"
```

---

### Task 3: Base Abstractions

**Files:**
- Create: `scrapers/base.py`
- Create: `repositories/base.py`
- Create: `tests/test_base_abstractions.py`

**Interfaces:**
- Consumes: `InterestRate` from `models.interest_rate`
- Produces:
  - `BaseScraper` with abstract `scrape(self) -> list[InterestRate]`
  - `BaseRepository` with abstract `save(self, records: list[InterestRate]) -> None`

- [ ] **Step 1: Write failing tests**

Create `tests/test_base_abstractions.py`:

```python
import pytest
from scrapers.base import BaseScraper
from repositories.base import BaseRepository
from models.interest_rate import InterestRate


def test_base_scraper_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseScraper()


def test_base_repository_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseRepository()


def test_concrete_scraper_must_implement_scrape():
    class IncompleteScraper(BaseScraper):
        pass
    with pytest.raises(TypeError):
        IncompleteScraper()


def test_concrete_repository_must_implement_save():
    class IncompleteRepository(BaseRepository):
        pass
    with pytest.raises(TypeError):
        IncompleteRepository()


def test_concrete_scraper_works_when_scrape_implemented():
    class OkScraper(BaseScraper):
        def scrape(self) -> list[InterestRate]:
            return []
    assert OkScraper().scrape() == []


def test_concrete_repository_works_when_save_implemented():
    class OkRepository(BaseRepository):
        def save(self, records: list[InterestRate]) -> None:
            pass
    OkRepository().save([])
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_base_abstractions.py -v
```

Expected: `ModuleNotFoundError: No module named 'scrapers.base'`

- [ ] **Step 3: Implement BaseScraper**

Create `scrapers/base.py`:

```python
from abc import ABC, abstractmethod
from models.interest_rate import InterestRate


class BaseScraper(ABC):
    @abstractmethod
    def scrape(self) -> list[InterestRate]:
        pass
```

- [ ] **Step 4: Implement BaseRepository**

Create `repositories/base.py`:

```python
from abc import ABC, abstractmethod
from models.interest_rate import InterestRate


class BaseRepository(ABC):
    @abstractmethod
    def save(self, records: list[InterestRate]) -> None:
        pass
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_base_abstractions.py -v
```

Expected: `6 passed`

- [ ] **Step 6: Commit**

```bash
git add scrapers/base.py repositories/base.py tests/test_base_abstractions.py
git commit -m "feat: add BaseScraper and BaseRepository abstractions"
```

---

### Task 4: CSVRepository

**Files:**
- Create: `repositories/csv_repository.py`
- Create: `tests/test_csv_repository.py`

**Interfaces:**
- Consumes: `BaseRepository` from `repositories.base`, `InterestRate` from `models.interest_rate`
- Produces: `CSVRepository(data_dir: str)` — `save(records)` writes `<data_dir>/interest_YYYY-MM-DD.csv`

- [ ] **Step 1: Write failing tests**

Create `tests/test_csv_repository.py`:

```python
import csv
import os
import pytest
from repositories.csv_repository import CSVRepository
from models.interest_rate import InterestRate


@pytest.fixture
def tmp_repo(tmp_path):
    return CSVRepository(data_dir=str(tmp_path))


@pytest.fixture
def sample_records():
    return [
        InterestRate("2026-06-19", "Techcombank", "counter", 3.5, 4.0, 5.0, 5.5, None, 5.8, 6.0),
        InterestRate("2026-06-19", "Vietcombank", "online",  3.2, 3.8, 4.5, 5.0, None, 5.5, 5.8),
    ]


def test_creates_csv_file(tmp_repo, sample_records, tmp_path):
    tmp_repo.save(sample_records)
    assert os.path.exists(os.path.join(str(tmp_path), "interest_2026-06-19.csv"))


def test_csv_has_correct_header(tmp_repo, sample_records, tmp_path):
    tmp_repo.save(sample_records)
    with open(os.path.join(str(tmp_path), "interest_2026-06-19.csv")) as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == ["date", "bank", "channel", "rate_1m", "rate_3m", "rate_6m",
                      "rate_12m", "rate_18m", "rate_24m", "rate_36m"]


def test_csv_none_written_as_empty_string(tmp_repo, sample_records, tmp_path):
    tmp_repo.save(sample_records)
    with open(os.path.join(str(tmp_path), "interest_2026-06-19.csv")) as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        row = next(reader)
    assert row[7] == ""  # rate_18m is None → empty cell


def test_csv_float_values_written_correctly(tmp_repo, sample_records, tmp_path):
    tmp_repo.save(sample_records)
    with open(os.path.join(str(tmp_path), "interest_2026-06-19.csv")) as f:
        reader = csv.reader(f)
        next(reader)
        row = next(reader)
    assert row[3] == "3.5"   # rate_1m
    assert row[4] == "4.0"   # rate_3m


def test_creates_data_dir_if_not_exists(tmp_path):
    nested = os.path.join(str(tmp_path), "nested", "data")
    repo = CSVRepository(data_dir=nested)
    records = [InterestRate("2026-06-19", "BankA", "counter", 3.0, 3.5, 4.0, 4.5, None, 5.0, 5.5)]
    repo.save(records)
    assert os.path.exists(os.path.join(nested, "interest_2026-06-19.csv"))
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_csv_repository.py -v
```

Expected: `ModuleNotFoundError: No module named 'repositories.csv_repository'`

- [ ] **Step 3: Implement CSVRepository**

Create `repositories/csv_repository.py`:

```python
import csv
import os
from repositories.base import BaseRepository
from models.interest_rate import InterestRate

_HEADERS = ["date", "bank", "channel", "rate_1m", "rate_3m", "rate_6m",
            "rate_12m", "rate_18m", "rate_24m", "rate_36m"]


class CSVRepository(BaseRepository):
    def __init__(self, data_dir: str = "data"):
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
                    "" if r.rate_1m  is None else r.rate_1m,
                    "" if r.rate_3m  is None else r.rate_3m,
                    "" if r.rate_6m  is None else r.rate_6m,
                    "" if r.rate_12m is None else r.rate_12m,
                    "" if r.rate_18m is None else r.rate_18m,
                    "" if r.rate_24m is None else r.rate_24m,
                    "" if r.rate_36m is None else r.rate_36m,
                ])
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_csv_repository.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add repositories/csv_repository.py tests/test_csv_repository.py
git commit -m "feat: add CSVRepository"
```

---

### Task 5: TechcombankScraper

**Files:**
- Create: `scrapers/techcombank.py`
- Create: `tests/fixtures/techcombank_sample.html`
- Create: `tests/test_techcombank_scraper.py`

**Interfaces:**
- Consumes: `BaseScraper` from `scrapers.base`, `InterestRate` from `models.interest_rate`
- Produces: `TechcombankScraper()` — `scrape() -> list[InterestRate]`

- [ ] **Step 1: Create HTML fixture**

Create `tests/fixtures/techcombank_sample.html`:

```html
<!DOCTYPE html>
<html>
<body>
  <h2>Lãi suất gửi tiết kiệm tại quầy</h2>
  <table>
    <thead>
      <tr>
        <th>Ngân hàng</th>
        <th>1 tháng</th>
        <th>3 tháng</th>
        <th>6 tháng</th>
        <th>12 tháng</th>
        <th>18 tháng</th>
        <th>24 tháng</th>
        <th>36 tháng</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Techcombank</td>
        <td>3.5%/năm</td>
        <td>4.0%/năm</td>
        <td>5.0%/năm</td>
        <td>5.5%/năm</td>
        <td>-</td>
        <td>5.8%/năm</td>
        <td>6.0%/năm</td>
      </tr>
      <tr>
        <td>Vietcombank</td>
        <td>3.2%/năm</td>
        <td>3.8%/năm</td>
        <td>4.5%/năm</td>
        <td>5.0%/năm</td>
        <td>-</td>
        <td>5.5%/năm</td>
        <td>5.8%/năm</td>
      </tr>
    </tbody>
  </table>
  <h2>Lãi suất gửi tiết kiệm online</h2>
  <table>
    <thead>
      <tr>
        <th>Ngân hàng</th>
        <th>1 tháng</th>
        <th>3 tháng</th>
        <th>6 tháng</th>
        <th>12 tháng</th>
        <th>18 tháng</th>
        <th>24 tháng</th>
        <th>36 tháng</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Techcombank</td>
        <td>3.7%/năm</td>
        <td>4.2%/năm</td>
        <td>5.2%/năm</td>
        <td>5.7%/năm</td>
        <td>-</td>
        <td>6.0%/năm</td>
        <td>6.2%/năm</td>
      </tr>
    </tbody>
  </table>
</body>
</html>
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_techcombank_scraper.py`:

```python
import os
import pytest
from unittest.mock import patch, MagicMock
from scrapers.techcombank import TechcombankScraper

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "techcombank_sample.html")


@pytest.fixture
def mock_response():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        html = f.read()
    mock = MagicMock()
    mock.text = html
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def scraper(mock_response):
    with patch("scrapers.techcombank.requests.get", return_value=mock_response):
        s = TechcombankScraper()
        s._html = mock_response.text
        return s


def test_scrape_returns_list(mock_response):
    with patch("scrapers.techcombank.requests.get", return_value=mock_response):
        records = TechcombankScraper().scrape()
    assert isinstance(records, list)


def test_scrape_returns_both_channels(mock_response):
    with patch("scrapers.techcombank.requests.get", return_value=mock_response):
        records = TechcombankScraper().scrape()
    channels = {r.channel for r in records}
    assert channels == {"counter", "online"}


def test_counter_techcombank_rates(mock_response):
    with patch("scrapers.techcombank.requests.get", return_value=mock_response):
        records = TechcombankScraper().scrape()
    tcb_counter = next(r for r in records if r.bank == "Techcombank" and r.channel == "counter")
    assert tcb_counter.rate_1m == 3.5
    assert tcb_counter.rate_3m == 4.0
    assert tcb_counter.rate_12m == 5.5
    assert tcb_counter.rate_18m is None


def test_online_techcombank_rates(mock_response):
    with patch("scrapers.techcombank.requests.get", return_value=mock_response):
        records = TechcombankScraper().scrape()
    tcb_online = next(r for r in records if r.bank == "Techcombank" and r.channel == "online")
    assert tcb_online.rate_1m == 3.7
    assert tcb_online.rate_18m is None


def test_dash_value_becomes_none(mock_response):
    with patch("scrapers.techcombank.requests.get", return_value=mock_response):
        records = TechcombankScraper().scrape()
    for r in records:
        assert r.rate_18m is None


def test_date_matches_today(mock_response):
    from datetime import date
    with patch("scrapers.techcombank.requests.get", return_value=mock_response):
        records = TechcombankScraper().scrape()
    assert all(r.date == date.today().strftime("%Y-%m-%d") for r in records)


def test_multiple_banks_parsed(mock_response):
    with patch("scrapers.techcombank.requests.get", return_value=mock_response):
        records = TechcombankScraper().scrape()
    counter_banks = [r.bank for r in records if r.channel == "counter"]
    assert "Techcombank" in counter_banks
    assert "Vietcombank" in counter_banks
```

- [ ] **Step 3: Run to verify failure**

```bash
pytest tests/test_techcombank_scraper.py -v
```

Expected: `ModuleNotFoundError: No module named 'scrapers.techcombank'`

- [ ] **Step 4: Implement TechcombankScraper**

Create `scrapers/techcombank.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_techcombank_scraper.py -v
```

Expected: `8 passed`

- [ ] **Step 6: Verify against real page (manual check)**

Run this one-off diagnostic to confirm requests can reach the live page:

```bash
source venv/bin/activate
python3 -c "
import requests
r = requests.get(
    'https://techcombank.com/thong-tin/blog/lai-suat-tiet-kiem',
    headers={'User-Agent': 'Mozilla/5.0'},
    timeout=30
)
from bs4 import BeautifulSoup
soup = BeautifulSoup(r.text, 'html.parser')
tables = soup.find_all('table')
print(f'Tables found: {len(tables)}')
if tables:
    rows = tables[0].find_all('tr')
    print(f'Rows in first table: {len(rows)}')
    print('First data row:', [c.get_text(strip=True) for c in rows[1].find_all(['td','th'])])
"
```

**Expected:** `Tables found: 2`, rows with bank names and rates.

**If `Tables found: 0`:** The page renders via JavaScript. In that case, replace the `requests.get(...)` call in `TechcombankScraper.scrape()` with Playwright:

```bash
pip install playwright && python3 -m playwright install chromium
```

```python
# Replacement for the requests.get block in scrape():
from playwright.sync_api import sync_playwright

def scrape(self) -> list[InterestRate]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(_URL)
        page.wait_for_selector("table", timeout=15000)
        html = page.content()
        browser.close()
    return self._parse(html)
```

- [ ] **Step 7: Commit**

```bash
git add scrapers/techcombank.py tests/fixtures/techcombank_sample.html tests/test_techcombank_scraper.py
git commit -m "feat: add TechcombankScraper"
```

---

### Task 6: CrawlRunner

**Files:**
- Create: `runner.py`
- Create: `tests/test_runner.py`

**Interfaces:**
- Consumes: `BaseScraper`, `BaseRepository`, `InterestRate`
- Produces: `CrawlRunner(scrapers: list[BaseScraper], repository: BaseRepository)` with `run() -> None`

- [ ] **Step 1: Write failing tests**

Create `tests/test_runner.py`:

```python
from unittest.mock import MagicMock, call
from runner import CrawlRunner
from models.interest_rate import InterestRate


def _make_record(bank: str) -> InterestRate:
    return InterestRate("2026-06-19", bank, "counter", 3.5, 4.0, 5.0, 5.5, None, 5.8, 6.0)


def test_run_calls_all_scrapers():
    scraper_a = MagicMock()
    scraper_a.scrape.return_value = [_make_record("BankA")]
    scraper_b = MagicMock()
    scraper_b.scrape.return_value = [_make_record("BankB")]
    repo = MagicMock()

    CrawlRunner([scraper_a, scraper_b], repo).run()

    scraper_a.scrape.assert_called_once()
    scraper_b.scrape.assert_called_once()


def test_run_saves_aggregated_results():
    scraper_a = MagicMock()
    scraper_a.scrape.return_value = [_make_record("BankA")]
    scraper_b = MagicMock()
    scraper_b.scrape.return_value = [_make_record("BankB")]
    repo = MagicMock()

    CrawlRunner([scraper_a, scraper_b], repo).run()

    saved = repo.save.call_args[0][0]
    assert len(saved) == 2
    assert {r.bank for r in saved} == {"BankA", "BankB"}


def test_run_calls_save_once():
    scraper = MagicMock()
    scraper.scrape.return_value = [_make_record("BankA")]
    repo = MagicMock()

    CrawlRunner([scraper], repo).run()

    repo.save.assert_called_once()


def test_run_with_empty_scraper_list_saves_empty():
    repo = MagicMock()
    CrawlRunner([], repo).run()
    repo.save.assert_called_once_with([])
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_runner.py -v
```

Expected: `ModuleNotFoundError: No module named 'runner'`

- [ ] **Step 3: Implement CrawlRunner**

Create `runner.py`:

```python
from scrapers.base import BaseScraper
from repositories.base import BaseRepository
from models.interest_rate import InterestRate


class CrawlRunner:
    def __init__(self, scrapers: list[BaseScraper], repository: BaseRepository):
        self._scrapers = scrapers
        self._repository = repository

    def run(self) -> None:
        records: list[InterestRate] = []
        for scraper in self._scrapers:
            records.extend(scraper.scrape())
        self._repository.save(records)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_runner.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add runner.py tests/test_runner.py
git commit -m "feat: add CrawlRunner"
```

---

### Task 7: main.py + setup_cron.sh

**Files:**
- Modify: `main.py` (replace all existing content)
- Create: `setup_cron.sh`

**Interfaces:**
- Consumes: `TechcombankScraper`, `CSVRepository`, `CrawlRunner`
- Produces: running `python3 main.py` creates `data/interest_YYYY-MM-DD.csv`

- [ ] **Step 1: Replace main.py entirely**

Overwrite `main.py` with:

```python
import os
import sys

from runner import CrawlRunner
from scrapers.techcombank import TechcombankScraper
from repositories.csv_repository import CSVRepository

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def main():
    scrapers = [TechcombankScraper()]
    repository = CSVRepository(data_dir=DATA_DIR)
    CrawlRunner(scrapers, repository).run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create setup_cron.sh**

Create `setup_cron.sh`:

```bash
#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$PROJECT_DIR/venv/bin/python3"
LOG="$PROJECT_DIR/data/cron.log"

CRON_JOB="0 8 * * * $PYTHON $PROJECT_DIR/main.py >> $LOG 2>&1"

# Add only if not already present
(crontab -l 2>/dev/null | grep -qF "$PROJECT_DIR/main.py") \
  && echo "Cron job already exists. No changes made." \
  || (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Cron job scheduled:"
crontab -l | grep "main.py"
```

- [ ] **Step 3: Make setup_cron.sh executable**

```bash
chmod +x setup_cron.sh
```

- [ ] **Step 4: Run full pipeline end-to-end**

```bash
source venv/bin/activate
python3 main.py
```

Expected: no errors. Then verify:

```bash
ls data/
```

Expected: `interest_2026-06-19.csv` (today's date) and `.gitkeep`

```bash
head -3 data/interest_$(date +%Y-%m-%d).csv
```

Expected: header row + data rows with float rates and empty cells for None values.

- [ ] **Step 5: Run all tests together**

```bash
pytest -v
```

Expected: all tests pass (no failures).

- [ ] **Step 6: Install cron job**

```bash
./setup_cron.sh
```

Expected output:
```
Cron job scheduled:
0 8 * * * /Users/namnx/Documents/project/nxn/venv/bin/python3 /Users/namnx/Documents/project/nxn/main.py >> /Users/namnx/Documents/project/nxn/data/cron.log 2>&1
```

- [ ] **Step 7: Commit**

```bash
git add main.py setup_cron.sh
git commit -m "feat: wire main entry point and cron setup"
```