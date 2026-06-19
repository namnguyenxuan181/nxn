from abc import ABC, abstractmethod
from interest.model import InterestRate


class BaseScraper(ABC):
    @abstractmethod
    def scrape(self) -> list[InterestRate]:
        pass
