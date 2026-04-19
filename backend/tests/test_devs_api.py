"""Tests for GET /api/devs/posts.

These tests exercise the serving layer (Slice 3). They depend on ORM classes
`DevPost` / `XTopicDigestRow` and the Pydantic schemas defined by Slice 1.
When those symbols aren't yet present in the current worktree we skip the
module rather than fail; the harmonizer re-runs the suite after merge.
"""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import guard — skip the whole module when Slice 1 isn't merged.
_MODELS_MISSING_REASON = "needs Slice 1/2 merge (DevPost + XTopicDigestRow ORM models)"

try:
    from app.models import DevPost, XTopicDigestRow  # type: ignore  # noqa: F401
    from app.routers import devs as devs_router  # noqa: F401
    _slice1_ready = True
except Exception:  # pragma: no cover - triggered when slice 1 missing
    _slice1_ready = False

pytestmark = pytest.mark.skipif(not _slice1_ready, reason=_MODELS_MISSING_REASON)


@pytest.fixture
def devs_client():
    from app.routers import devs

    app = FastAPI()
    app.include_router(devs.router)
    with TestClient(app) as tc:
        yield tc


def test_list_dev_posts_empty(devs_client):
    r = devs_client.get("/api/devs/posts")
    assert r.status_code == 200
    assert r.json() == []


def test_list_dev_posts_returns_union_and_is_ordered(devs_client, db_session):
    """Seed HN + GitHub DevPost rows + an XTopicDigestRow; expect union-shaped
    JSON ordered by display_order ascending, each item carrying the `source`
    discriminator."""
    from app.models import DevPost, XTopicDigestRow

    hn = DevPost(
        source="hn",
        url="https://news.ycombinator.com/item?id=1",
        published_at=datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc),
        collected_at=datetime(2026, 4, 18, 13, 0, tzinfo=timezone.utc),
        title="Show HN: A new coding agent",
        importance_score=8.0,
        rank_score=9.0,
        topics=["coding agent"],
        is_active=True,
        display_order=1,
        hn_url="https://news.ycombinator.com/item?id=1",
        points=420,
        comments=88,
        bullets=["great tool", "reviewers skeptical"],
        top_comment_excerpt="This is a top comment.",
    )
    gh = DevPost(
        source="github",
        url="https://github.com/anthropics/claude-code/releases/tag/v1.0.0",
        published_at=datetime(2026, 4, 17, 20, 0, tzinfo=timezone.utc),
        collected_at=datetime(2026, 4, 17, 20, 30, tzinfo=timezone.utc),
        title="claude-code v1.0.0",
        importance_score=9.0,
        rank_score=9.5,
        topics=["coding agent"],
        is_active=True,
        display_order=4,
        repo="anthropics/claude-code",
        version="v1.0.0",
        release_bullets=["new sub-agents", "tool use improvements"],
        release_notes_excerpt="…",
        why_it_matters="Spec-driven agents get easier.",
        has_breaking_changes=False,
        stars=5000,
        stars_velocity_7d=120,
    )
    inactive = DevPost(
        source="hn",
        url="https://news.ycombinator.com/item?id=999",
        published_at=datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
        collected_at=datetime(2026, 4, 10, 13, 0, tzinfo=timezone.utc),
        title="Old HN story",
        is_active=False,
        display_order=99,
        hn_url="https://news.ycombinator.com/item?id=999",
        points=10,
        comments=1,
    )
    x_digest = XTopicDigestRow(
        topic="MCP patterns",
        bullets=[
            {
                "text": "Servers are converging on a standard transport.",
                "sources": [
                    {
                        "url": "https://x.com/user/status/1",
                        "author_handle": "karpathy",
                        "author_name": "Andrej",
                    }
                ],
            }
        ],
        rank_score=8.0,
        is_active=True,
        display_order=6,
        created_at=datetime(2026, 4, 18, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([hn, gh, inactive, x_digest])
    db_session.commit()

    r = devs_client.get("/api/devs/posts")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 3  # inactive row excluded

    # Ordered by display_order ascending across all three sources.
    orders = [item["display_order"] for item in body]
    assert orders == sorted(orders)
    assert orders == [1, 4, 6]

    # Every item carries a `source` discriminator.
    sources = [item["source"] for item in body]
    assert sources == ["hn", "github", "x"]

    hn_item = body[0]
    assert hn_item["title"] == "Show HN: A new coding agent"
    assert hn_item["points"] == 420
    assert hn_item["bullets"] == ["great tool", "reviewers skeptical"]

    gh_item = body[1]
    assert gh_item["repo"] == "anthropics/claude-code"
    assert gh_item["has_breaking_changes"] is False
    assert gh_item["release_bullets"] == ["new sub-agents", "tool use improvements"]

    x_item = body[2]
    assert x_item["topic"] == "MCP patterns"
    assert x_item["bullets"][0]["sources"][0]["author_handle"] == "karpathy"
    # X digests have no url / published_at per frontend contract.
    assert "url" not in x_item or x_item.get("url") is None
