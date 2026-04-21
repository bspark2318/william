"""X pipeline integration tests — real DB, mocked Apify + LLM."""

from datetime import datetime, timezone

from app.models import CandidateXTweet, XTopicDigestRow


def test_collect_x_inserts_tweets_and_scores(db_session, monkeypatch):
    from app.services import devs_pipeline, devs_ranker, x_source

    monkeypatch.setenv("APIFY_TOKEN", "fake")
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")
    monkeypatch.setattr(x_source, "_flatten_handles", lambda cfg: ["karpathy"])

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        x_source,
        "fetch_tweets_via_apify",
        lambda handles, **kw: [
            {
                "url": "https://twitter.com/karpathy/status/1",
                "author_handle": "karpathy",
                "author_name": "Andrej",
                "author_avatar_url": None,
                "text": "MCP servers are cool",
                "likes": 100,
                "reposts": 20,
                "replies": 5,
                "published_at": now,
            }
        ],
    )

    count = devs_pipeline.collect_x(db_session)
    assert count == 1

    row = db_session.query(CandidateXTweet).one()
    assert row.author_handle == "karpathy"
    assert row.quality_score is not None
    assert row.quality_score > 0


def test_publish_x_clusters_and_synthesizes_bullets(db_session, monkeypatch):
    from app.services import devs_pipeline, devs_ranker

    now = datetime.now(timezone.utc)
    for i in range(3):
        db_session.add(
            CandidateXTweet(
                url=f"https://x.com/a/status/{i}",
                author_handle="a",
                text=f"tweet {i}",
                published_at=now,
                collected_at=now,
                quality_score=8.0,
            )
        )
    db_session.commit()

    tweet_ids = [t.id for t in db_session.query(CandidateXTweet).all()]

    monkeypatch.setattr(
        devs_ranker,
        "cluster_tweets_into_topics",
        lambda tweets: {"MCP patterns": tweet_ids},
    )
    monkeypatch.setattr(
        devs_ranker,
        "synthesize_topic_digest",
        lambda label, tweets: [
            {
                "text": "MCP is converging.",
                "sources": [
                    {
                        "url": tweets[0]["url"],
                        "author_handle": "a",
                        "author_name": None,
                    }
                ],
            }
        ],
    )

    count = devs_pipeline.publish_x(db_session, start_order=6)
    assert count == 1

    digest = db_session.query(XTopicDigestRow).one()
    assert digest.topic == "MCP patterns"
    assert digest.display_order == 6
    assert digest.is_active is True
    assert digest.bullets[0]["text"] == "MCP is converging."
    assert digest.rank_score == 8.0  # avg of cluster quality_scores


def test_publish_x_backlinks_used_in_digest_id(db_session, monkeypatch):
    from app.services import devs_pipeline, devs_ranker

    now = datetime.now(timezone.utc)
    cited = CandidateXTweet(
        url="https://x.com/a/status/1",
        author_handle="a",
        text="cited",
        published_at=now,
        collected_at=now,
        quality_score=9.0,
    )
    uncited = CandidateXTweet(
        url="https://x.com/a/status/2",
        author_handle="a",
        text="uncited",
        published_at=now,
        collected_at=now,
        quality_score=8.0,
    )
    db_session.add_all([cited, uncited])
    db_session.commit()

    monkeypatch.setattr(
        devs_ranker,
        "cluster_tweets_into_topics",
        lambda ts: {"MCP": [cited.id, uncited.id]},
    )
    monkeypatch.setattr(
        devs_ranker,
        "synthesize_topic_digest",
        lambda label, tweets: [
            {
                "text": "b",
                "sources": [
                    {"url": "https://x.com/a/status/1", "author_handle": "a"}
                ],
            }
        ],
    )

    devs_pipeline.publish_x(db_session, start_order=6)

    digest = db_session.query(XTopicDigestRow).one()
    db_session.refresh(cited)
    db_session.refresh(uncited)

    assert cited.used_in_digest_id == digest.id
    assert cited.topic_cluster == "MCP"
    # Uncited tweet in the same cluster must NOT be backlinked.
    assert uncited.used_in_digest_id is None
    assert uncited.topic_cluster is None


def test_publish_x_assigns_slots_6_to_8(db_session, monkeypatch):
    from app.services import devs_pipeline, devs_ranker

    now = datetime.now(timezone.utc)
    for i in range(9):
        db_session.add(
            CandidateXTweet(
                url=f"https://x.com/a/status/{i}",
                author_handle="a",
                text=f"t{i}",
                published_at=now,
                collected_at=now,
                quality_score=8.0,
            )
        )
    db_session.commit()

    all_tweets = db_session.query(CandidateXTweet).order_by(CandidateXTweet.id).all()
    ids = [t.id for t in all_tweets]

    monkeypatch.setattr(
        devs_ranker,
        "cluster_tweets_into_topics",
        lambda ts: {
            "topic_a": ids[0:3],
            "topic_b": ids[3:6],
            "topic_c": ids[6:9],
        },
    )
    monkeypatch.setattr(
        devs_ranker,
        "synthesize_topic_digest",
        lambda label, tweets: [
            {
                "text": label,
                "sources": [{"url": tweets[0]["url"], "author_handle": "a"}],
            }
        ],
    )

    count = devs_pipeline.publish_x(db_session, start_order=6)
    assert count == 3

    digests = (
        db_session.query(XTopicDigestRow)
        .order_by(XTopicDigestRow.display_order)
        .all()
    )
    assert [d.display_order for d in digests] == [6, 7, 8]
