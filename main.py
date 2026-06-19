import os

from runner import CrawlRunner, StockCrawlRunner
from scrapers.techcombank import TechcombankScraper
from scrapers.vnstock_scraper import VnstockScraper
from repositories.csv_repository import CSVRepository
from repositories.stock_csv_repository import StockCSVRepository

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def main():
    CrawlRunner([TechcombankScraper()], CSVRepository(data_dir=DATA_DIR)).run()
    StockCrawlRunner([VnstockScraper()], StockCSVRepository(data_dir=DATA_DIR)).run()


if __name__ == "__main__":
    main()
