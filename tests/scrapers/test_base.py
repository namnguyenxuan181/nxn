import pytest
from scrapers.base import BaseScraper
from models.interest_rate import InterestRate


def test_base_scraper_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseScraper()


def test_concrete_scraper_must_implement_scrape():
    class IncompleteScraper(BaseScraper):
        pass
    with pytest.raises(TypeError):
        IncompleteScraper()


def test_concrete_scraper_works_when_scrape_implemented():
    class OkScraper(BaseScraper):
        def scrape(self) -> list[InterestRate]:
            return []
    assert OkScraper().scrape() == []
