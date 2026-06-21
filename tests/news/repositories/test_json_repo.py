import json
import os
from news.model import NewsArticle
from news.repositories.json_repo import JSONNewsRepository


def _make_article(source: str, title: str, url: str) -> NewsArticle:
    return NewsArticle(
        source=source, title=title, url=url,
        published_at="2026-06-21T08:00:00+07:00",
        description="desc", summary="Tóm tắt.", sentiment="positive",
    )


def test_save_creates_json_file(tmp_path):
    repo = JSONNewsRepository(data_dir=str(tmp_path))
    repo.save([_make_article("vnexpress", "Title", "https://vnexpress.net/1.html")], "2026-06-21")
    assert (tmp_path / "news_2026-06-21.json").exists()


def test_save_writes_correct_fields(tmp_path):
    repo = JSONNewsRepository(data_dir=str(tmp_path))
    repo.save([_make_article("cafef", "Lãi suất", "https://cafef.vn/1.html")], "2026-06-21")
    with open(tmp_path / "news_2026-06-21.json", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["source"] == "cafef"
    assert data[0]["title"] == "Lãi suất"
    assert data[0]["sentiment"] == "positive"


def test_load_returns_articles(tmp_path):
    repo = JSONNewsRepository(data_dir=str(tmp_path))
    repo.save([_make_article("vietstock", "MSCI", "https://vietstock.vn/1.htm")], "2026-06-21")
    loaded = repo.load("2026-06-21")
    assert len(loaded) == 1
    assert loaded[0].source == "vietstock"
    assert loaded[0].sentiment == "positive"


def test_load_returns_empty_when_no_file(tmp_path):
    repo = JSONNewsRepository(data_dir=str(tmp_path))
    assert repo.load("2026-06-21") == []


def test_save_does_nothing_for_empty_list(tmp_path):
    repo = JSONNewsRepository(data_dir=str(tmp_path))
    repo.save([], "2026-06-21")
    assert not any(tmp_path.iterdir())


def test_save_creates_data_dir_if_missing(tmp_path):
    data_dir = str(tmp_path / "news")
    repo = JSONNewsRepository(data_dir=data_dir)
    repo.save([_make_article("vnexpress", "T", "https://v.net/1.html")], "2026-06-21")
    assert os.path.isdir(data_dir)
