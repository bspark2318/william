"""GitHub pipeline integration tests — real DB, mocked HTTP + LLM."""

from datetime import datetime, timedelta, timezone

from app.models import DevPost, RepoStarSnapshot


def test_collect_github_writes_snapshots_for_velocity(db_session, monkeypatch):
    from app.services import devs_pipeline, devs_ranker, github_source

    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")

    now = datetime.now(timezone.utc)

    monkeypatch.setattr(
        github_source,
        "_load_config",
        lambda: {"github_topics": ["llm"], "topic_search_cap": 10, "github_curated_repos": []},
    )
    monkeypatch.setattr(
        github_source,
        "fetch_topic_candidates",
        lambda topics, *, cap=50, stars_floor=50, forks_floor=0, lang_allowlist=None, topic_blocklist=None, token=None, client=None, today=None: [
            {
                "kind": "trending",
                "repo": "acme/widget",
                "url": "https://github.com/acme/widget",
                "title": "widget description",
                "stars": 1500,
                "forks": 300,
                "published_at": now,
                "topics": ["llm"],
            }
        ],
    )
    monkeypatch.setattr(
        github_source,
        "fetch_releases",
        lambda repos, *, token=None, client=None, today=None: [],
    )

    count = devs_pipeline.collect_github(db_session)
    assert count == 1

    snaps = db_session.query(RepoStarSnapshot).filter_by(repo="acme/widget").all()
    assert len(snaps) == 1
    assert snaps[0].stars == 1500


def test_velocity_with_prior_snapshots_computes_delta(db_session, monkeypatch):
    """collect_github writes stars_velocity_7d using the velocity helper."""
    from app.services import devs_pipeline, devs_ranker, github_source

    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")

    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            RepoStarSnapshot(
                repo="a/b", stars=500, observed_at=now - timedelta(days=10)
            ),
            RepoStarSnapshot(
                repo="a/b", stars=800, observed_at=now - timedelta(minutes=1)
            ),
        ]
    )
    db_session.add(
        DevPost(
            source="github",
            url="https://github.com/a/b/releases/tag/v1",
            published_at=now,
            collected_at=now,
            title="a/b v1",
            repo="a/b",
            stars=800,
            importance_score=None,
            is_active=False,
        )
    )
    db_session.commit()

    # No fresh ingest — we want to isolate the scoring+velocity branch.
    monkeypatch.setattr(github_source, "fetch_trending", lambda *a, **kw: [])
    monkeypatch.setattr(github_source, "fetch_releases", lambda *a, **kw: [])

    devs_pipeline.collect_github(db_session)

    row = db_session.query(DevPost).filter_by(repo="a/b").one()
    assert row.stars_velocity_7d == 300  # 800 - 500
    assert row.rank_features["stars_velocity_7d"] == 300


def test_velocity_without_prior_snapshots_returns_none(db_session, monkeypatch):
    """One recent snapshot → no baseline ≥7d old → velocity stays None."""
    from app.services import devs_pipeline, devs_ranker, github_source

    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")

    now = datetime.now(timezone.utc)
    db_session.add(
        RepoStarSnapshot(repo="a/b", stars=200, observed_at=now - timedelta(days=2))
    )
    db_session.add(
        DevPost(
            source="github",
            url="https://github.com/a/b/releases/tag/v1",
            published_at=now,
            collected_at=now,
            title="a/b v1",
            repo="a/b",
            stars=200,
            importance_score=None,
            is_active=False,
        )
    )
    db_session.commit()

    monkeypatch.setattr(github_source, "fetch_trending", lambda *a, **kw: [])
    monkeypatch.setattr(github_source, "fetch_releases", lambda *a, **kw: [])

    devs_pipeline.collect_github(db_session)

    row = db_session.query(DevPost).filter_by(repo="a/b").one()
    assert row.stars_velocity_7d is None
    assert row.rank_features["stars_velocity_7d"] is None


def test_publish_github_populates_insights(db_session, monkeypatch):
    from app.services import devs_pipeline, devs_ranker

    now = datetime.now(timezone.utc)
    db_session.add(
        DevPost(
            source="github",
            url="https://github.com/foo/bar/releases/tag/v1",
            published_at=now,
            collected_at=now,
            title="foo/bar v1",
            importance_score=8.0,
            is_active=False,
            repo="foo/bar",
            release_notes_excerpt="Adds X. Breaking: removed Y.",
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        devs_ranker,
        "extract_github_insights",
        lambda repo, notes: {
            "release_bullets": ["Adds feature X", "Removes legacy Y"],
            "why_it_matters": "Agentic tool-use tightens.",
            "has_breaking_changes": True,
        },
    )

    count = devs_pipeline.publish_github(db_session, start_order=4)
    assert count == 1

    row = db_session.query(DevPost).filter_by(source="github").one()
    assert row.release_bullets == ["Adds feature X", "Removes legacy Y"]
    assert row.why_it_matters == "Agentic tool-use tightens."
    assert row.has_breaking_changes is True
    assert row.is_active is True
    assert row.display_order == 4
    assert row.rank_score == 8.0


def test_publish_github_assigns_slots_4_and_5(db_session, monkeypatch):
    from app.services import devs_pipeline, devs_ranker

    monkeypatch.setattr(
        devs_ranker,
        "extract_github_insights",
        lambda r, n: {
            "release_bullets": [],
            "why_it_matters": "",
            "has_breaking_changes": False,
        },
    )

    now = datetime.now(timezone.utc)
    for i, score in enumerate([9.0, 7.0, 3.0]):
        db_session.add(
            DevPost(
                source="github",
                url=f"https://github.com/r/{i}",
                published_at=now,
                collected_at=now,
                title=f"repo {i}",
                importance_score=score,
                is_active=False,
                repo=f"r/{i}",
            )
        )
    db_session.commit()

    count = devs_pipeline.publish_github(db_session, start_order=4)
    assert count == 2  # slot_allocation default: 2 github slots

    active = (
        db_session.query(DevPost)
        .filter_by(source="github", is_active=True)
        .order_by(DevPost.display_order)
        .all()
    )
    assert [a.display_order for a in active] == [4, 5]
    # Highest importance_score first.
    assert active[0].repo == "r/0"
    assert active[1].repo == "r/1"
    # Lowest scored row left out.
    third = db_session.query(DevPost).filter_by(repo="r/2").one()
    assert third.is_active is False
