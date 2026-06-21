import os

from interest.runner import CrawlRunner
from interest.scrapers.techcombank import TechcombankScraper
from interest.repositories.csv import CSVRepository
from stock.runner import StockCrawlRunner
from stock.scrapers.vnstock import VnstockScraper
from stock.repositories.csv import StockCSVRepository

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def main():
    CrawlRunner(
        [TechcombankScraper()],
        CSVRepository(data_dir=os.path.join(DATA_DIR, "interest")),
    ).run()
    StockCrawlRunner(
        [VnstockScraper()],
        StockCSVRepository(data_dir=os.path.join(DATA_DIR, "stock")),
    ).run()

    if os.environ.get("ANTHROPIC_API_KEY"):
        from news.repositories.json_repo import JSONNewsRepository
        from news.runner import NewsRunner
        from news.scrapers.cafef import CafefScraper
        from news.scrapers.vnexpress import VnExpressScraper
        from news.scrapers.vietstock import VietstockScraper
        NewsRunner(
            [VnExpressScraper(), CafefScraper(), VietstockScraper()],
            JSONNewsRepository(data_dir=os.path.join(DATA_DIR, "news")),
        ).run()


if __name__ == "__main__":
    main()
