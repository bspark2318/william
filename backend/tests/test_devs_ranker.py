"""Unit tests for devs_ranker — no DB, all LLM calls mocked."""

import json

from app.services import devs_ranker


# ---------------------------------------------------------------------------
# rank_hn_post
# ---------------------------------------------------------------------------

def test_rank_hn_post_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")
    out = devs_ranker.rank_hn_post(
        {"title": "Show HN: Claude Code sub-agents", "points": 100, "comments": 50}
    )
    assert "score" in out
    assert "topics" in out
    assert out["score"] > 0
    assert out["topics"] == []


def test_rank_hn_post_llm_success(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker,
        "_call_openai",
        lambda system, user, model="gpt-4o-mini": json.dumps(
            {"score": 8.5, "topics": ["mcp", "agents"]}
        ),
    )
    out = devs_ranker.rank_hn_post(
        {"title": "MCP server patterns", "points": 50, "comments": 20}
    )
    assert out == {"score": 8.5, "topics": ["mcp", "agents"]}


def test_rank_hn_post_llm_bad_json_falls_back(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker, "_call_openai", lambda system, user, model="gpt-4o-mini": "not json"
    )
    out = devs_ranker.rank_hn_post({"title": "x", "points": 10, "comments": 5})
    assert out["score"] > 0
    assert out["topics"] == []


# ---------------------------------------------------------------------------
# rank_github_post
# ---------------------------------------------------------------------------

def test_rank_github_post_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")
    out = devs_ranker.rank_github_post({"repo": "a/b", "title": "release", "stars": 1000})
    assert out["score"] > 0
    assert out["topics"] == []


def test_rank_github_post_llm_success(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker,
        "_call_openai",
        lambda s, u, model="gpt-4o-mini": json.dumps({"score": 9.0, "topics": ["coding agents"]}),
    )
    out = devs_ranker.rank_github_post(
        {"repo": "anthropics/claude-code", "title": "v1.2", "stars": 5000}
    )
    assert out == {"score": 9.0, "topics": ["coding agents"]}


# ---------------------------------------------------------------------------
# rank_x_tweet
# ---------------------------------------------------------------------------

def test_rank_x_tweet_batch_fallback(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")
    tweets = [
        {"id": 1, "author_handle": "a", "text": "t", "likes": 10, "reposts": 2, "replies": 1},
        {"id": 2, "author_handle": "b", "text": "t2", "likes": 100, "reposts": 50, "replies": 20},
    ]
    out = devs_ranker.rank_x_tweet(tweets)
    assert isinstance(out, list)
    assert len(out) == 2
    assert all("quality_score" in o for o in out)
    assert out[1]["quality_score"] > out[0]["quality_score"]


def test_rank_x_tweet_batch_llm_success(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker,
        "_call_openai",
        lambda s, u, model="gpt-4o-mini": json.dumps(
            [
                {"id": 1, "quality_score": 8.0, "topics": ["mcp"]},
                {"id": 2, "quality_score": 3.0, "topics": []},
            ]
        ),
    )
    tweets = [
        {"id": 1, "author_handle": "a", "text": "t", "likes": 10, "reposts": 2, "replies": 1},
        {"id": 2, "author_handle": "b", "text": "t2", "likes": 100, "reposts": 50, "replies": 20},
    ]
    out = devs_ranker.rank_x_tweet(tweets)
    assert out == [
        {"id": 1, "quality_score": 8.0, "topics": ["mcp"]},
        {"id": 2, "quality_score": 3.0, "topics": []},
    ]


def test_rank_x_tweet_single_form(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")
    out = devs_ranker.rank_x_tweet(
        {"id": 1, "author_handle": "a", "text": "t", "likes": 5, "reposts": 1, "replies": 0}
    )
    assert isinstance(out, dict)
    assert "quality_score" in out
    assert "topics" in out


def test_rank_x_tweet_empty_batch():
    assert devs_ranker.rank_x_tweet([]) == []


# ---------------------------------------------------------------------------
# summarize_hn_thread
# ---------------------------------------------------------------------------

def test_summarize_hn_thread_empty_comments():
    assert devs_ranker.summarize_hn_thread("title", []) == []


def test_summarize_hn_thread_fallback(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")
    comments = [
        "I tried Claude Code last week. It actually works well for small refactors.",
        "The MCP integration is underrated. Saves me a ton of prompt-building time.",
    ]
    out = devs_ranker.summarize_hn_thread("HN Post", comments)
    assert len(out) >= 1
    assert all(isinstance(s, str) for s in out)


def test_summarize_hn_thread_llm_success(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker,
        "_call_openai",
        lambda s, u, model="gpt-4o-mini": json.dumps(["Bullet 1", "Bullet 2"]),
    )
    out = devs_ranker.summarize_hn_thread("t", ["comment1", "comment2"])
    assert out == ["Bullet 1", "Bullet 2"]


def test_summarize_hn_thread_bad_json(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker, "_call_openai", lambda s, u, model="gpt-4o-mini": "not json"
    )
    out = devs_ranker.summarize_hn_thread("t", ["c"])
    assert out == []


# ---------------------------------------------------------------------------
# extract_github_insights
# ---------------------------------------------------------------------------

def test_extract_github_insights_llm_success(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker,
        "_call_openai",
        lambda s, u, model="gpt-4o-mini": json.dumps(
            {
                "release_bullets": ["Added MCP support", "Breaks old tool api"],
                "why_it_matters": "Faster agent tool-use.",
                "has_breaking_changes": True,
            }
        ),
    )
    out = devs_ranker.extract_github_insights("a/b", "notes")
    assert out["release_bullets"] == ["Added MCP support", "Breaks old tool api"]
    assert out["why_it_matters"] == "Faster agent tool-use."
    assert out["has_breaking_changes"] is True


def test_extract_github_insights_heuristic_detects_breaking(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")
    notes = "- Added feature X\n- Breaking change: removed deprecated API"
    out = devs_ranker.extract_github_insights("a/b", notes)
    assert out["has_breaking_changes"] is True
    assert len(out["release_bullets"]) >= 1


def test_extract_github_insights_heuristic_no_breaking(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")
    out = devs_ranker.extract_github_insights("a/b", "- new feature shipped")
    assert out["has_breaking_changes"] is False


def test_extract_github_insights_empty_notes(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")
    out = devs_ranker.extract_github_insights("a/b", "")
    assert out["has_breaking_changes"] is False
    assert isinstance(out["release_bullets"], list)


# ---------------------------------------------------------------------------
# cluster_tweets_into_topics
# ---------------------------------------------------------------------------

def test_cluster_tweets_empty():
    assert devs_ranker.cluster_tweets_into_topics([]) == {}


def test_cluster_tweets_fallback_single_bucket(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")
    out = devs_ranker.cluster_tweets_into_topics(
        [{"id": 1, "author_handle": "a", "text": "hi"}, {"id": 2, "author_handle": "b", "text": "yo"}]
    )
    assert out == {"general": [1, 2]}


def test_cluster_tweets_llm_success(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker,
        "_call_openai",
        lambda s, u, model="gpt-4o-mini": json.dumps(
            {"MCP patterns": [1, 2], "Agent evals": [3]}
        ),
    )
    out = devs_ranker.cluster_tweets_into_topics(
        [
            {"id": 1, "author_handle": "a", "text": "x"},
            {"id": 2, "author_handle": "b", "text": "y"},
            {"id": 3, "author_handle": "c", "text": "z"},
        ]
    )
    assert out == {"MCP patterns": [1, 2], "Agent evals": [3]}


# ---------------------------------------------------------------------------
# synthesize_topic_digest
# ---------------------------------------------------------------------------

def test_synthesize_digest_empty():
    assert devs_ranker.synthesize_topic_digest("t", []) == []


def test_synthesize_digest_fallback(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "")
    tweets = [
        {
            "id": 1,
            "url": "https://twitter.com/a/status/1",
            "author_handle": "a",
            "author_name": "Alice",
            "text": "MCP is great for agentic coding. You should try it.",
        }
    ]
    out = devs_ranker.synthesize_topic_digest("MCP", tweets)
    assert len(out) == 1
    assert out[0]["sources"][0]["url"] == "https://twitter.com/a/status/1"
    assert out[0]["sources"][0]["author_handle"] == "a"


def test_synthesize_digest_llm_success(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker,
        "_call_openai",
        lambda s, u, model="gpt-4o-mini": json.dumps(
            [
                {
                    "text": "Engineers are converging on MCP for tool standardization.",
                    "sources": [
                        {
                            "url": "https://twitter.com/a/status/1",
                            "author_handle": "a",
                            "author_name": "Alice",
                        }
                    ],
                }
            ]
        ),
    )
    tweets = [
        {
            "id": 1,
            "url": "https://twitter.com/a/status/1",
            "author_handle": "a",
            "author_name": "Alice",
            "text": "MCP FTW",
        }
    ]
    out = devs_ranker.synthesize_topic_digest("MCP", tweets)
    assert len(out) == 1
    assert out[0]["text"].startswith("Engineers")
    assert out[0]["sources"][0]["author_handle"] == "a"


def test_synthesize_digest_drops_hallucinated_source_urls(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker,
        "_call_openai",
        lambda s, u, model="gpt-4o-mini": json.dumps(
            [
                {
                    "text": "Valid bullet citing a real tweet.",
                    "sources": [
                        {
                            "url": "https://twitter.com/a/status/1",
                            "author_handle": "a",
                            "author_name": "Alice",
                        }
                    ],
                },
                {
                    "text": "Hallucinated bullet citing a fake url.",
                    "sources": [
                        {
                            "url": "https://twitter.com/ghost/status/999",
                            "author_handle": "ghost",
                            "author_name": "Ghost",
                        }
                    ],
                },
            ]
        ),
    )
    tweets = [
        {
            "id": 1,
            "url": "https://twitter.com/a/status/1",
            "author_handle": "a",
            "author_name": "Alice",
            "text": "MCP FTW",
        }
    ]
    out = devs_ranker.synthesize_topic_digest("MCP", tweets)
    assert len(out) == 1
    assert out[0]["text"] == "Valid bullet citing a real tweet."
    assert out[0]["sources"][0]["url"] == "https://twitter.com/a/status/1"


def test_synthesize_digest_all_hallucinated_falls_back(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker,
        "_call_openai",
        lambda s, u, model="gpt-4o-mini": json.dumps(
            [
                {
                    "text": "Fabricated 1",
                    "sources": [
                        {
                            "url": "https://twitter.com/ghost/status/999",
                            "author_handle": "ghost",
                            "author_name": "Ghost",
                        }
                    ],
                },
                {
                    "text": "Fabricated 2",
                    "sources": [
                        {
                            "url": "https://twitter.com/nope/status/42",
                            "author_handle": "nope",
                            "author_name": "Nope",
                        }
                    ],
                },
            ]
        ),
    )
    tweets = [
        {
            "id": 1,
            "url": "https://twitter.com/a/status/1",
            "author_handle": "a",
            "author_name": "Alice",
            "text": "MCP is great for agentic coding. You should try it.",
        }
    ]
    out = devs_ranker.synthesize_topic_digest("MCP", tweets)
    assert len(out) >= 1
    for b in out:
        assert len(b["sources"]) >= 1
        for src in b["sources"]:
            assert src["url"] == "https://twitter.com/a/status/1"


def test_synthesize_digest_drops_bullets_without_sources(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker,
        "_call_openai",
        lambda s, u, model="gpt-4o-mini": json.dumps(
            [{"text": "no sources", "sources": []}]
        ),
    )
    tweets = [
        {
            "id": 1,
            "url": "https://twitter.com/a/status/1",
            "author_handle": "a",
            "author_name": "Alice",
            "text": "x",
        }
    ]
    # Falls back because LLM gave no valid bullets.
    out = devs_ranker.synthesize_topic_digest("T", tweets)
    assert len(out) >= 1
    assert all(len(b["sources"]) >= 1 for b in out)
