import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from tavily import TavilyClient

from ..config import NEWS_QUERIES, NEWS_RESULTS_PER_QUERY, TAVILY_API_KEY
from ..models import CandidateStory

logger = logging.getLogger(__name__)


def _normalize_published_date(raw: str | None) -> str:
    """Store YYYY-MM-DD. Tavily may return ISO or RFC 2822; naive [:10] breaks on the latter."""
    if not raw or not (raw := raw.strip()):
        return ""
    if (
        len(raw) >= 10
        and raw[0:4].isdigit()
        and raw[4] == "-"
        and raw[5:7].isdigit()
        and raw[7] == "-"
        and raw[8:10].isdigit()
    ):
        return raw[:10]
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(raw).date().isoformat()
    except (TypeError, ValueError):
        return ""


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
    seen_urls: set[str] = set()
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
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            existing = db.query(CandidateStory).filter(CandidateStory.url == url).first()
            if existing:
                continue

            candidate = CandidateStory(
                title=item.get("title", "Untitled"),
                summary=item.get("content", "")[:2000],
                source=_extract_source(url),
                url=url,
                image_url=None,
                date=_normalize_published_date(item.get("published_date")),
                tavily_score=item.get("score"),
                search_query=query,
            )
            db.add(candidate)
            added += 1

    db.commit()
    logger.info("Tavily search complete — %d new candidates", added)
    return added
