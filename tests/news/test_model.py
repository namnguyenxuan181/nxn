from services.news.model import NewsArticle


def test_news_article_defaults():
    a = NewsArticle(
        source="vnexpress",
        title="Test",
        url="https://example.com",
        published_at="2026-06-21T08:00:00+07:00",
        description="desc",
    )
    assert a.summary == ""
    assert a.sentiment == "neutral"


def test_news_article_with_all_fields():
    a = NewsArticle(
        source="cafef",
        title="Title",
        url="https://cafef.vn/1.html",
        published_at="2026-06-21T09:00:00+07:00",
        description="desc",
        summary="Tóm tắt.",
        sentiment="positive",
    )
    assert a.sentiment == "positive"
    assert a.summary == "Tóm tắt."
