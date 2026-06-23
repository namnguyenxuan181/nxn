import pytest
import pandas as pd
from news.model import NewsArticle
from alerts.checker import check_price_alerts, check_news_alerts


def _df(rows):
    return pd.DataFrame(rows, columns=["symbol", "close"])


def _article(title, description="", source="vnexpress"):
    return NewsArticle(
        source=source, title=title, url="https://example.com",
        published_at="2026-06-23T10:00:00+07:00", description=description,
    )


def test_price_alert_above_threshold():
    df_today = _df([("TCB", 32050)])
    df_yest = _df([("TCB", 30000)])
    results = check_price_alerts(["TCB"], df_today, df_yest)
    assert len(results) == 1
    assert results[0]["symbol"] == "TCB"
    assert results[0]["change_pct"] == pytest.approx(6.83, abs=0.01)


def test_price_alert_below_threshold():
    df_today = _df([("TCB", 30500)])
    df_yest = _df([("TCB", 30000)])
    results = check_price_alerts(["TCB"], df_today, df_yest)
    assert results == []


def test_price_alert_negative_move():
    df_today = _df([("HPG", 28000)])
    df_yest = _df([("HPG", 30000)])
    results = check_price_alerts(["HPG"], df_today, df_yest)
    assert len(results) == 1
    assert results[0]["change_pct"] < 0


def test_price_alert_symbol_missing_today():
    df_today = _df([])
    df_yest = _df([("TCB", 30000)])
    results = check_price_alerts(["TCB"], df_today, df_yest)
    assert results == []


def test_price_alert_symbol_missing_yesterday():
    df_today = _df([("TCB", 32050)])
    df_yest = _df([])
    results = check_price_alerts(["TCB"], df_today, df_yest)
    assert results == []


def test_price_alert_uses_intraday_when_provided():
    df_today = _df([("TCB", 30100)])   # EOD: +0.3%, under threshold
    df_yest = _df([("TCB", 30000)])
    intraday = {"TCB": 32050}          # intraday: +6.8%, over threshold
    results = check_price_alerts(["TCB"], df_today, df_yest, intraday=intraday)
    assert len(results) == 1
    assert results[0]["change_pct"] == pytest.approx(6.83, abs=0.01)


def test_news_alert_title_match():
    articles = [_article("TCB tăng mạnh hôm nay")]
    results = check_news_alerts(["TCB"], articles)
    assert len(results) == 1
    assert results[0]["symbol"] == "TCB"


def test_news_alert_description_match():
    articles = [_article("Thị trường hôm nay", description="Cổ phiếu HPG tăng 5%")]
    results = check_news_alerts(["HPG"], articles)
    assert len(results) == 1


def test_news_alert_no_match():
    articles = [_article("Thị trường ổn định")]
    results = check_news_alerts(["TCB", "VCB"], articles)
    assert results == []


def test_news_alert_case_insensitive():
    articles = [_article("tcb hôm nay")]
    results = check_news_alerts(["TCB"], articles)
    assert len(results) == 1
