import os

from runner import CrawlRunner
from scrapers.techcombank import TechcombankScraper
from repositories.csv_repository import CSVRepository

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def main():
    scrapers = [TechcombankScraper()]
    repository = CSVRepository(data_dir=DATA_DIR)
    CrawlRunner(scrapers, repository).run()


if __name__ == "__main__":
    main()
