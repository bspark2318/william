import logging
import re
from datetime import date, datetime, timedelta, timezone

from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from ..config import (
    MAX_VIDEO_DURATION_SECS,
    MAX_VIDEO_SEARCHES_PER_COLLECT,
    MIN_VIDEO_DURATION_SECS,
    MIN_VIDEO_VIEWS,
    VIDEO_QUERIES,
    VIDEO_RESULTS_PER_QUERY,
    YOUTUBE_API_KEY,
)
from ..models import CandidateVideo
from ..query_rotation import queries_for_collect

logger = logging.getLogger(__name__)

_ISO_DURATION_RE = re.compile(
    r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
)


def _parse_duration(iso: str) -> int:
    """Convert ISO 8601 duration (PT1H2M3S) to total seconds."""
    m = _ISO_DURATION_RE.match(iso or "")
    if not m:
        return 0
    h, mi, s = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mi * 60 + s


def search_videos(
    db: Session,
    queries: list[str] | None = None,
    *,
    today: date | None = None,
) -> int:
    """Search YouTube for AI videos, enrich with stats, filter, and store candidates."""
    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY not set — skipping video search")
        return 0

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    pool = queries or VIDEO_QUERIES
    day = today or date.today()
    queries = queries_for_collect(pool, MAX_VIDEO_SEARCHES_PER_COLLECT, day)
    if not queries:
        logger.warning("No video queries selected (empty pool or max_video_searches_per_collect=0)")
        return 0
    logger.info(
        "YouTube: %d search call(s) today (pool %d, cap %s)",
        len(queries),
        len(pool),
        MAX_VIDEO_SEARCHES_PER_COLLECT if MAX_VIDEO_SEARCHES_PER_COLLECT is not None else "none",
    )
    published_after = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    added = 0
    seen_ids: set[str] = set()

    for query in queries:
        try:
            response = (
                youtube.search()
                .list(
                    q=query,
                    type="video",
                    order="relevance",
                    publishedAfter=published_after,
                    maxResults=VIDEO_RESULTS_PER_QUERY,
                    videoCategoryId="28",
                    part="snippet",
                )
                .execute()
            )
        except Exception:
            logger.exception("YouTube search failed for query: %s", query)
            continue

        items = response.get("items", [])
        if not items:
            continue

        video_ids = [item["id"]["videoId"] for item in items]

        try:
            stats_resp = (
                youtube.videos()
                .list(id=",".join(video_ids), part="statistics,contentDetails")
                .execute()
            )
        except Exception:
            logger.exception("YouTube videos.list failed for query: %s", query)
            stats_resp = {"items": []}

        stats_by_id: dict[str, dict] = {}
        for v in stats_resp.get("items", []):
            views = int(v.get("statistics", {}).get("viewCount", 0))
            duration = _parse_duration(v.get("contentDetails", {}).get("duration", ""))
            stats_by_id[v["id"]] = {"views": views, "duration": duration}

        for item in items:
            video_id = item["id"]["videoId"]

            if video_id in seen_ids:
                continue
            seen_ids.add(video_id)

            existing = (
                db.query(CandidateVideo)
                .filter(CandidateVideo.youtube_id == video_id)
                .first()
            )
            if existing:
                continue

            st = stats_by_id.get(video_id, {})
            views = st.get("views", 0)
            duration = st.get("duration", 0)

            if views < MIN_VIDEO_VIEWS:
                continue
            if duration < MIN_VIDEO_DURATION_SECS or duration > MAX_VIDEO_DURATION_SECS:
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
                view_count=views,
                duration_seconds=duration,
                search_query=query,
            )
            db.add(candidate)
            added += 1

    db.commit()
    logger.info("YouTube search complete — %d new candidates (after filtering)", added)
    return added
