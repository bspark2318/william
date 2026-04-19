"""Hacker News ingestion via Firebase API.

Pulls top stories, filters by agentic-coding-weighted keyword allowlist (and a
blocklist for non-engineering noise), and writes new rows into `dev_posts` with
source="hn", is_active=False. Ranking + bullet generation happen later in the
pipeline (see devs_pipeline.collect_hn + publish_hn).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import yaml
from sqlalchemy.orm import Session

try:  # pragma: no cover — exercised via tests only after Slice 1 merge
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

try:  # Slice 1 adds this model; source-only tests don't need it.
    from ..models import DevPost
except ImportError:  # pragma: no cover
    DevPost = None  # type: ignore

logger = logging.getLogger(__name__)

_HN_BASE = "https://hacker-news.firebaseio.com/v0"
_TOP_STORIES_URL = f"{_HN_BASE}/topstories.json"
_ITEM_URL = f"{_HN_BASE}/item/{{item_id}}.json"

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH = _BACKEND_ROOT / "devs_config.yaml"

# Default cap on how many top-stories to scan per collect run (avoids hammering
# the API — top 200 is more than enough to catch anything relevant in a day).
_TOP_STORY_SCAN_LIMIT = 200


def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


def _matches_allowlist(title: str, allowlist: Iterable[str]) -> bool:
    """Case-insensitive substring match against the keyword list."""
    lowered = (title or "").lower()
    return any(kw.lower() in lowered for kw in allowlist)


def _matches_blocklist(title: str, blocklist: Iterable[str]) -> bool:
    lowered = (title or "").lower()
    return any(kw.lower() in lowered for kw in blocklist)


def _hn_item_url(item_id: int) -> str:
    return f"https://news.ycombinator.com/item?id={item_id}"


def _get(client, url: str, *, timeout: float = 10.0):
    resp = client.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_hn_candidates(
    *,
    limit: int = _TOP_STORY_SCAN_LIMIT,
    client=None,
) -> list[dict]:
    """Fetch + filter HN stories. Returns list of normalized candidate dicts.

    A story passes if its title matches the allowlist AND does not hit the
    blocklist. Returns empty list on network failure (logged).
    """
    if client is None:
        if httpx is None:
            logger.warning("httpx not installed — cannot fetch HN")
            return []
        client = httpx.Client(timeout=10.0)
        own_client = True
    else:
        own_client = False

    cfg = _load_config()
    allowlist = cfg.get("hn_keyword_allowlist") or []
    blocklist = cfg.get("hn_keyword_blocklist") or []

    try:
        try:
            top_ids = _get(client, _TOP_STORIES_URL)
        except Exception:
            logger.exception("HN top-stories fetch failed")
            return []

        if not isinstance(top_ids, list):
            logger.warning("HN top-stories returned unexpected shape: %r", type(top_ids))
            return []

        candidates: list[dict] = []
        for item_id in top_ids[:limit]:
            try:
                item = _get(client, _ITEM_URL.format(item_id=item_id))
            except Exception:
                logger.warning("HN item fetch failed for %s", item_id)
                continue

            if not item or item.get("type") != "story":
                continue
            if item.get("dead") or item.get("deleted"):
                continue

            title = (item.get("title") or "").strip()
            if not title:
                continue

            # URL may be absent for "Ask HN" etc — fall back to the HN
            # comment-thread URL so the row is still linkable.
            url = item.get("url") or _hn_item_url(item_id)

            if not _matches_allowlist(title, allowlist):
                continue
            if _matches_blocklist(title, blocklist):
                continue

            published_ts = item.get("time")
            if published_ts is None:
                continue
            try:
                published_at = datetime.fromtimestamp(int(published_ts), tz=timezone.utc)
            except (TypeError, ValueError):
                continue

            candidates.append(
                {
                    "hn_id": item_id,
                    "title": title,
                    "url": url,
                    "hn_url": _hn_item_url(item_id),
                    "points": int(item.get("score") or 0),
                    "comments": int(item.get("descendants") or 0),
                    "published_at": published_at,
                    "kids": item.get("kids") or [],
                }
            )
        return candidates
    finally:
        if own_client:
            try:
                client.close()
            except Exception:  # pragma: no cover
                pass


def fetch_hn_comments(
    item_id: int,
    *,
    max_comments: int = 20,
    client=None,
) -> list[dict]:
    """Breadth-first fetch of top comments for an HN story.

    Returns a list of `{id, text, by, score}` dicts, ordered by HN's native
    `kids` ordering on the parent (roughly top-voted first). Dead/deleted
    comments are skipped. Network failures return what was gathered so far.
    """
    if client is None:
        if httpx is None:
            logger.warning("httpx not installed — cannot fetch HN comments")
            return []
        client = httpx.Client(timeout=10.0)
        own_client = True
    else:
        own_client = False

    collected: list[dict] = []
    try:
        try:
            parent = _get(client, _ITEM_URL.format(item_id=item_id))
        except Exception:
            logger.warning("HN parent fetch failed for %s", item_id)
            return []

        kids = (parent or {}).get("kids") or []
        for kid_id in kids[:max_comments]:
            try:
                kid = _get(client, _ITEM_URL.format(item_id=kid_id))
            except Exception:
                continue
            if not kid or kid.get("dead") or kid.get("deleted"):
                continue
            text = (kid.get("text") or "").strip()
            if not text:
                continue
            collected.append(
                {
                    "id": kid_id,
                    "text": text,
                    "by": kid.get("by"),
                    "score": kid.get("score") or 0,
                }
            )
        return collected
    finally:
        if own_client:
            try:
                client.close()
            except Exception:  # pragma: no cover
                pass


def ingest_hn(db: Session, *, client=None, limit: int = _TOP_STORY_SCAN_LIMIT) -> int:
    """Fetch + filter + insert HN candidates. Returns count of new rows.

    Matches the `tavily_search.search_news` contract: takes a Session, writes
    candidate rows, returns count. Dedups by `url` against existing rows.
    """
    candidates = fetch_hn_candidates(limit=limit, client=client)
    if not candidates:
        return 0

    # Pre-load all URLs we're about to insert to do one DB lookup, not N.
    urls = [c["url"] for c in candidates]
    existing = {
        row.url
        for row in db.query(DevPost.url).filter(DevPost.url.in_(urls)).all()
    }

    added = 0
    for cand in candidates:
        if cand["url"] in existing:
            continue

        row = DevPost(
            source="hn",
            url=cand["url"],
            title=cand["title"],
            published_at=cand["published_at"],
            hn_url=cand["hn_url"],
            points=cand["points"],
            comments=cand["comments"],
            is_active=False,
        )
        db.add(row)
        added += 1

    db.commit()
    logger.info("HN ingest complete — %d new candidates", added)
    return added
