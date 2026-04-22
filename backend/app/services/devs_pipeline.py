"""Orchestrators for `/api/devs/posts`.

Two per-source collect+publish pipelines, plus two top-level orchestrators:

  collect_dev_candidates(db) — runs HN + GitHub collectors + scores candidates
  publish_dev_feed(db)       — deactivates old, publishes new slots, purges old

Source shapes diverge too much for a unified ranker (HN post vs GitHub
release), so each source has its own publish function. Slot allocation is
config-driven.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from ..models import DevPost, RepoStarSnapshot

from . import devs_ranker
from .github_source import compute_stars_velocity_7d, ingest_github
from .hn_source import fetch_hn_comments, ingest_hn

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH = _BACKEND_ROOT / "devs_config.yaml"


def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


def _slot_allocation(cfg: dict | None = None) -> dict[str, int]:
    c = cfg or _load_config()
    alloc = c.get("slot_allocation") or {}
    return {
        "hn": int(alloc.get("hn", int(os.getenv("DEV_FEED_SIZE_HN", "3")))),
        "github": int(alloc.get("github", int(os.getenv("DEV_FEED_SIZE_GITHUB", "2")))),
    }


def _retention_days() -> int:
    return int(os.getenv("RETENTION_DAYS", "30"))


# ---------------------------------------------------------------------------
# Per-source collect
# ---------------------------------------------------------------------------

def collect_hn(db: Session) -> int:
    """Ingest HN top-stories, score any new rows, return count of new rows."""
    added = ingest_hn(db)

    unscored = (
        db.query(DevPost)
        .filter(DevPost.source == "hn")
        .filter(DevPost.importance_score.is_(None))
        .all()
    )
    for row in unscored:
        res = devs_ranker.rank_hn_post(
            {"title": row.title, "points": row.points, "comments": row.comments}
        )
        row.importance_score = float(res.get("score") or 0.0)
        topics = res.get("topics") or []
        if topics:
            row.topics = topics
        row.rank_features = {
            "points": row.points,
            "comments": row.comments,
            "llm_score": res.get("score"),
        }
    db.commit()
    return added


def collect_github(db: Session) -> int:
    """Ingest GitHub trending + releases, score new rows, return new-row count."""
    token = os.getenv("GITHUB_TOKEN") or None
    added = ingest_github(db, token=token)

    unscored = (
        db.query(DevPost)
        .filter(DevPost.source == "github")
        .filter(DevPost.importance_score.is_(None))
        .all()
    )
    for row in unscored:
        velocity = compute_stars_velocity_7d(db, row.repo) if row.repo else None
        row.stars_velocity_7d = velocity
        res = devs_ranker.rank_github_post(
            {
                "repo": row.repo,
                "title": row.title,
                "release_notes_excerpt": row.release_notes_excerpt,
                "stars": row.stars,
            }
        )
        row.importance_score = float(res.get("score") or 0.0)
        topics = res.get("topics") or []
        if topics and not row.topics:
            row.topics = topics
        row.rank_features = {
            "stars": row.stars,
            "stars_velocity_7d": velocity,
            "llm_score": res.get("score"),
        }
    db.commit()
    return added


def collect_dev_candidates(db: Session) -> dict:
    """Run HN + GitHub collectors. Returns per-source counts."""
    hn_added = 0
    gh_added = 0
    try:
        hn_added = collect_hn(db)
    except Exception:
        logger.exception("collect_hn failed")
    try:
        gh_added = collect_github(db)
    except Exception:
        logger.exception("collect_github failed")

    logger.info(
        "collect_dev_candidates complete — hn=%d, github=%d",
        hn_added, gh_added,
    )
    return {"hn": hn_added, "github": gh_added}


# ---------------------------------------------------------------------------
# Per-source publish
# ---------------------------------------------------------------------------

_HN_LOOKBACK_HOURS = 48
_GITHUB_LOOKBACK_DAYS = 7
_HN_FINALIST_POOL = 5
_GITHUB_FINALIST_POOL = 4


def _deactivate_active(db: Session) -> None:
    """Flip is_active=False on all currently active dev_posts rows."""
    db.query(DevPost).filter(DevPost.is_active.is_(True)).update(
        {"is_active": False, "display_order": None}, synchronize_session=False
    )
    db.commit()


def publish_hn(db: Session, *, start_order: int = 1, now: datetime | None = None) -> int:
    """Pick top HN candidates, generate bullets, mark active. Returns count published."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=_HN_LOOKBACK_HOURS)
    slots = _slot_allocation()["hn"]

    candidates = (
        db.query(DevPost)
        .filter(DevPost.source == "hn")
        .filter(DevPost.collected_at >= cutoff)
        .order_by(DevPost.importance_score.desc().nullslast())
        .limit(_HN_FINALIST_POOL)
        .all()
    )
    if not candidates:
        return 0

    finalists = candidates[:slots]
    published = 0
    for order_offset, post in enumerate(finalists):
        hn_item_id = _extract_hn_item_id(post.hn_url)
        bullets: list[str] = []
        top_comment: str | None = None
        if hn_item_id:
            try:
                comments = fetch_hn_comments(hn_item_id)
            except Exception:
                logger.warning("fetch_hn_comments failed for %s", post.url)
                comments = []
            comment_texts = [c["text"] for c in comments if c.get("text")]
            if comment_texts:
                top_comment = comment_texts[0][:280]
            try:
                bullets = devs_ranker.summarize_hn_thread(post.title, comment_texts)
            except Exception:
                logger.warning("summarize_hn_thread failed for %s", post.url)
                bullets = []

        post.bullets = bullets or None
        post.top_comment_excerpt = top_comment
        post.rank_score = post.importance_score
        post.is_active = True
        post.display_order = start_order + order_offset
        published += 1

    db.commit()
    return published


def publish_github(db: Session, *, start_order: int, now: datetime | None = None) -> int:
    """Pick top GitHub candidates, extract insights, mark active."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=_GITHUB_LOOKBACK_DAYS)
    slots = _slot_allocation()["github"]

    candidates = (
        db.query(DevPost)
        .filter(DevPost.source == "github")
        .filter(DevPost.collected_at >= cutoff)
        .order_by(DevPost.importance_score.desc().nullslast())
        .limit(_GITHUB_FINALIST_POOL)
        .all()
    )
    if not candidates:
        return 0

    finalists = candidates[:slots]
    published = 0
    for order_offset, post in enumerate(finalists):
        notes = post.release_notes_excerpt or ""
        try:
            insights = devs_ranker.extract_github_insights(post.repo or "", notes)
        except Exception:
            logger.warning("extract_github_insights failed for %s", post.url)
            insights = {
                "release_bullets": [],
                "why_it_matters": "",
                "has_breaking_changes": False,
            }

        post.release_bullets = insights.get("release_bullets") or None
        post.why_it_matters = insights.get("why_it_matters") or None
        post.has_breaking_changes = bool(insights.get("has_breaking_changes"))
        post.rank_score = post.importance_score
        post.is_active = True
        post.display_order = start_order + order_offset
        published += 1

    db.commit()
    return published


def _extract_hn_item_id(hn_url: str | None) -> int | None:
    if not hn_url:
        return None
    import re
    m = re.search(r"id=(\d+)", hn_url)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Publish orchestrator + purge
# ---------------------------------------------------------------------------

def _purge_old(db: Session, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=_retention_days())

    dp = db.query(DevPost).filter(DevPost.collected_at < cutoff).delete(synchronize_session=False)
    rs = db.query(RepoStarSnapshot).filter(RepoStarSnapshot.observed_at < cutoff).delete(synchronize_session=False)
    db.commit()
    return {
        "dev_posts_deleted": int(dp),
        "repo_star_snapshots_deleted": int(rs),
    }


def publish_dev_feed(db: Session) -> dict | None:
    """Deactivate → publish HN → publish GH → purge old rows."""
    slots = _slot_allocation()
    _deactivate_active(db)

    hn_start = 1
    gh_start = hn_start + slots["hn"]

    try:
        hn_count = publish_hn(db, start_order=hn_start)
    except Exception:
        logger.exception("publish_hn failed")
        hn_count = 0
    try:
        gh_count = publish_github(db, start_order=gh_start)
    except Exception:
        logger.exception("publish_github failed")
        gh_count = 0

    try:
        purge_stats = _purge_old(db)
    except Exception:
        logger.exception("purge failed")
        purge_stats = {}

    logger.info(
        "publish_dev_feed complete — hn=%d github=%d",
        hn_count, gh_count,
    )
    return {
        "hn_published": hn_count,
        "github_published": gh_count,
        "purged": purge_stats,
    }
