import logging
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from ..config import VIDEO_QUERIES, VIDEO_RESULTS_PER_QUERY, YOUTUBE_API_KEY
from ..models import CandidateVideo

logger = logging.getLogger(__name__)


def search_videos(db: Session, queries: list[str] | None = None) -> int:
    """Search YouTube for AI videos and store new candidates. Returns count of new rows."""
    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY not set — skipping video search")
        return 0

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    queries = queries or VIDEO_QUERIES
    published_after = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    added = 0

    for query in queries:
        try:
            response = (
                youtube.search()
                .list(
                    q=query,
                    type="video",
                    order="date",
                    publishedAfter=published_after,
                    maxResults=VIDEO_RESULTS_PER_QUERY,
                    part="snippet",
                )
                .execute()
            )
        except Exception:
            logger.exception("YouTube search failed for query: %s", query)
            continue

        for item in response.get("items", []):
            video_id = item["id"]["videoId"]

            existing = (
                db.query(CandidateVideo)
                .filter(CandidateVideo.youtube_id == video_id)
                .first()
            )
            if existing:
                continue

            snippet = item.get("snippet", {})
            candidate = CandidateVideo(
                youtube_id=video_id,
                title=snippet.get("title", "Untitled"),
                channel=snippet.get("channelTitle", "Unknown"),
                thumbnail_url=snippet.get("thumbnails", {})
                .get("high", {})
                .get("url", snippet.get("thumbnails", {}).get("default", {}).get("url", "")),
                description=snippet.get("description", "")[:500] or None,
                published_at=snippet.get("publishedAt", "")[:10],
                search_query=query,
            )
            db.add(candidate)
            added += 1

    db.commit()
    logger.info("YouTube search complete — %d new candidates", added)
    return added
