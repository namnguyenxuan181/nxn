from abc import ABC, abstractmethod
from news.model import NewsArticle


class BaseNewsScraper(ABC):
    @abstractmethod
    def scrape(self) -> list[NewsArticle]:
        pass
