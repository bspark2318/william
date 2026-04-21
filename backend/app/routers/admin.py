from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import (
    APIFY_MONTHLY_TWEET_CAP,
    MAX_X_HANDLES,
    VIDEO_PUBLISH_LOOKBACK_DAYS,
)
from ..database import get_db
from ..models import CandidateStory, CandidateVideo
from ..schemas import CandidateStoryOut, CandidateVideoOut
from ..services.pipeline import collect_candidates, publish_issue

from ..models import (
    CandidateXTweet,
    DevPost,
    DiscoveredHandle,
)
from ..services.devs_pipeline import collect_dev_candidates, publish_dev_feed

router = APIRouter(prefix="/api/admin", tags=["admin"])

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_DEVS_CONFIG_PATH = _BACKEND_ROOT / "devs_config.yaml"


@router.post("/collect")
def trigger_collect(db: Session = Depends(get_db)):
    result = collect_candidates(db)
    return result


@router.post("/publish")
def trigger_publish(db: Session = Depends(get_db)):
    result = publish_issue(db)
    return result


@router.get("/candidates")
def list_candidates(db: Session = Depends(get_db)):
    stories = (
        db.query(CandidateStory)
        .filter(CandidateStory.processed == False)  # noqa: E712
        .order_by(CandidateStory.collected_at.desc())
        .all()
    )
    video_cutoff = datetime.now(timezone.utc) - timedelta(days=VIDEO_PUBLISH_LOOKBACK_DAYS)
    videos = (
        db.query(CandidateVideo)
        .filter(CandidateVideo.collected_at >= video_cutoff)
        .order_by(CandidateVideo.collected_at.desc())
        .all()
    )
    return {
        "stories": [CandidateStoryOut.model_validate(s) for s in stories],
        "videos": [CandidateVideoOut.model_validate(v) for v in videos],
    }


# ---------------------------------------------------------------------------
# /api/admin/devs — skill-development feed admin
# ---------------------------------------------------------------------------

_DEVS_CANDIDATE_LOOKBACK_DAYS = 14


def _load_devs_yaml() -> dict:
    if _DEVS_CONFIG_PATH.exists():
        with open(_DEVS_CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


def _write_devs_yaml(cfg: dict) -> None:
    with open(_DEVS_CONFIG_PATH, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)


def _count_x_handles(cfg: dict) -> int:
    handles: set[str] = set()
    for tier in (cfg.get("x_handles") or {}).values():
        if isinstance(tier, list):
            handles.update(tier)
    return len(handles)


@router.post("/devs/collect")
def trigger_devs_collect(db: Session = Depends(get_db)):
    result = collect_dev_candidates(db) or {}
    hn = int(result.get("hn", 0) or 0)
    github = int(result.get("github", 0) or 0)
    x = int(result.get("x", 0) or 0)
    return {
        "status": "ok",
        "stories_added": hn + github,
        "videos_added": 0,
        "tweets_added": x,
    }


@router.post("/devs/publish")
def trigger_devs_publish(db: Session = Depends(get_db)):
    result = publish_dev_feed(db) or {}
    hn = int(result.get("hn_published", 0) or 0)
    github = int(result.get("github_published", 0) or 0)
    x = int(result.get("x_published", 0) or 0)
    feed_size = hn + github + x
    return {
        "status": "published" if feed_size > 0 else "skipped",
        "feed_size": feed_size,
        "digest_title": "Developer briefing",
    }


@router.get("/devs/candidates")
def list_devs_candidates(db: Session = Depends(get_db)):
    """Flat candidate list for the admin inspector — hn/github posts + x tweets."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=_DEVS_CANDIDATE_LOOKBACK_DAYS)
    dev_posts = (
        db.query(DevPost)
        .filter(DevPost.collected_at >= cutoff)
        .order_by(DevPost.collected_at.desc())
        .all()
    )
    x_tweets = (
        db.query(CandidateXTweet)
        .filter(CandidateXTweet.collected_at >= cutoff)
        .order_by(CandidateXTweet.collected_at.desc())
        .all()
    )

    out: list[dict] = []
    for r in dev_posts:
        out.append({
            "id": r.id,
            "source": r.source,
            "title": r.title,
            "text": None,
            "url": r.url,
            "importance_score": r.importance_score,
            "rank_score": r.rank_score,
            "rank_features": r.rank_features,
            "collected_at": r.collected_at.isoformat() if r.collected_at else None,
            "is_active": bool(r.is_active),
            "display_order": r.display_order,
        })
    for r in x_tweets:
        out.append({
            "id": r.id,
            "source": "x",
            "title": None,
            "text": r.text,
            "url": r.url,
            "importance_score": None,
            "rank_score": r.quality_score,
            "rank_features": None,
            "collected_at": r.collected_at.isoformat() if r.collected_at else None,
            "is_active": r.used_in_digest_id is not None,
            "display_order": None,
        })
    out.sort(key=lambda c: c["collected_at"] or "", reverse=True)
    return out


@router.get("/devs/handle-stats")
def devs_handle_stats(db: Session = Depends(get_db)):
    """Per-X-handle 30-day productivity — tweets collected, above-bar, published, last published."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    tweets = (
        db.query(CandidateXTweet)
        .filter(CandidateXTweet.collected_at >= cutoff)
        .all()
    )
    by_handle: dict[str, dict] = {}
    for t in tweets:
        h = by_handle.setdefault(
            t.author_handle,
            {
                "handle": t.author_handle,
                "tweets_collected_30d": 0,
                "tweets_scored_above_6_30d": 0,
                "tweets_published_30d": 0,
                "last_published_at": None,
            },
        )
        h["tweets_collected_30d"] += 1
        if (t.quality_score or 0) > 6.0:
            h["tweets_scored_above_6_30d"] += 1
        if t.used_in_digest_id is not None:
            h["tweets_published_30d"] += 1
            iso = t.collected_at.isoformat() if t.collected_at else None
            if iso and (h["last_published_at"] is None or iso > h["last_published_at"]):
                h["last_published_at"] = iso

    result = list(by_handle.values())
    result.sort(key=lambda r: r["tweets_published_30d"])
    return result


@router.get("/devs/discovered-handles")
def list_discovered_handles(
    status: str = "pending", db: Session = Depends(get_db)
):
    rows = (
        db.query(DiscoveredHandle)
        .filter(DiscoveredHandle.status == status)
        .order_by(DiscoveredHandle.seed_engagement_count.desc())
        .all()
    )
    return [
        {
            "handle": r.handle,
            "status": r.status,
            "first_seen_at": r.first_seen_at.isoformat() if r.first_seen_at else None,
            "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
            "seed_engagement_count": r.seed_engagement_count,
            "seed_handles": r.seed_handles,
        }
        for r in rows
    ]


@router.post("/devs/discovered-handles/{handle}/add")
def add_discovered_handle(handle: str, db: Session = Depends(get_db)):
    row = (
        db.query(DiscoveredHandle)
        .filter(DiscoveredHandle.handle == handle)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Handle not found")

    cfg = _load_devs_yaml()
    current = _count_x_handles(cfg)
    if current >= MAX_X_HANDLES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"MAX_X_HANDLES cap reached ({current}/{MAX_X_HANDLES}); "
                "ignore or remove a handle before adding another."
            ),
        )

    x_handles = cfg.setdefault("x_handles", {})
    tier = x_handles.setdefault("tier_b", [])
    if handle not in tier and not any(handle in (v or []) for v in x_handles.values()):
        tier.append(handle)
        _write_devs_yaml(cfg)

    row.status = "added"
    db.commit()

    return {
        "handle": handle,
        "status": "added",
        "total_handles": _count_x_handles(cfg),
    }


@router.post("/devs/discovered-handles/{handle}/ignore")
def ignore_discovered_handle(handle: str, db: Session = Depends(get_db)):
    row = (
        db.query(DiscoveredHandle)
        .filter(DiscoveredHandle.handle == handle)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Handle not found")
    row.status = "ignored"
    db.commit()
    return {"handle": handle, "status": "ignored"}


@router.get("/devs/budget")
def devs_budget(db: Session = Depends(get_db)):
    """Apify rolling 30-day tweet count vs monthly cap."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    tweets_30d = int(
        db.query(func.count(CandidateXTweet.id))
        .filter(CandidateXTweet.collected_at >= cutoff)
        .scalar()
        or 0
    )
    cap = APIFY_MONTHLY_TWEET_CAP
    pct_used = (tweets_30d / cap * 100.0) if cap > 0 else 0.0
    over_cap = tweets_30d >= cap
    return {
        "tweets_used_30d": tweets_30d,
        "tweets_cap": cap,
        "remaining": max(0, cap - tweets_30d),
        "pct_used": round(pct_used, 2),
        "will_pause_at": datetime.now(timezone.utc).isoformat() if over_cap else None,
    }
