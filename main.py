import json
import os
import pandas as pd
from datetime import date, datetime, timedelta, timezone

from interest.runner import CrawlRunner
from interest.scrapers.multi_rate import MultiRateScraper
from interest.repositories.csv import CSVRepository
from stock.runner import StockCrawlRunner
from stock.scrapers.vnstock import VnstockScraper
from stock.repositories.csv import StockCSVRepository

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
_VN_TZ = timezone(timedelta(hours=7))


def _is_trading_day_after_open() -> bool:
    now = datetime.now(_VN_TZ)
    return now.weekday() < 5 and now.hour >= 9


def _load_stock_csv(date_str: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "stock", f"stock_{date_str}.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["symbol", "close"])
    return pd.read_csv(path)


def main():
    CrawlRunner(
        [MultiRateScraper()],
        CSVRepository(data_dir=os.path.join(DATA_DIR, "interest")),
    ).run()

    stock_repo = StockCSVRepository(data_dir=os.path.join(DATA_DIR, "stock"))
    StockCrawlRunner([VnstockScraper()], stock_repo).run()

    if _is_trading_day_after_open():
        today_str = date.today().strftime("%Y-%m-%d")
        today_records = VnstockScraper(target_date=today_str).scrape()
        if today_records:
            stock_repo.save(today_records)

    from news.repositories.json_repo import JSONNewsRepository
    from news.runner import NewsRunner
    from news.scrapers.cafef import CafefScraper
    from news.scrapers.vnexpress import VnExpressScraper
    from news.scrapers.vietstock import VietstockScraper
    news_repo = JSONNewsRepository(data_dir=os.path.join(DATA_DIR, "news"))
    NewsRunner(
        [VnExpressScraper(), CafefScraper(), VietstockScraper()],
        news_repo,
    ).run()

    portfolio_path = os.path.join(BASE_DIR, "portfolio.json")
    if not os.path.exists(portfolio_path):
        return

    with open(portfolio_path, encoding="utf-8") as f:
        portfolio = json.load(f)

    watchlist = list(
        {sym for sym in portfolio.get("watchlist", [])} |
        {h["symbol"] for h in portfolio.get("holdings", [])}
    )
    if not watchlist:
        return

    from alerts.checker import check_price_alerts, check_news_alerts
    from alerts.notifier import notify
    from stock.scrapers.intraday import fetch_intraday_prices, is_market_open

    today_str = date.today().strftime("%Y-%m-%d")
    yest_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    df_today = _load_stock_csv(today_str)
    df_yest = _load_stock_csv(yest_str)

    intraday = fetch_intraday_prices(watchlist) if is_market_open() else {}

    for hit in check_price_alerts(watchlist, df_today, df_yest, intraday=intraday):
        sign = "+" if hit["change_pct"] > 0 else ""
        notify(f"📈 {hit['symbol']}", f"{sign}{hit['change_pct']:.1f}%")

    articles = news_repo.load(today_str)
    seen = set()
    for hit in check_news_alerts(watchlist, articles):
        key = (hit["symbol"], hit["title"])
        if key not in seen:
            seen.add(key)
            notify(f"📰 {hit['symbol']}", hit["title"][:80])


if __name__ == "__main__":
    main()
