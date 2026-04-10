from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Issue
from ..schemas import FeaturedVideoOut, IssueListItemOut, IssueOut, StoryOut

router = APIRouter(prefix="/api/issues", tags=["issues"])


def _edition_map(db: Session) -> dict[int, int]:
    """Build {issue_id: edition} from a single query, ordered by week_of."""
    issues = db.query(Issue.id, Issue.week_of).order_by(Issue.week_of.asc()).all()
    return {issue_id: idx for idx, (issue_id, _) in enumerate(issues, 1)}


@router.get("", response_model=list[IssueListItemOut])
def list_issues(db: Session = Depends(get_db)):
    issues = db.query(Issue).order_by(Issue.week_of.desc()).all()
    editions = _edition_map(db)
    return [
        IssueListItemOut(
            id=i.id,
            week_of=i.week_of,
            title=i.title,
            edition=editions.get(i.id, 1),
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
        edition=_edition_map(db).get(issue.id, 1),
        stories=[StoryOut.model_validate(s) for s in stories],
        featured_video=FeaturedVideoOut.model_validate(videos[0]) if videos else None,
        featured_videos=[FeaturedVideoOut.model_validate(v) for v in videos],
    )
