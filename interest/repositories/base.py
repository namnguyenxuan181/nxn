from abc import ABC, abstractmethod
from interest.model import InterestRate


class BaseRepository(ABC):
    @abstractmethod
    def save(self, records: list[InterestRate]) -> None:
        pass
