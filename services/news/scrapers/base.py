from abc import ABC, abstractmethod
from services.news.model import NewsArticle


class BaseNewsScraper(ABC):
    @abstractmethod
    def scrape(self) -> list[NewsArticle]:
        pass
