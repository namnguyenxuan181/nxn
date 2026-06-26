import csv
import json
from datetime import date
from pathlib import Path

import pytest


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    (tmp_path / "stock").mkdir()
    (tmp_path / "news").mkdir()
    (tmp_path / "interest").mkdir()
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return tmp_path


def _write_stock(directory: Path, date_str: str, rows: list[dict]):
    path = directory / f"stock_{date_str}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "symbol", "open", "high", "low", "close", "volume"])
        w.writeheader()
        w.writerows(rows)


def _write_news(directory: Path, date_str: str, articles: list[dict]):
    (directory / f"news_{date_str}.json").write_text(json.dumps(articles), encoding="utf-8")


def _write_interest(directory: Path, date_str: str, rows: list[dict]):
    path = directory / f"interest_{date_str}.csv"
    fields = ["date", "bank", "channel", "rate_1m", "rate_3m", "rate_6m", "rate_12m", "rate_18m", "rate_24m", "rate_36m"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def test_get_all_symbols_returns_sorted(data_dir):
    _write_stock(data_dir / "stock", "2026-06-25", [
        {"date": "2026-06-25", "symbol": "VCB", "open": 80000, "high": 81000, "low": 79000, "close": 80500, "volume": 1000000},
        {"date": "2026-06-25", "symbol": "TCB", "open": 31000, "high": 32000, "low": 30000, "close": 31500, "volume": 500000},
    ])
    from ai_platform.data_access import get_all_symbols
    assert get_all_symbols() == ["TCB", "VCB"]


def test_get_all_symbols_empty_when_no_file(data_dir):
    from ai_platform.data_access import get_all_symbols
    assert get_all_symbols() == []


def test_get_latest_stock_filters_by_symbol(data_dir):
    _write_stock(data_dir / "stock", "2026-06-25", [
        {"date": "2026-06-25", "symbol": "TCB", "open": 31000, "high": 32000, "low": 30000, "close": 31500, "volume": 500000},
        {"date": "2026-06-25", "symbol": "VCB", "open": 80000, "high": 81000, "low": 79000, "close": 80500, "volume": 1000000},
    ])
    from ai_platform.data_access import get_latest_stock
    result = get_latest_stock(["TCB"])
    assert "TCB" in result
    assert result["TCB"].close == 31500
    assert "VCB" not in result


def test_get_previous_stock_reads_second_csv(data_dir):
    _write_stock(data_dir / "stock", "2026-06-24", [
        {"date": "2026-06-24", "symbol": "TCB", "open": 30000, "high": 31000, "low": 29000, "close": 30500, "volume": 400000},
    ])
    _write_stock(data_dir / "stock", "2026-06-25", [
        {"date": "2026-06-25", "symbol": "TCB", "open": 31000, "high": 32000, "low": 30000, "close": 31500, "volume": 500000},
    ])
    from ai_platform.data_access import get_previous_stock
    result = get_previous_stock(["TCB"])
    assert result["TCB"].close == 30500


def test_get_previous_stock_empty_when_only_one_csv(data_dir):
    _write_stock(data_dir / "stock", "2026-06-25", [
        {"date": "2026-06-25", "symbol": "TCB", "open": 31000, "high": 32000, "low": 30000, "close": 31500, "volume": 500000},
    ])
    from ai_platform.data_access import get_previous_stock
    assert get_previous_stock(["TCB"]) == {}


def test_get_stock_history_ordered_oldest_first(data_dir):
    _write_stock(data_dir / "stock", "2026-06-24", [
        {"date": "2026-06-24", "symbol": "TCB", "open": 30000, "high": 31000, "low": 29000, "close": 30500, "volume": 400000},
    ])
    _write_stock(data_dir / "stock", "2026-06-25", [
        {"date": "2026-06-25", "symbol": "TCB", "open": 31000, "high": 32000, "low": 30000, "close": 31500, "volume": 500000},
    ])
    from ai_platform.data_access import get_stock_history
    result = get_stock_history("TCB", days=10)
    assert len(result) == 2
    assert result[0].date == "2026-06-24"
    assert result[1].date == "2026-06-25"


def test_get_stock_history_empty_for_unknown_symbol(data_dir):
    _write_stock(data_dir / "stock", "2026-06-25", [
        {"date": "2026-06-25", "symbol": "TCB", "open": 31000, "high": 32000, "low": 30000, "close": 31500, "volume": 500000},
    ])
    from ai_platform.data_access import get_stock_history
    assert get_stock_history("UNKNOWN", days=10) == []


def test_get_recent_news_filters_by_symbol(data_dir):
    today = date.today().strftime("%Y-%m-%d")
    _write_news(data_dir / "news", today, [
        {"source": "VnExpress", "title": "TCB tăng mạnh", "url": "http://a.com", "published_at": "2026-06-25T10:00:00+07:00", "description": "Techcombank", "summary": "", "sentiment": "positive"},
        {"source": "CafeF", "title": "VN-Index hôm nay", "url": "http://b.com", "published_at": "2026-06-25T11:00:00+07:00", "description": "Thị trường", "summary": "", "sentiment": "neutral"},
    ])
    from ai_platform.data_access import get_recent_news
    result = get_recent_news(["TCB"], days=1)
    assert len(result) == 1
    assert result[0].title == "TCB tăng mạnh"


def test_get_recent_news_returns_all_when_no_symbols(data_dir):
    today = date.today().strftime("%Y-%m-%d")
    _write_news(data_dir / "news", today, [
        {"source": "VnExpress", "title": "Tin 1", "url": "http://a.com", "published_at": "2026-06-25T10:00:00", "description": "", "summary": "", "sentiment": "neutral"},
        {"source": "CafeF", "title": "Tin 2", "url": "http://b.com", "published_at": "2026-06-25T11:00:00", "description": "", "summary": "", "sentiment": "neutral"},
    ])
    from ai_platform.data_access import get_recent_news
    assert len(get_recent_news([], days=1)) == 2


def test_get_interest_rates_parses_csv(data_dir):
    _write_interest(data_dir / "interest", "2026-06-25", [
        {"date": "2026-06-25", "bank": "Techcombank", "channel": "online", "rate_1m": "3.5", "rate_3m": "4.0", "rate_6m": "5.0", "rate_12m": "6.0", "rate_18m": "", "rate_24m": "6.5", "rate_36m": ""},
    ])
    from ai_platform.data_access import get_interest_rates
    result = get_interest_rates()
    assert len(result) == 1
    assert result[0].bank == "Techcombank"
    assert result[0].rate_3m == 4.0
    assert result[0].rate_18m is None


def test_get_interest_rates_empty_when_no_file(data_dir):
    from ai_platform.data_access import get_interest_rates
    assert get_interest_rates() == []
