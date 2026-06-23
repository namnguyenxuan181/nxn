import os
import pytest
from unittest.mock import patch, MagicMock
from interest.scrapers.multi_rate import MultiRateScraper

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "..", "fixtures", "techcombank_sample.html")


@pytest.fixture
def mock_response():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        html = f.read()
    mock = MagicMock()
    mock.text = html
    mock.raise_for_status = MagicMock()
    return mock


def test_scrape_returns_list(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    assert isinstance(records, list)


def test_scrape_returns_both_channels(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    channels = {r.channel for r in records}
    assert channels == {"counter", "online"}


def test_counter_techcombank_rates(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    tcb_counter = next(r for r in records if r.bank == "Techcombank" and r.channel == "counter")
    assert tcb_counter.rate_1m == 3.5
    assert tcb_counter.rate_3m == 4.0
    assert tcb_counter.rate_12m == 5.5
    assert tcb_counter.rate_18m is None


def test_online_techcombank_rates(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    tcb_online = next(r for r in records if r.bank == "Techcombank" and r.channel == "online")
    assert tcb_online.rate_1m == 3.7
    assert tcb_online.rate_18m is None


def test_dash_value_becomes_none(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    for r in records:
        assert r.rate_18m is None


def test_date_matches_today(mock_response):
    from datetime import date
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    assert all(r.date == date.today().strftime("%Y-%m-%d") for r in records)


def test_multiple_banks_parsed(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        records = MultiRateScraper().scrape()
    counter_banks = [r.bank for r in records if r.channel == "counter"]
    assert "Techcombank" in counter_banks
    assert "Vietcombank" in counter_banks


def test_scrape_calls_raise_for_status(mock_response):
    with patch("interest.scrapers.multi_rate.requests.get", return_value=mock_response):
        MultiRateScraper().scrape()
    mock_response.raise_for_status.assert_called_once()


_NO_THEAD_HTML = """<html><body>
<table>
  <tbody>
    <tr>
      <th>Ngân hàng</th><th>1 tháng</th><th>3 tháng</th>
      <th>6 tháng</th><th>12 tháng</th><th>18 tháng</th>
      <th>24 tháng</th><th>36 tháng</th>
    </tr>
    <tr>
      <td>Techcombank</td><td>3.5%/năm</td><td>4.0%/năm</td>
      <td>5.0%/năm</td><td>5.5%/năm</td><td>-</td>
      <td>5.8%/năm</td><td>6.0%/năm</td>
    </tr>
  </tbody>
</table>
<table>
  <tbody>
    <tr>
      <th>Ngân hàng</th><th>1 tháng</th><th>3 tháng</th>
      <th>6 tháng</th><th>12 tháng</th><th>18 tháng</th>
      <th>24 tháng</th><th>36 tháng</th>
    </tr>
    <tr>
      <td>Techcombank</td><td>3.7%/năm</td><td>4.2%/năm</td>
      <td>5.2%/năm</td><td>5.7%/năm</td><td>-</td>
      <td>6.0%/năm</td><td>6.2%/năm</td>
    </tr>
  </tbody>
</table>
</body></html>"""


def test_header_row_in_tbody_is_skipped():
    scraper = MultiRateScraper.__new__(MultiRateScraper)
    records = scraper._parse(_NO_THEAD_HTML)
    bank_names = [r.bank for r in records]
    assert "Ngân hàng" not in bank_names
    assert "Techcombank" in bank_names


def test_header_row_in_tbody_exact_record_count():
    scraper = MultiRateScraper.__new__(MultiRateScraper)
    records = scraper._parse(_NO_THEAD_HTML)
    assert len(records) == 2


_NGAN_HANG_TD_HTML = """<html><body>
<table>
  <tbody>
    <tr>
      <td>Ngân hàng</td><td>1 tháng</td><td>3 tháng</td>
      <td>6 tháng</td><td>12 tháng</td><td>18 tháng</td>
      <td>24 tháng</td><td>36 tháng</td>
    </tr>
    <tr>
      <td>Techcombank</td><td>3.5%/năm</td><td>4.0%/năm</td>
      <td>5.0%/năm</td><td>5.5%/năm</td><td>-</td>
      <td>5.8%/năm</td><td>6.0%/năm</td>
    </tr>
  </tbody>
</table>
<table>
  <tbody>
    <tr>
      <td>Ngân hàng</td><td>1 tháng</td><td>3 tháng</td>
      <td>6 tháng</td><td>12 tháng</td><td>18 tháng</td>
      <td>24 tháng</td><td>36 tháng</td>
    </tr>
    <tr>
      <td>Techcombank</td><td>3.7%/năm</td><td>4.2%/năm</td>
      <td>5.2%/năm</td><td>5.7%/năm</td><td>-</td>
      <td>6.0%/năm</td><td>6.2%/năm</td>
    </tr>
  </tbody>
</table>
</body></html>"""


def test_ngan_hang_td_row_is_skipped():
    scraper = MultiRateScraper.__new__(MultiRateScraper)
    records = scraper._parse(_NGAN_HANG_TD_HTML)
    bank_names = [r.bank for r in records]
    assert "Ngân hàng" not in bank_names
    assert "Techcombank" in bank_names
    assert len(records) == 2


_NOISY_RATES_HTML = """<html><body>
<table>
  <tbody>
    <tr>
      <td>Ngân hàng</td><td>1 tháng</td><td>3 tháng</td>
      <td>6 tháng</td><td>12 tháng</td><td>18 tháng</td>
      <td>24 tháng</td><td>36 tháng</td>
    </tr>
    <tr>
      <td>Techcombank</td>
      <td>4.40 Tham khảo: Biểu phí, lãi suất</td>
      <td>5.00 Tham khảo: Biểu phí, lãi suất</td>
      <td>5.50%/năm</td><td>6.00%/năm</td><td>-</td>
      <td>6.20%/năm</td><td>6.50%/năm</td>
    </tr>
  </tbody>
</table>
<table>
  <tbody>
    <tr>
      <td>Ngân hàng</td><td>1 tháng</td><td>3 tháng</td>
      <td>6 tháng</td><td>12 tháng</td><td>18 tháng</td>
      <td>24 tháng</td><td>36 tháng</td>
    </tr>
  </tbody>
</table>
</body></html>"""


def test_noisy_rate_extracts_leading_number():
    scraper = MultiRateScraper.__new__(MultiRateScraper)
    records = scraper._parse(_NOISY_RATES_HTML)
    assert len(records) == 1
    assert records[0].rate_1m == 4.40
    assert records[0].rate_3m == 5.00
    assert records[0].rate_6m == 5.50
