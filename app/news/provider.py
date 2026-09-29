import httpx
import structlog

from app.errors import describe_exception
from app.news.base import NewsItem, NewsProvider

logger = structlog.get_logger()


class WebNewsProvider(NewsProvider):
    """Fetches recent German news headlines via NewsAPI-compatible endpoint.

    Disabled gracefully (returns []) if no API key is configured, so the
    content generator falls back to non-news categories instead of
    fabricating articles.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, query: str) -> list[NewsItem]:
        if not self.api_key:
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": query,
                        "language": "de",
                        "sortBy": "publishedAt",
                        "pageSize": 5,
                        "apiKey": self.api_key,
                    },
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("news_fetch_failed", error=describe_exception(exc))
            return []

        items = []
        for article in data.get("articles", [])[:5]:
            if not article.get("title") or not article.get("url"):
                continue
            items.append(
                NewsItem(
                    title=article["title"],
                    summary=article.get("description") or "",
                    source=article.get("source", {}).get("name", "unknown"),
                    source_url=article["url"],
                    publication_date=(article.get("publishedAt") or "")[:10],
                )
            )
        return items


class NullNewsProvider(NewsProvider):
    async def search(self, query: str) -> list[NewsItem]:
        return []
