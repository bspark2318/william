from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Issue
from ..schemas import FeaturedVideoOut, IssueListItemOut, IssueOut, StoryOut

router = APIRouter(prefix="/api/issues", tags=["issues"])


def _edition(db: Session, week_of: str) -> int:
    """1-based issue number by publication order (ISO week_of strings sort chronologically)."""
    older = (
        db.query(func.count(Issue.id)).filter(Issue.week_of < week_of).scalar() or 0
    )
    return older + 1


@router.get("", response_model=list[IssueListItemOut])
def list_issues(db: Session = Depends(get_db)):
    issues = db.query(Issue).order_by(Issue.week_of.desc()).all()
    return [
        IssueListItemOut(
            id=i.id,
            week_of=i.week_of,
            title=i.title,
            edition=_edition(db, i.week_of),
        )
        for i in issues
    ]


@router.get("/{issue_id}", response_model=IssueOut)
def get_issue(issue_id: int, db: Session = Depends(get_db)):
    issue = (
        db.query(Issue)
        .options(joinedload(Issue.stories), joinedload(Issue.featured_videos))
        .filter(Issue.id == issue_id)
        .first()
    )
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    stories = sorted(issue.stories, key=lambda s: s.display_order)
    videos = list(issue.featured_videos)
    return IssueOut(
        id=issue.id,
        week_of=issue.week_of,
        title=issue.title,
        edition=_edition(db, issue.week_of),
        stories=[StoryOut.model_validate(s) for s in stories],
        featured_video=FeaturedVideoOut.model_validate(videos[0]) if videos else None,
        featured_videos=[FeaturedVideoOut.model_validate(v) for v in videos],
    )
