import pytest
from scrapers.base import BaseScraper
from repositories.base import BaseRepository
from models.interest_rate import InterestRate


def test_base_scraper_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseScraper()


def test_base_repository_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseRepository()


def test_concrete_scraper_must_implement_scrape():
    class IncompleteScraper(BaseScraper):
        pass
    with pytest.raises(TypeError):
        IncompleteScraper()


def test_concrete_repository_must_implement_save():
    class IncompleteRepository(BaseRepository):
        pass
    with pytest.raises(TypeError):
        IncompleteRepository()


def test_concrete_scraper_works_when_scrape_implemented():
    class OkScraper(BaseScraper):
        def scrape(self) -> list[InterestRate]:
            return []
    assert OkScraper().scrape() == []


def test_concrete_repository_works_when_save_implemented():
    class OkRepository(BaseRepository):
        def save(self, records: list[InterestRate]) -> None:
            pass
    OkRepository().save([])
