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
