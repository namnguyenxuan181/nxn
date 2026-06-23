import json
import os
import pandas as pd
from unittest.mock import patch
from web.data_loader import available_dates, load_interest, load_stock, load_portfolio, load_intraday_prices


def _write_csv(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


_INTEREST_CSV = (
    "date,bank,channel,rate_1m,rate_3m,rate_6m,rate_12m,rate_18m,rate_24m,rate_36m\n"
    "2026-06-19,Techcombank,counter,4.4,4.7,6.4,6.6,,5.7,5.7\n"
)

_STOCK_CSV = (
    "date,symbol,open,high,low,close,volume\n"
    "2026-06-18,HPG,24050,24150,23650,23650,18040500\n"
)


def test_available_dates_returns_sorted_desc(tmp_path, monkeypatch):
    monkeypatch.setattr("web.data_loader.DATA_DIR", str(tmp_path))
    _write_csv(str(tmp_path / "interest" / "interest_2026-06-17.csv"), _INTEREST_CSV)
    _write_csv(str(tmp_path / "interest" / "interest_2026-06-19.csv"), _INTEREST_CSV)
    dates = available_dates("interest")
    assert dates == ["2026-06-19", "2026-06-17"]


def test_available_dates_returns_empty_when_no_files(tmp_path, monkeypatch):
    monkeypatch.setattr("web.data_loader.DATA_DIR", str(tmp_path))
    (tmp_path / "interest").mkdir()
    assert available_dates("interest") == []


def test_load_interest_returns_dataframe(tmp_path, monkeypatch):
    monkeypatch.setattr("web.data_loader.DATA_DIR", str(tmp_path))
    _write_csv(str(tmp_path / "interest" / "interest_2026-06-19.csv"), _INTEREST_CSV)
    df = load_interest("2026-06-19")
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == [
        "date", "bank", "channel",
        "rate_1m", "rate_3m", "rate_6m", "rate_12m",
        "rate_18m", "rate_24m", "rate_36m",
    ]
    assert len(df) == 1
    assert df.iloc[0]["bank"] == "Techcombank"


def test_load_stock_returns_dataframe(tmp_path, monkeypatch):
    monkeypatch.setattr("web.data_loader.DATA_DIR", str(tmp_path))
    _write_csv(str(tmp_path / "stock" / "stock_2026-06-18.csv"), _STOCK_CSV)
    df = load_stock("2026-06-18")
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["date", "symbol", "open", "high", "low", "close", "volume"]
    assert len(df) == 1
    assert df.iloc[0]["symbol"] == "HPG"
    assert df.iloc[0]["close"] == 23650


_PORTFOLIO = {
    "watchlist": ["TCB", "VCB"],
    "holdings": [{"symbol": "TCB", "quantity": 1000, "buy_price": 28500}],
}


def test_load_portfolio_returns_data(tmp_path, monkeypatch):
    p = tmp_path / "portfolio.json"
    p.write_text(json.dumps(_PORTFOLIO), encoding="utf-8")
    monkeypatch.setattr("web.data_loader._PORTFOLIO_PATH", str(p))
    result = load_portfolio()
    assert result["watchlist"] == ["TCB", "VCB"]
    assert len(result["holdings"]) == 1
    assert result["holdings"][0]["symbol"] == "TCB"


def test_load_portfolio_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("web.data_loader._PORTFOLIO_PATH", str(tmp_path / "missing.json"))
    result = load_portfolio()
    assert result == {"watchlist": [], "holdings": []}


def test_load_intraday_prices_skips_when_market_closed():
    with patch("stock.scrapers.intraday.is_market_open", return_value=False):
        result = load_intraday_prices(("TCB", "VCB"))
    assert result == {}


def test_load_intraday_prices_fetches_when_market_open():
    with patch("stock.scrapers.intraday.is_market_open", return_value=True), \
         patch("stock.scrapers.intraday.fetch_intraday_prices", return_value={"TCB": 32050}) as mock_fetch:
        result = load_intraday_prices(("TCB",))
    mock_fetch.assert_called_once_with(["TCB"])
    assert result == {"TCB": 32050}
