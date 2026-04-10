from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Issue
from ..schemas import IssueListItemOut, IssueOut

router = APIRouter(prefix="/api/issues", tags=["issues"])


@router.get("", response_model=list[IssueListItemOut])
def list_issues(db: Session = Depends(get_db)):
    issues = db.query(Issue).order_by(Issue.week_of.desc()).all()
    return issues


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
    return issue
