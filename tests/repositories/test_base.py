import pytest
from repositories.base import BaseRepository
from models.interest_rate import InterestRate


def test_base_repository_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseRepository()


def test_concrete_repository_must_implement_save():
    class IncompleteRepository(BaseRepository):
        pass
    with pytest.raises(TypeError):
        IncompleteRepository()


def test_concrete_repository_works_when_save_implemented():
    class OkRepository(BaseRepository):
        def save(self, records: list[InterestRate]) -> None:
            pass
    OkRepository().save([])
