from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import VIDEO_PUBLISH_LOOKBACK_DAYS
from ..database import get_db
from ..models import CandidateStory, CandidateVideo
from ..schemas import CandidateStoryOut, CandidateVideoOut
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
