"""Tests for the /api/devs/posts ORM models (Slice 1)."""

from datetime import datetime, timezone

from app.models import (
    CandidateXTweet,
    DevPost,
    DiscoveredHandle,
    RepoStarSnapshot,
    XTopicDigestRow,
)


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
# CandidateXTweet
# ---------------------------------------------------------------------------


def test_candidate_x_tweet_roundtrip(db_session):
    tw = CandidateXTweet(
        url="https://x.com/simonw/status/1",
        author_handle="simonw",
        author_name="Simon Willison",
        author_avatar_url="https://example.com/a.png",
        text="MCP is changing how I wire up agents.",
        likes=500,
        reposts=100,
        replies=40,
        published_at=_dt(),
        quality_score=8.2,
        topic_cluster="mcp patterns",
    )
    db_session.add(tw)
    db_session.commit()
    db_session.refresh(tw)

    got = db_session.query(CandidateXTweet).one()
    assert got.author_handle == "simonw"
    assert got.likes == 500
    assert got.quality_score == 8.2
    assert got.topic_cluster == "mcp patterns"
    assert got.used_in_digest_id is None


# ---------------------------------------------------------------------------
# XTopicDigestRow + FK backref from CandidateXTweet
# ---------------------------------------------------------------------------


def test_x_topic_digest_and_tweet_backlink(db_session):
    digest = XTopicDigestRow(
        topic="MCP patterns",
        bullets=[
            {
                "text": "Sub-agents via MCP are taking off.",
                "sources": [
                    {
                        "url": "https://x.com/simonw/status/1",
                        "author_handle": "simonw",
                        "author_name": "Simon Willison",
                    }
                ],
            }
        ],
        rank_score=9.1,
        is_active=True,
        display_order=6,
    )
    db_session.add(digest)
    db_session.commit()
    db_session.refresh(digest)

    tw = CandidateXTweet(
        url="https://x.com/simonw/status/1",
        author_handle="simonw",
        text="MCP patterns.",
        published_at=_dt(),
        used_in_digest_id=digest.id,
    )
    db_session.add(tw)
    db_session.commit()
    db_session.refresh(tw)

    assert tw.used_in_digest_id == digest.id
    assert digest.bullets[0]["sources"][0]["author_handle"] == "simonw"
    assert digest.is_active is True
    assert digest.display_order == 6
    assert digest.created_at is not None


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
# DiscoveredHandle
# ---------------------------------------------------------------------------


def test_discovered_handle_defaults_and_roundtrip(db_session):
    row = DiscoveredHandle(
        handle="newhandle",
        seed_engagement_count=3,
        seed_handles=["simonw", "karpathy"],
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)

    got = db_session.query(DiscoveredHandle).one()
    assert got.handle == "newhandle"
    assert got.status == "pending"  # default
    assert got.seed_engagement_count == 3
    assert got.seed_handles == ["simonw", "karpathy"]
    assert got.first_seen_at is not None
    assert got.last_seen_at is not None


def test_discovered_handle_unique_handle(db_session):
    db_session.add(DiscoveredHandle(handle="dup"))
    db_session.commit()

    db_session.add(DiscoveredHandle(handle="dup"))
    import pytest
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


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
