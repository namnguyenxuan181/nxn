import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from stock.scrapers.intraday import is_market_open, fetch_intraday_prices

_VN_TZ = timezone(timedelta(hours=7))


def _make_dt(weekday: int, hour: int) -> datetime:
    from datetime import date, timedelta as td
    base = date(2026, 6, 22)  # Monday
    delta = (weekday - base.weekday()) % 7
    d = base + td(days=delta)
    return datetime(d.year, d.month, d.day, hour, 0, tzinfo=_VN_TZ)


def test_is_market_open_weekday_morning():
    with patch("stock.scrapers.intraday.datetime") as mock_dt:
        mock_dt.now.return_value = _make_dt(0, 10)  # Monday 10:00
        assert is_market_open() is True


def test_is_market_open_weekday_before_open():
    with patch("stock.scrapers.intraday.datetime") as mock_dt:
        mock_dt.now.return_value = _make_dt(0, 8)  # Monday 08:00
        assert is_market_open() is False


def test_is_market_open_weekday_after_close():
    with patch("stock.scrapers.intraday.datetime") as mock_dt:
        mock_dt.now.return_value = _make_dt(0, 15)  # Monday 15:00
        assert is_market_open() is False


def test_is_market_open_saturday():
    with patch("stock.scrapers.intraday.datetime") as mock_dt:
        mock_dt.now.return_value = _make_dt(5, 10)  # Saturday 10:00
        assert is_market_open() is False


def test_fetch_intraday_prices_returns_vnd():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "t": [1782190000],
        "o": [32.0], "h": [32.1], "l": [31.9],
        "c": [32.05],
        "v": [100000],
    }
    with patch("stock.scrapers.intraday.requests.get", return_value=mock_resp):
        result = fetch_intraday_prices(["TCB"])
    assert result == {"TCB": 32050}


def test_fetch_intraday_prices_skips_empty_symbol():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"t": [], "c": []}
    with patch("stock.scrapers.intraday.requests.get", return_value=mock_resp):
        result = fetch_intraday_prices(["XXX"])
    assert result == {}


def test_fetch_intraday_prices_skips_on_exception():
    with patch("stock.scrapers.intraday.requests.get", side_effect=Exception("timeout")):
        result = fetch_intraday_prices(["TCB"])
    assert result == {}


def test_fetch_intraday_prices_multiple_symbols():
    def _side_effect(url, params, headers, timeout):
        sym = params["symbol"]
        mock = MagicMock()
        mock.raise_for_status = MagicMock()
        if sym == "TCB":
            mock.json.return_value = {"t": [1], "c": [32.05], "o": [32.0], "h": [32.1], "l": [31.9], "v": [100]}
        else:
            mock.json.return_value = {"t": [1], "c": [100.0], "o": [99.0], "h": [101.0], "l": [98.0], "v": [200]}
        return mock

    with patch("stock.scrapers.intraday.requests.get", side_effect=_side_effect):
        result = fetch_intraday_prices(["TCB", "VCB"])
    assert result["TCB"] == 32050
    assert result["VCB"] == 100000
