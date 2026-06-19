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


def test_scrape_calls_raise_for_status(mock_response):
    with patch("scrapers.techcombank.requests.get", return_value=mock_response):
        TechcombankScraper().scrape()
    mock_response.raise_for_status.assert_called_once()
