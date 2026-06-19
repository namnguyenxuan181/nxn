import pytest
from unittest.mock import MagicMock, patch

from stock.scrapers.vnstock import VnstockScraper, _fetch_ohlc, _to_vnd
from stock.model import StockPrice

_SAMPLE_CSV = "ticker,comGroupCode\nHPG,HOSE\nVNM,HOSE\nVCB,HOSE\n"

_SAMPLE_OHLC = {
    "t": [1781748000],
    "o": [24.05],
    "h": [24.15],
    "l": [23.65],
    "c": [23.65],
    "v": [18040500],
    "nextTime": 0,
}


def _listing_mock(csv_text: str = _SAMPLE_CSV) -> MagicMock:
    m = MagicMock()
    m.text = csv_text
    m.raise_for_status = MagicMock()
    return m


def _ohlc_mock(data: dict = _SAMPLE_OHLC) -> MagicMock:
    m = MagicMock()
    m.json.return_value = data
    m.raise_for_status = MagicMock()
    return m


def _side_effect_factory(listing_csv=_SAMPLE_CSV, ohlc_data=_SAMPLE_OHLC):
    def side_effect(url, **kwargs):
        if "github" in url:
            return _listing_mock(listing_csv)
        return _ohlc_mock(ohlc_data)
    return side_effect


def test_to_vnd_converts_correctly():
    assert _to_vnd(24.05) == 24050
    assert _to_vnd(23.65) == 23650
    assert _to_vnd(7.38) == 7380


def test_fetch_ohlc_returns_stock_price():
    with patch("stock.scrapers.vnstock.requests.get", return_value=_ohlc_mock()):
        result = _fetch_ohlc("HPG", "2026-06-18")
    assert result is not None
    assert result.symbol == "HPG"
    assert result.date == "2026-06-18"
    assert result.open == 24050
    assert result.high == 24150
    assert result.low == 23650
    assert result.close == 23650
    assert result.volume == 18040500


def test_fetch_ohlc_returns_none_when_no_data():
    empty = {"t": [], "o": [], "h": [], "l": [], "c": [], "v": [], "nextTime": 0}
    with patch("stock.scrapers.vnstock.requests.get", return_value=_ohlc_mock(empty)):
        result = _fetch_ohlc("HPG", "2026-06-18")
    assert result is None


def test_fetch_ohlc_returns_none_on_network_error():
    with patch("stock.scrapers.vnstock.requests.get", side_effect=Exception("timeout")):
        result = _fetch_ohlc("HPG", "2026-06-18")
    assert result is None


def test_get_symbols_parses_csv():
    scraper = VnstockScraper(target_date="2026-06-18")
    with patch("stock.scrapers.vnstock.requests.get", return_value=_listing_mock()):
        symbols = scraper._get_symbols()
    assert symbols == ["HPG", "VNM", "VCB"]


def test_scrape_returns_sorted_results():
    scraper = VnstockScraper(target_date="2026-06-18", max_workers=2)
    with patch("stock.scrapers.vnstock.requests.get", side_effect=_side_effect_factory()):
        results = scraper.scrape()
    symbols = [r.symbol for r in results]
    assert symbols == sorted(symbols)
    assert len(results) == 3


def test_scrape_filters_none_results():
    empty_ohlc = {"t": [], "o": [], "h": [], "l": [], "c": [], "v": [], "nextTime": 0}
    scraper = VnstockScraper(target_date="2026-06-18", max_workers=2)
    with patch(
        "stock.scrapers.vnstock.requests.get",
        side_effect=_side_effect_factory(ohlc_data=empty_ohlc),
    ):
        results = scraper.scrape()
    assert results == []


def test_scrape_uses_yesterday_as_default_date():
    from datetime import date, timedelta
    scraper = VnstockScraper()
    assert scraper._date == (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")


def test_scrape_raises_when_listing_fetch_fails():
    scraper = VnstockScraper(target_date="2026-06-18")
    with patch("stock.scrapers.vnstock.requests.get", side_effect=Exception("network error")):
        with pytest.raises(Exception):
            scraper.scrape()
