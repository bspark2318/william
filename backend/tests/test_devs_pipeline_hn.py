"""HN pipeline integration tests — real DB, mocked HTTP + LLM."""

from datetime import datetime, timedelta, timezone

from app.models import DevPost


def test_collect_hn_inserts_rows_and_scores(db_session, monkeypatch):
    from app.services import devs_pipeline, devs_ranker, hn_source

    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        hn_source,
        "fetch_hn_candidates",
        lambda *, limit=200, client=None: [
            {
                "hn_id": 1,
                "title": "MCP server patterns",
                "url": "https://example.com/1",
                "hn_url": "https://news.ycombinator.com/item?id=1",
                "points": 100,
                "comments": 30,
                "published_at": now,
            }
        ],
    )

    count = devs_pipeline.collect_hn(db_session)
    assert count == 1

    row = db_session.query(DevPost).filter_by(source="hn").one()
    assert row.importance_score is not None
    assert row.importance_score > 0
    assert row.rank_features == {
        "points": 100,
        "comments": 30,
        "llm_score": row.importance_score,
    }


def test_collect_hn_dedups_by_url(db_session, monkeypatch):
    from app.services import devs_pipeline, devs_ranker, hn_source

    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        hn_source,
        "fetch_hn_candidates",
        lambda *, limit=200, client=None: [
            {
                "hn_id": 1,
                "title": "MCP patterns",
                "url": "https://example.com/1",
                "hn_url": "https://news.ycombinator.com/item?id=1",
                "points": 50,
                "comments": 10,
                "published_at": now,
            }
        ],
    )

    devs_pipeline.collect_hn(db_session)
    assert db_session.query(DevPost).filter_by(source="hn").count() == 1

    # Same URL on rerun must not duplicate.
    devs_pipeline.collect_hn(db_session)
    assert db_session.query(DevPost).filter_by(source="hn").count() == 1


def test_publish_hn_populates_bullets_and_flips_active(db_session, monkeypatch):
    from app.services import devs_pipeline, devs_ranker

    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            DevPost(
                source="hn",
                url="https://hn.example/1",
                published_at=now,
                collected_at=now,
                title="HN one",
                importance_score=9.0,
                is_active=False,
                hn_url="https://news.ycombinator.com/item?id=1",
                points=200,
                comments=50,
            ),
            DevPost(
                source="hn",
                url="https://hn.example/2",
                published_at=now,
                collected_at=now,
                title="HN two",
                importance_score=7.0,
                is_active=False,
                hn_url="https://news.ycombinator.com/item?id=2",
                points=100,
                comments=20,
            ),
        ]
    )
    db_session.commit()

    monkeypatch.setattr(
        devs_pipeline,
        "fetch_hn_comments",
        lambda _id: [{"text": "a comment", "by": "u"}],
    )
    monkeypatch.setattr(
        devs_ranker,
        "summarize_hn_thread",
        lambda title, comments: ["bullet 1", "bullet 2"],
    )

    count = devs_pipeline.publish_hn(db_session, start_order=1)
    assert count == 2

    rows = (
        db_session.query(DevPost)
        .filter_by(source="hn")
        .order_by(DevPost.display_order)
        .all()
    )
    assert [r.display_order for r in rows] == [1, 2]
    assert all(r.is_active is True for r in rows)
    # Ordered by importance_score desc — importance=9 gets slot 1.
    assert rows[0].title == "HN one"
    assert rows[0].bullets == ["bullet 1", "bullet 2"]
    assert rows[0].rank_score == 9.0


def test_publish_hn_sets_top_comment_excerpt(db_session, monkeypatch):
    from app.services import devs_pipeline, devs_ranker

    now = datetime.now(timezone.utc)
    db_session.add(
        DevPost(
            source="hn",
            url="https://hn.example/top",
            published_at=now,
            collected_at=now,
            title="Top HN",
            importance_score=10.0,
            is_active=False,
            hn_url="https://news.ycombinator.com/item?id=42",
            points=500,
            comments=100,
        )
    )
    db_session.commit()

    long_text = "A" * 400
    monkeypatch.setattr(
        devs_pipeline,
        "fetch_hn_comments",
        lambda _id: [{"text": long_text, "by": "top_commenter"}],
    )
    monkeypatch.setattr(devs_ranker, "summarize_hn_thread", lambda t, c: ["b"])

    devs_pipeline.publish_hn(db_session, start_order=1)

    row = db_session.query(DevPost).filter_by(source="hn").one()
    # Spec: first 280 chars of top-scored comment text.
    assert row.top_comment_excerpt == "A" * 280


def test_publish_dev_feed_deactivates_previous_issue(db_session, monkeypatch):
    from app.services import devs_pipeline, devs_ranker

    now = datetime.now(timezone.utc)
    # Stale row outside every publish lookback window (so it won't be
    # republished) but inside the 30-day retention window (so purge won't
    # delete it). This isolates the _deactivate_active step.
    stale_ts = now - timedelta(days=10)
    old_hn = DevPost(
        source="hn",
        url="https://hn.example/old",
        published_at=stale_ts,
        collected_at=stale_ts,
        title="Stale HN",
        importance_score=5.0,
        is_active=True,
        display_order=1,
        hn_url="https://news.ycombinator.com/item?id=900",
        points=10,
        comments=1,
    )
    db_session.add(old_hn)
    db_session.commit()

    # No-op every publish path so we assert only deactivation behavior.
    monkeypatch.setattr(devs_pipeline, "fetch_hn_comments", lambda _id: [])
    monkeypatch.setattr(devs_ranker, "summarize_hn_thread", lambda t, c: [])
    monkeypatch.setattr(
        devs_ranker,
        "extract_github_insights",
        lambda r, n: {
            "release_bullets": [],
            "why_it_matters": "",
            "has_breaking_changes": False,
        },
    )

    result = devs_pipeline.publish_dev_feed(db_session)
    assert result is not None

    db_session.refresh(old_hn)
    assert old_hn.is_active is False
    assert old_hn.display_order is None
