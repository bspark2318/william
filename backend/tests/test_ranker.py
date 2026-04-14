import json

from app.services import ranker


# ---------------------------------------------------------------------------
# quick_rank_stories
# ---------------------------------------------------------------------------

def test_quick_rank_stories_empty_no_key(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "")
    assert ranker.quick_rank_stories([]) == []


def test_quick_rank_stories_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "")
    out = ranker.quick_rank_stories(
        [{"id": 1, "title": "a", "source": "c", "tavily_score": 0.75}]
    )
    assert out == [{"id": 1, "score": 7.5}]


def test_quick_rank_stories_success(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "fake")

    def fake_openai(system, user):
        return json.dumps([{"id": 1, "score": 9.0}])

    monkeypatch.setattr(ranker, "_call_openai", fake_openai)
    out = ranker.quick_rank_stories([{"id": 1, "title": "a", "source": "c"}])
    assert out == [{"id": 1, "score": 9.0}]


def test_quick_rank_stories_parse_error(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(ranker, "_call_openai", lambda s, u: "not json")
    out = ranker.quick_rank_stories([{"id": 1, "title": "a", "source": "c"}])
    assert out == [{"id": 1, "score": 5.0}]


# ---------------------------------------------------------------------------
# quick_rank_videos
# ---------------------------------------------------------------------------

def test_quick_rank_videos_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "")
    out = ranker.quick_rank_videos([{"id": 2, "title": "v", "channel": "ch"}])
    assert out == [{"id": 2, "score": 0}]


def test_quick_rank_videos_success(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(ranker, "_call_openai", lambda s, u: json.dumps([{"id": 2, "score": 8.0}]))
    out = ranker.quick_rank_videos([{"id": 2, "title": "v", "channel": "ch"}])
    assert out == [{"id": 2, "score": 8.0}]


# ---------------------------------------------------------------------------
# comparative_select_stories
# ---------------------------------------------------------------------------

def test_comparative_select_stories_fallback(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "")
    cands = [
        {"id": 1, "title": "a", "summary": "x", "source": "s", "importance_score": 9},
        {"id": 2, "title": "b", "summary": "y", "source": "s", "importance_score": 7},
    ]
    out = ranker.comparative_select_stories(cands)
    assert out[0]["id"] == 1
    assert out[0]["rank"] == 1


def test_comparative_select_stories_success(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        ranker, "_call_openai",
        lambda s, u: json.dumps([{"id": 1, "rank": 1, "topic": "models"}]),
    )
    out = ranker.comparative_select_stories(
        [{"id": 1, "title": "a", "summary": "x", "source": "s"}]
    )
    assert out == [{"id": 1, "rank": 1, "topic": "models"}]


# ---------------------------------------------------------------------------
# comparative_select_videos
# ---------------------------------------------------------------------------

def test_comparative_select_videos_fallback(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "")
    cands = [
        {"id": 1, "title": "v", "channel": "c", "description": "d", "importance_score": 8},
    ]
    out = ranker.comparative_select_videos(cands)
    assert out[0]["id"] == 1


def test_comparative_select_videos_with_rich_metadata(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        ranker, "_call_openai",
        lambda s, u: json.dumps([{"id": 1, "rank": 1, "topic": "llm"}]),
    )
    cands = [{
        "id": 1, "title": "v", "channel": "c", "description": "d",
        "content_type": "deep_analysis", "view_velocity": 300.0,
        "engagement_rate": 0.02, "duration_seconds": 900,
        "channel_tier": "top", "transcript_excerpt": "some transcript...",
    }]
    out = ranker.comparative_select_videos(cands)
    assert out == [{"id": 1, "rank": 1, "topic": "llm"}]


# ---------------------------------------------------------------------------
# classify_video_content
# ---------------------------------------------------------------------------

def test_classify_regex_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "")
    cands = [
        {"id": 1, "title": "How to fine-tune LLMs", "channel": "c", "description": "tutorial"},
        {"id": 2, "title": "GPT-5 deep dive analysis", "channel": "c", "description": ""},
        {"id": 3, "title": "AI news this week roundup", "channel": "c", "description": ""},
        {"id": 4, "title": "My reaction to Claude 4", "channel": "c", "description": ""},
    ]
    out = ranker.classify_video_content(cands)
    type_map = {c["id"]: c["content_type"] for c in out}
    assert type_map[1] == "tutorial"
    assert type_map[2] == "deep_analysis"
    assert type_map[3] == "news_roundup"
    assert type_map[4] == "reaction"


def test_classify_llm_success(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        ranker, "_call_openai",
        lambda s, u: json.dumps([{"id": 1, "content_type": "demo"}]),
    )
    out = ranker.classify_video_content([{"id": 1, "title": "t", "channel": "c"}])
    assert out == [{"id": 1, "content_type": "demo"}]


def test_classify_empty():
    assert ranker.classify_video_content([]) == []


# ---------------------------------------------------------------------------
# tight_bullets + generate_title (unchanged)
# ---------------------------------------------------------------------------

def test_generate_title_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "")
    assert ranker.generate_title([{"title": "Any"}]) == "This Week in AI"


def test_tight_bullets_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "")
    raw = (
        "OpenAI shipped a new model. It scores higher on math benchmarks. "
        "Enterprise API pricing unchanged. Rollout starts this week."
    )
    out = ranker.tight_bullets("Some title", raw)
    assert len(out) >= 2
    assert all(isinstance(s, str) and s for s in out)


def test_tight_bullets_parses_llm_json(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(
        ranker, "_call_openai",
        lambda s, u: json.dumps(["Alpha", "Beta", "Gamma"]),
    )
    assert ranker.tight_bullets("T", "body") == ["Alpha", "Beta", "Gamma"]
