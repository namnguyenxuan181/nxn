from abc import ABC, abstractmethod
from models.interest_rate import InterestRate


class BaseScraper(ABC):
    @abstractmethod
    def scrape(self) -> list[InterestRate]:
        pass
