from concurrent.futures import ThreadPoolExecutor
from datetime import date

from news.analyzer import analyze_article
from news.model import NewsArticle
from news.repositories.base import BaseNewsRepository
from news.scrapers.base import BaseNewsScraper

_MAX_WORKERS = 10


class NewsRunner:
    def __init__(self, scrapers: list, repository: BaseNewsRepository, max_workers: int = _MAX_WORKERS):
        self._scrapers = scrapers
        self._repository = repository
        self._max_workers = max_workers

    def run(self, target_date: str = None) -> None:
        if target_date is None:
            target_date = date.today().strftime("%Y-%m-%d")

        raw: list[NewsArticle] = []
        for scraper in self._scrapers:
            raw.extend(scraper.scrape())

        existing = self._repository.load(target_date)
        existing_urls = {a.url for a in existing}
        new_articles = [a for a in raw if a.url not in existing_urls]

        def _analyze(article: NewsArticle) -> NewsArticle:
            summary, sentiment = analyze_article(article.title, article.description)
            article.summary = summary
            article.sentiment = sentiment
            return article

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            analyzed = list(executor.map(_analyze, new_articles))

        all_articles = existing + analyzed
        all_articles.sort(key=lambda a: a.published_at, reverse=True)
        self._repository.save(all_articles, target_date)
