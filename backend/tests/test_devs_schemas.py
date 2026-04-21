"""Tests for the /api/devs/posts Pydantic schemas (Slice 1)."""

from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from app.models import DevPost, XTopicDigestRow
from app.schemas import (
    DevPostOut,
    GitHubPostOut,
    HNPostOut,
    XBullet,
    XBulletSource,
    XTopicDigestOut,
)


def _dt(year=2026, month=4, day=17, hour=14, minute=30):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# XTopicDigestOut — instantiate + serialize
# ---------------------------------------------------------------------------


def test_x_topic_digest_out_instantiate_and_dump():
    bullet = XBullet(
        text="Sub-agents via MCP are taking off.",
        sources=[
            XBulletSource(
                url="https://x.com/simonw/status/1",
                author_handle="simonw",
                author_name="Simon Willison",
            )
        ],
    )
    digest = XTopicDigestOut(
        id=1,
        rank_score=9.1,
        display_order=6,
        topic="MCP patterns",
        bullets=[bullet],
    )
    assert digest.source == "x"
    dumped = digest.model_dump()
    assert dumped["source"] == "x"
    assert dumped["topic"] == "MCP patterns"
    assert dumped["bullets"][0]["text"] == "Sub-agents via MCP are taking off."
    assert dumped["bullets"][0]["sources"][0]["author_handle"] == "simonw"
    # No url / published_at on X digest shape
    assert "url" not in dumped
    assert "published_at" not in dumped


def test_x_topic_digest_out_from_orm(db_session):
    digest = XTopicDigestRow(
        topic="MCP patterns",
        bullets=[
            {
                "text": "Sub-agents via MCP.",
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

    out = XTopicDigestOut.model_validate(digest)
    assert out.source == "x"
    assert out.topic == "MCP patterns"
    assert out.display_order == 6
    assert out.bullets[0].sources[0].author_handle == "simonw"


# ---------------------------------------------------------------------------
# HNPostOut — instantiate + serialize + ISO datetime
# ---------------------------------------------------------------------------


def test_hn_post_out_instantiate_and_serialize_iso():
    post = HNPostOut(
        id=2,
        rank_score=8.1,
        display_order=1,
        url="https://news.ycombinator.com/item?id=1",
        published_at=_dt(),
        title="Show HN: my agentic coding setup",
        hn_url="https://news.ycombinator.com/item?id=1",
        points=420,
        comments=150,
        bullets=["one", "two"],
        top_comment_excerpt="A great top comment",
        topics=["mcp"],
    )
    assert post.source == "hn"
    dumped = post.model_dump()
    # published_at is serialized as ISO datetime string
    assert isinstance(dumped["published_at"], str)
    assert dumped["published_at"].startswith("2026-04-17T14:30:00")
    # JSON round-trip
    raw = post.model_dump_json()
    assert "\"source\":\"hn\"" in raw
    assert "\"published_at\":\"2026-04-17T14:30:00" in raw


def test_hn_post_out_from_orm(db_session):
    row = DevPost(
        source="hn",
        url="https://news.ycombinator.com/item?id=2",
        published_at=_dt(),
        title="hn title",
        hn_url="https://news.ycombinator.com/item?id=2",
        points=100,
        comments=25,
        bullets=["b1"],
        topics=["mcp"],
        is_active=True,
        display_order=2,
        rank_score=7.0,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)

    out = HNPostOut.model_validate(row)
    assert out.source == "hn"
    assert out.points == 100
    assert out.comments == 25
    assert out.bullets == ["b1"]
    assert out.display_order == 2


# ---------------------------------------------------------------------------
# GitHubPostOut — instantiate + serialize
# ---------------------------------------------------------------------------


def test_github_post_out_instantiate_and_serialize():
    post = GitHubPostOut(
        id=3,
        rank_score=9.0,
        display_order=4,
        url="https://github.com/anthropics/claude-code/releases/tag/v1.2.0",
        published_at=_dt(day=16),
        repo="anthropics/claude-code",
        title="claude-code v1.2.0",
        version="v1.2.0",
        release_bullets=["Sub-agents", "Faster startup"],
        release_notes_excerpt="Notes...",
        why_it_matters="Matters.",
        has_breaking_changes=False,
        stars=12000,
        stars_velocity_7d=350,
        topics=["coding agents"],
    )
    assert post.source == "github"
    dumped = post.model_dump()
    assert dumped["repo"] == "anthropics/claude-code"
    assert dumped["has_breaking_changes"] is False
    assert isinstance(dumped["published_at"], str)
    assert dumped["published_at"].startswith("2026-04-16T")


def test_github_post_out_from_orm(db_session):
    row = DevPost(
        source="github",
        url="https://github.com/foo/bar/releases/tag/v1",
        published_at=_dt(),
        title="foo/bar v1",
        repo="foo/bar",
        version="v1",
        release_bullets=["rb"],
        why_it_matters="why",
        has_breaking_changes=True,
        stars=500,
        stars_velocity_7d=20,
        is_active=True,
        display_order=5,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)

    out = GitHubPostOut.model_validate(row)
    assert out.source == "github"
    assert out.repo == "foo/bar"
    assert out.has_breaking_changes is True
    assert out.display_order == 5


# ---------------------------------------------------------------------------
# DevPostOut discriminated union — routing by `source`
# ---------------------------------------------------------------------------


def test_devpost_out_union_routes_hn():
    adapter = TypeAdapter(DevPostOut)
    parsed = adapter.validate_python(
        {
            "source": "hn",
            "id": 1,
            "display_order": 1,
            "url": "https://news.ycombinator.com/item?id=1",
            "published_at": "2026-04-17T14:30:00+00:00",
            "title": "t",
            "hn_url": "https://news.ycombinator.com/item?id=1",
            "points": 10,
            "comments": 2,
        }
    )
    assert isinstance(parsed, HNPostOut)
    assert parsed.source == "hn"


def test_devpost_out_union_routes_github():
    adapter = TypeAdapter(DevPostOut)
    parsed = adapter.validate_python(
        {
            "source": "github",
            "id": 2,
            "display_order": 4,
            "url": "https://github.com/foo/bar",
            "published_at": "2026-04-17T14:30:00+00:00",
            "repo": "foo/bar",
            "title": "foo/bar v1",
        }
    )
    assert isinstance(parsed, GitHubPostOut)
    assert parsed.source == "github"
    assert parsed.repo == "foo/bar"


def test_devpost_out_union_routes_x():
    adapter = TypeAdapter(DevPostOut)
    parsed = adapter.validate_python(
        {
            "source": "x",
            "id": 3,
            "display_order": 6,
            "topic": "MCP",
            "bullets": [
                {
                    "text": "t",
                    "sources": [
                        {"url": "https://x.com/a/1", "author_handle": "a"}
                    ],
                }
            ],
        }
    )
    assert isinstance(parsed, XTopicDigestOut)
    assert parsed.topic == "MCP"


def test_devpost_out_union_rejects_unknown_source():
    adapter = TypeAdapter(DevPostOut)
    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "source": "rss",
                "id": 99,
                "display_order": 1,
                "url": "https://example.com",
                "published_at": "2026-04-17T14:30:00+00:00",
                "title": "t",
            }
        )


def test_devpost_out_list_serialization_mixed():
    adapter = TypeAdapter(list[DevPostOut])
    items = [
        HNPostOut(
            id=1,
            display_order=1,
            url="https://news.ycombinator.com/item?id=1",
            published_at=_dt(),
            title="hn",
            hn_url="https://news.ycombinator.com/item?id=1",
            points=10,
            comments=2,
        ),
        GitHubPostOut(
            id=2,
            display_order=4,
            url="https://github.com/foo/bar",
            published_at=_dt(),
            repo="foo/bar",
            title="foo/bar v1",
        ),
        XTopicDigestOut(
            id=3,
            display_order=6,
            topic="MCP",
            bullets=[
                XBullet(
                    text="t",
                    sources=[
                        XBulletSource(url="https://x.com/a/1", author_handle="a")
                    ],
                )
            ],
        ),
    ]
    dumped = adapter.dump_python(items)
    assert [d["source"] for d in dumped] == ["hn", "github", "x"]
    assert [d["display_order"] for d in dumped] == [1, 4, 6]
    # HN + GitHub have published_at as ISO string; X does not
    assert isinstance(dumped[0]["published_at"], str)
    assert isinstance(dumped[1]["published_at"], str)
    assert "published_at" not in dumped[2]
