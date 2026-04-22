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
        lambda system, user, model="gpt-4o-mini", response_format=None: json.dumps(
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
        devs_ranker, "_call_openai", lambda system, user, model="gpt-4o-mini", response_format=None: "not json"
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
        lambda s, u, model="gpt-4o-mini", response_format=None: json.dumps({"score": 9.0, "topics": ["coding agents"]}),
    )
    out = devs_ranker.rank_github_post(
        {"repo": "anthropics/claude-code", "title": "v1.2", "stars": 5000}
    )
    assert out == {"score": 9.0, "topics": ["coding agents"]}


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
        lambda s, u, model="gpt-4o-mini", response_format=None: json.dumps(
            {"bullets": ["Bullet 1", "Bullet 2"]}
        ),
    )
    out = devs_ranker.summarize_hn_thread("t", ["comment1", "comment2"])
    assert out == ["Bullet 1", "Bullet 2"]


def test_summarize_hn_thread_bad_json(monkeypatch):
    monkeypatch.setattr(devs_ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        devs_ranker, "_call_openai", lambda s, u, model="gpt-4o-mini", response_format=None: "not json"
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
        lambda s, u, model="gpt-4o-mini", response_format=None: json.dumps(
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
