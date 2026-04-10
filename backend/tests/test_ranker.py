import json

from app.services import ranker


def test_rank_stories_empty_no_key(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "")
    assert ranker.rank_stories([]) == []


def test_rank_stories_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "")
    out = ranker.rank_stories(
        [{"id": 1, "title": "a", "summary": "b", "source": "c", "tavily_score": 7.5}]
    )
    assert out == [{"id": 1, "score": 7.5, "reasoning": "no LLM"}]


def test_rank_videos_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "")
    out = ranker.rank_videos([{"id": 2, "title": "v", "channel": "ch", "description": "d"}])
    assert out == [{"id": 2, "score": 0, "reasoning": "no LLM"}]


def test_generate_title_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "")
    assert ranker.generate_title([{"title": "Any"}]) == "This Week in AI"


def test_rank_stories_parse_error_uses_default(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "fake")

    def bad_openai(system, user):
        return "not json"

    monkeypatch.setattr(ranker, "_call_openai", bad_openai)
    out = ranker.rank_stories(
        [{"id": 1, "title": "a", "summary": "b" * 400, "source": "c"}]
    )
    assert out == [{"id": 1, "score": 5.0, "reasoning": "parse error"}]


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

    def fake_openai(system, user):
        return json.dumps(["Alpha", "Beta", "Gamma"])

    monkeypatch.setattr(ranker, "_call_openai", fake_openai)
    assert ranker.tight_bullets("T", "body") == ["Alpha", "Beta", "Gamma"]


def test_rank_stories_success(monkeypatch):
    monkeypatch.setattr(ranker, "OPENAI_API_KEY", "fake")

    def fake_openai(system, user):
        return json.dumps([{"id": 1, "score": 9.0, "reasoning": "ok"}])

    monkeypatch.setattr(ranker, "_call_openai", fake_openai)
    out = ranker.rank_stories(
        [{"id": 1, "title": "a", "summary": "short", "source": "c"}]
    )
    assert out == [{"id": 1, "score": 9.0, "reasoning": "ok"}]
