import logging
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from tavily import TavilyClient

from ..config import NEWS_QUERIES, NEWS_RESULTS_PER_QUERY, TAVILY_API_KEY
from ..models import CandidateStory

logger = logging.getLogger(__name__)


def _extract_source(url: str) -> str:
    """Pull a human-readable source name from a URL."""
    host = urlparse(url).netloc.lower()
    host = host.removeprefix("www.")
    return host.split(".")[0].title()


def search_news(db: Session, queries: list[str] | None = None) -> int:
    """Search Tavily for AI news and store new candidates. Returns count of new rows."""
    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set — skipping news search")
        return 0

    client = TavilyClient(api_key=TAVILY_API_KEY)
    queries = queries or NEWS_QUERIES
    added = 0

    for query in queries:
        try:
            results = client.search(
                query=query,
                topic="news",
                search_depth="advanced",
                max_results=NEWS_RESULTS_PER_QUERY,
                days=7,
            )
        except Exception:
            logger.exception("Tavily search failed for query: %s", query)
            continue

        for item in results.get("results", []):
            url = item.get("url", "")
            if not url:
                continue

            existing = db.query(CandidateStory).filter(CandidateStory.url == url).first()
            if existing:
                continue

            candidate = CandidateStory(
                title=item.get("title", "Untitled"),
                summary=item.get("content", "")[:2000],
                source=_extract_source(url),
                url=url,
                image_url=None,
                date=item.get("published_date", "")[:10] if item.get("published_date") else "",
                tavily_score=item.get("score"),
                search_query=query,
            )
            db.add(candidate)
            added += 1

    db.commit()
    logger.info("Tavily search complete — %d new candidates", added)
    return added
