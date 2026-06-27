import csv
import os
import pytest

from services.stock.repositories.csv import StockCSVRepository
from services.stock.model import StockPrice


def _make_records():
    return [
        StockPrice(date="2026-06-18", symbol="HPG", open=24050, high=24150, low=23650, close=23650, volume=18040500),
        StockPrice(date="2026-06-18", symbol="VNM", open=59500, high=59700, low=59100, close=59200, volume=2482800),
    ]


def test_save_creates_csv_file(tmp_path):
    repo = StockCSVRepository(data_dir=str(tmp_path))
    repo.save(_make_records())
    assert (tmp_path / "stock_2026-06-18.csv").exists()


def test_save_writes_correct_headers(tmp_path):
    repo = StockCSVRepository(data_dir=str(tmp_path))
    repo.save(_make_records())
    with open(tmp_path / "stock_2026-06-18.csv", encoding="utf-8") as f:
        headers = next(csv.reader(f))
    assert headers == ["date", "symbol", "open", "high", "low", "close", "volume"]


def test_save_writes_correct_data(tmp_path):
    repo = StockCSVRepository(data_dir=str(tmp_path))
    repo.save(_make_records())
    with open(tmp_path / "stock_2026-06-18.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]["symbol"] == "HPG"
    assert rows[0]["open"] == "24050"
    assert rows[0]["close"] == "23650"
    assert rows[1]["symbol"] == "VNM"
    assert rows[1]["close"] == "59200"


def test_save_writes_empty_string_for_none_values(tmp_path):
    repo = StockCSVRepository(data_dir=str(tmp_path))
    records = [StockPrice(date="2026-06-18", symbol="TST", open=None, high=None, low=None, close=None, volume=None)]
    repo.save(records)
    with open(tmp_path / "stock_2026-06-18.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["open"] == ""
    assert rows[0]["close"] == ""


def test_save_does_nothing_for_empty_records(tmp_path):
    repo = StockCSVRepository(data_dir=str(tmp_path))
    repo.save([])
    assert not any(tmp_path.iterdir())


def test_save_creates_data_dir_if_missing(tmp_path):
    data_dir = str(tmp_path / "new_dir")
    repo = StockCSVRepository(data_dir=data_dir)
    repo.save(_make_records())
    assert os.path.isdir(data_dir)
