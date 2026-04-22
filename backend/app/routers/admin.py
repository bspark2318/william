from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import VIDEO_PUBLISH_LOOKBACK_DAYS
from ..database import get_db
from ..models import CandidateStory, CandidateVideo, DevPost
from ..schemas import CandidateStoryOut, CandidateVideoOut
from ..services.devs_pipeline import collect_dev_candidates, publish_dev_feed
from ..services.pipeline import collect_candidates, publish_issue

router = APIRouter(prefix="/api/admin", tags=["admin"])


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


@router.post("/devs/collect")
def trigger_devs_collect(db: Session = Depends(get_db)):
    result = collect_dev_candidates(db) or {}
    hn = int(result.get("hn", 0) or 0)
    github = int(result.get("github", 0) or 0)
    return {
        "status": "ok",
        "stories_added": hn + github,
        "videos_added": 0,
    }


@router.post("/devs/publish")
def trigger_devs_publish(db: Session = Depends(get_db)):
    result = publish_dev_feed(db) or {}
    hn = int(result.get("hn_published", 0) or 0)
    github = int(result.get("github_published", 0) or 0)
    feed_size = hn + github
    return {
        "status": "published" if feed_size > 0 else "skipped",
        "feed_size": feed_size,
        "digest_title": "Developer briefing",
    }


@router.get("/devs/candidates")
def list_devs_candidates(db: Session = Depends(get_db)):
    """Flat candidate list for the admin inspector — hn + github posts."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=_DEVS_CANDIDATE_LOOKBACK_DAYS)
    dev_posts = (
        db.query(DevPost)
        .filter(DevPost.collected_at >= cutoff)
        .order_by(DevPost.collected_at.desc())
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
    out.sort(key=lambda c: c["collected_at"] or "", reverse=True)
    return out
