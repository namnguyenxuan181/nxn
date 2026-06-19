from abc import ABC, abstractmethod
from models.interest_rate import InterestRate


class BaseRepository(ABC):
    @abstractmethod
    def save(self, records: list[InterestRate]) -> None:
        pass
