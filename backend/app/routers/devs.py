from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DevPost, XTopicDigestRow
from ..schemas import DevPostOut, GitHubPostOut, HNPostOut, XTopicDigestOut

router = APIRouter(prefix="/api/devs", tags=["devs"])


def _serialize_dev_post(row):
    """Serialize a DevPost ORM row into its discriminated Pydantic shape."""
    if row.source == "hn":
        return HNPostOut.model_validate(row)
    if row.source == "github":
        return GitHubPostOut.model_validate(row)
    raise ValueError(f"unknown dev_post source {row.source!r} (id={row.id})")


def _serialize_x_digest(row):
    return XTopicDigestOut.model_validate(row)


@router.get("/posts", response_model=list[DevPostOut])
def list_dev_posts(db: Session = Depends(get_db)):
    """Return the active developer feed.

    UNIONs active `dev_posts` rows (HN + GitHub) with active
    `x_topic_digests` rows, ordered by `display_order` ascending.
    """
    dev_rows = (
        db.query(DevPost)
        .filter(DevPost.is_active == True)  # noqa: E712
        .all()
    )
    x_rows = (
        db.query(XTopicDigestRow)
        .filter(XTopicDigestRow.is_active == True)  # noqa: E712
        .all()
    )

    serialized: list = []
    for r in dev_rows:
        serialized.append(_serialize_dev_post(r))
    for r in x_rows:
        serialized.append(_serialize_x_digest(r))

    serialized.sort(
        key=lambda p: (p.display_order if p.display_order is not None else 10_000)
    )
    return serialized
