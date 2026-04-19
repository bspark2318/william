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

# Slice 1/2 symbols — imported defensively so the module still loads when
# those slices haven't been merged yet (e.g. in the slice-3 worktree CI).
try:
    from ..models import (  # type: ignore
        CandidateXTweet,
        DevPost,
        DiscoveredHandle,
        XTopicDigestRow,
    )
except ImportError:  # pragma: no cover - resolved at merge time
    CandidateXTweet = None  # type: ignore
    DevPost = None  # type: ignore
    DiscoveredHandle = None  # type: ignore
    XTopicDigestRow = None  # type: ignore

try:
    from ..services.devs_pipeline import (  # type: ignore
        collect_dev_candidates,
        publish_dev_feed,
    )
except ImportError:  # pragma: no cover
    collect_dev_candidates = None  # type: ignore
    publish_dev_feed = None  # type: ignore

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
    return collect_dev_candidates(db)


@router.post("/devs/publish")
def trigger_devs_publish(db: Session = Depends(get_db)):
    return publish_dev_feed(db)


@router.get("/devs/candidates")
def list_devs_candidates(db: Session = Depends(get_db)):
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
    x_digests = (
        db.query(XTopicDigestRow)
        .order_by(XTopicDigestRow.created_at.desc())
        .limit(50)
        .all()
    )

    def _dev_to_dict(r: DevPost) -> dict:
        return {
            "id": r.id,
            "source": r.source,
            "url": r.url,
            "title": r.title,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "collected_at": r.collected_at.isoformat() if r.collected_at else None,
            "importance_score": r.importance_score,
            "rank_score": r.rank_score,
            "rank_features": r.rank_features,
            "topics": r.topics,
            "is_active": r.is_active,
            "display_order": r.display_order,
            "repo": r.repo,
            "version": r.version,
            "stars": r.stars,
            "stars_velocity_7d": r.stars_velocity_7d,
            "points": r.points,
            "comments": r.comments,
        }

    def _tweet_to_dict(r: CandidateXTweet) -> dict:
        return {
            "id": r.id,
            "url": r.url,
            "author_handle": r.author_handle,
            "author_name": r.author_name,
            "text": r.text,
            "likes": r.likes,
            "reposts": r.reposts,
            "replies": r.replies,
            "quality_score": r.quality_score,
            "topic_cluster": r.topic_cluster,
            "used_in_digest_id": r.used_in_digest_id,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "collected_at": r.collected_at.isoformat() if r.collected_at else None,
        }

    def _digest_to_dict(r: XTopicDigestRow) -> dict:
        return {
            "id": r.id,
            "topic": r.topic,
            "bullets": r.bullets,
            "rank_score": r.rank_score,
            "is_active": r.is_active,
            "display_order": r.display_order,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }

    return {
        "dev_posts": [_dev_to_dict(r) for r in dev_posts],
        "candidate_x_tweets": [_tweet_to_dict(r) for r in x_tweets],
        "x_topic_digests": [_digest_to_dict(r) for r in x_digests],
    }


@router.get("/devs/handle-stats")
def devs_handle_stats(db: Session = Depends(get_db)):
    """Per-X-handle 30-day productivity — tweets collected, above-bar, used, last used."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    # Python-side aggregation keeps behavior consistent across dialects
    # (SQLite JSON/Boolean casts are finicky inside func.sum).
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
                "tweets_collected": 0,
                "tweets_above_6": 0,
                "tweets_used_in_digest": 0,
                "last_used_at": None,
            },
        )
        h["tweets_collected"] += 1
        if (t.quality_score or 0) > 6.0:
            h["tweets_above_6"] += 1
        if t.used_in_digest_id is not None:
            h["tweets_used_in_digest"] += 1
            iso = t.collected_at.isoformat() if t.collected_at else None
            if iso and (h["last_used_at"] is None or iso > h["last_used_at"]):
                h["last_used_at"] = iso

    result = list(by_handle.values())
    result.sort(key=lambda r: r["tweets_used_in_digest"])
    return {"handles": result}


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
    return {
        "handles": [
            {
                "id": r.id,
                "handle": r.handle,
                "status": r.status,
                "first_seen_at": r.first_seen_at.isoformat() if r.first_seen_at else None,
                "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
                "seed_engagement_count": r.seed_engagement_count,
                "seed_handles": r.seed_handles,
            }
            for r in rows
        ]
    }


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
    tweets_30d = (
        db.query(func.count(CandidateXTweet.id))
        .filter(CandidateXTweet.collected_at >= cutoff)
        .scalar()
        or 0
    )
    return {
        "tweets_last_30d": int(tweets_30d),
        "monthly_cap": APIFY_MONTHLY_TWEET_CAP,
        "remaining": max(0, APIFY_MONTHLY_TWEET_CAP - int(tweets_30d)),
        "over_cap": int(tweets_30d) >= APIFY_MONTHLY_TWEET_CAP,
    }
