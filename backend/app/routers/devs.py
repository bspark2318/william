from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DevPost
from ..schemas import DevPostOut, GitHubPostOut, HNPostOut

router = APIRouter(prefix="/api/devs", tags=["devs"])


def _serialize_dev_post(row):
    """Serialize a DevPost ORM row into its discriminated Pydantic shape."""
    if row.source == "hn":
        return HNPostOut.model_validate(row)
    if row.source == "github":
        return GitHubPostOut.model_validate(row)
    raise ValueError(f"unknown dev_post source {row.source!r} (id={row.id})")


@router.get("/posts", response_model=list[DevPostOut])
def list_dev_posts(db: Session = Depends(get_db)):
    """Return the active developer feed (active `dev_posts` rows, HN + GitHub)."""
    dev_rows = (
        db.query(DevPost)
        .filter(DevPost.is_active == True)  # noqa: E712
        .order_by(DevPost.display_order.asc().nullslast())
        .all()
    )
    return [_serialize_dev_post(r) for r in dev_rows]
