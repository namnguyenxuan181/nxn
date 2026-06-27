import dataclasses
import json
import os

from services.news.model import NewsArticle
from services.news.repositories.base import BaseNewsRepository


class JSONNewsRepository(BaseNewsRepository):
    def __init__(self, data_dir: str = "data/news"):
        self._data_dir = data_dir

    def _path(self, date: str) -> str:
        return os.path.join(self._data_dir, f"news_{date}.json")

    def load(self, date: str) -> list[NewsArticle]:
        path = self._path(date)
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [NewsArticle(**d) for d in data]

    def save(self, articles: list[NewsArticle], date: str) -> None:
        if not articles:
            return
        os.makedirs(self._data_dir, exist_ok=True)
        with open(self._path(date), "w", encoding="utf-8") as f:
            json.dump([dataclasses.asdict(a) for a in articles], f, ensure_ascii=False, indent=2)
