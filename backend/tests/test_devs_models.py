"""Tests for the /api/devs/posts ORM models (Slice 1)."""

from datetime import datetime, timezone

from app.models import DevPost, RepoStarSnapshot


def _dt(year=2026, month=4, day=17, hour=12, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# DevPost — HN row
# ---------------------------------------------------------------------------


def test_devpost_hn_row_roundtrip(db_session):
    row = DevPost(
        source="hn",
        url="https://news.ycombinator.com/item?id=1",
        published_at=_dt(),
        collected_at=_dt(hour=13),
        title="Show HN: my agentic coding setup",
        importance_score=7.5,
        rank_score=8.1,
        rank_features={"recency": 0.9, "keyword_hits": ["mcp", "claude code"]},
        topics=["coding agents", "mcp"],
        is_active=True,
        display_order=1,
        hn_url="https://news.ycombinator.com/item?id=1",
        points=420,
        comments=150,
        bullets=["Bullet one", "Bullet two"],
        top_comment_excerpt="Top comment text here.",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)

    got = db_session.query(DevPost).filter_by(source="hn").one()
    assert got.id == row.id
    assert got.source == "hn"
    assert got.url == "https://news.ycombinator.com/item?id=1"
    assert got.points == 420
    assert got.comments == 150
    assert got.bullets == ["Bullet one", "Bullet two"]
    assert got.top_comment_excerpt == "Top comment text here."
    assert got.topics == ["coding agents", "mcp"]
    assert got.rank_features == {
        "recency": 0.9,
        "keyword_hits": ["mcp", "claude code"],
    }
    assert got.is_active is True
    assert got.display_order == 1
    # GitHub-only cols should be None
    assert got.repo is None
    assert got.stars is None
    assert got.has_breaking_changes is None


# ---------------------------------------------------------------------------
# DevPost — GitHub row
# ---------------------------------------------------------------------------


def test_devpost_github_row_roundtrip(db_session):
    row = DevPost(
        source="github",
        url="https://github.com/anthropics/claude-code/releases/tag/v1.2.0",
        published_at=_dt(day=16),
        title="claude-code v1.2.0",
        rank_score=9.0,
        topics=["coding agents"],
        is_active=True,
        display_order=4,
        repo="anthropics/claude-code",
        version="v1.2.0",
        release_bullets=["Adds sub-agent support", "Faster startup"],
        release_notes_excerpt="Long notes here...",
        why_it_matters="Enables orchestrated workflows.",
        has_breaking_changes=False,
        stars=12000,
        stars_velocity_7d=350,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)

    got = db_session.query(DevPost).filter_by(source="github").one()
    assert got.source == "github"
    assert got.repo == "anthropics/claude-code"
    assert got.version == "v1.2.0"
    assert got.release_bullets == ["Adds sub-agent support", "Faster startup"]
    assert got.why_it_matters == "Enables orchestrated workflows."
    assert got.has_breaking_changes is False
    assert got.stars == 12000
    assert got.stars_velocity_7d == 350
    # HN-only cols should be None
    assert got.hn_url is None
    assert got.points is None
    assert got.bullets is None


# ---------------------------------------------------------------------------
# RepoStarSnapshot
# ---------------------------------------------------------------------------


def test_repo_star_snapshot_roundtrip(db_session):
    snap = RepoStarSnapshot(repo="anthropics/claude-code", stars=12000)
    db_session.add(snap)
    db_session.commit()
    db_session.refresh(snap)

    got = db_session.query(RepoStarSnapshot).one()
    assert got.repo == "anthropics/claude-code"
    assert got.stars == 12000
    assert got.observed_at is not None


# ---------------------------------------------------------------------------
# DevPost url uniqueness
# ---------------------------------------------------------------------------


def test_devpost_url_unique(db_session):
    db_session.add(
        DevPost(
            source="hn",
            url="https://example.com/a",
            published_at=_dt(),
            title="a",
        )
    )
    db_session.commit()

    db_session.add(
        DevPost(
            source="github",
            url="https://example.com/a",
            published_at=_dt(),
            title="b",
        )
    )
    import pytest
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
