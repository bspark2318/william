from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db

# Slice 1 ORM + schemas — defensive imports so the router module still loads
# when slice 1 hasn't merged. The endpoint will raise if actually invoked
# before slice 1 lands; that's fine, the route just won't work until then.
try:
    from ..models import DevPost, XTopicDigestRow  # type: ignore
    from ..schemas import (  # type: ignore
        DevPostOut,
        GitHubPostOut,
        HNPostOut,
        XTopicDigestOut,
    )

    _DEVS_READY = True
except ImportError:  # pragma: no cover - resolved at merge time
    DevPost = None  # type: ignore
    XTopicDigestRow = None  # type: ignore
    DevPostOut = None  # type: ignore
    GitHubPostOut = None  # type: ignore
    HNPostOut = None  # type: ignore
    XTopicDigestOut = None  # type: ignore
    _DEVS_READY = False


router = APIRouter(prefix="/api/devs", tags=["devs"])


def _serialize_dev_post(row):
    """Serialize a DevPost ORM row into its discriminated Pydantic shape."""
    if row.source == "hn":
        return HNPostOut.model_validate(row)
    return GitHubPostOut.model_validate(row)


def _serialize_x_digest(row):
    return XTopicDigestOut.model_validate(row)


if _DEVS_READY:

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

else:  # pragma: no cover - slice 1 not merged

    @router.get("/posts")
    def list_dev_posts_stub(db: Session = Depends(get_db)):
        return []
