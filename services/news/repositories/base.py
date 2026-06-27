from abc import ABC, abstractmethod
from services.news.model import NewsArticle


class BaseNewsRepository(ABC):
    @abstractmethod
    def load(self, date: str) -> list[NewsArticle]:
        pass

    @abstractmethod
    def save(self, articles: list[NewsArticle], date: str) -> None:
        pass
