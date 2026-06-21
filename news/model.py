from dataclasses import dataclass


@dataclass
class NewsArticle:
    source: str
    title: str
    url: str
    published_at: str
    description: str
    summary: str = ""
    sentiment: str = "neutral"
