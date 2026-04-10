import json
import logging

from openai import OpenAI

from ..config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

_STORY_SYSTEM_PROMPT = """\
You are an expert AI-news editor. You will receive a JSON array of candidate news articles about artificial intelligence.

Score each article from 1 to 10 based on:
- Impact on the AI field (weight: 3x)
- Breadth of interest to AI practitioners (weight: 2x)
- Novelty / newsworthiness (weight: 2x)
- Source credibility (weight: 1x)

Return ONLY a JSON array: [{"id": <int>, "score": <float>, "reasoning": "<one sentence>"}]
No markdown fences, no extra text."""

_VIDEO_SYSTEM_PROMPT = """\
You are an expert AI-content curator. You will receive a JSON array of candidate YouTube videos about artificial intelligence.

Score each video from 1 to 10 based on:
- Educational value for AI practitioners (weight: 3x)
- Production quality signals (title clarity, channel reputation) (weight: 2x)
- Timeliness / relevance to current AI trends (weight: 2x)
- Uniqueness of perspective (weight: 1x)

Return ONLY a JSON array: [{"id": <int>, "score": <float>, "reasoning": "<one sentence>"}]
No markdown fences, no extra text."""

_TITLE_SYSTEM_PROMPT = """\
You are a newspaper headline writer for "The AI Prophet", an AI-focused weekly newsletter.
Given the top stories of the week, generate a single punchy issue title (3-8 words).
Return ONLY the title string, no quotes, no extra text."""


def _call_openai(system: str, user: str) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content.strip()


def rank_stories(candidates: list[dict]) -> list[dict]:
    """Score candidate stories via LLM. Returns list of {id, score, reasoning}."""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — returning unscored candidates")
        return [{"id": c["id"], "score": c.get("tavily_score", 0) or 0, "reasoning": "no LLM"} for c in candidates]

    if not candidates:
        return []

    payload = json.dumps(
        [{"id": c["id"], "title": c["title"], "summary": c["summary"][:300], "source": c["source"]} for c in candidates]
    )
    raw = _call_openai(_STORY_SYSTEM_PROMPT, payload)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse ranker response: %s", raw[:500])
        return [{"id": c["id"], "score": 5.0, "reasoning": "parse error"} for c in candidates]


def rank_videos(candidates: list[dict]) -> list[dict]:
    """Score candidate videos via LLM. Returns list of {id, score, reasoning}."""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — returning unscored candidates")
        return [{"id": c["id"], "score": 0, "reasoning": "no LLM"} for c in candidates]

    if not candidates:
        return []

    payload = json.dumps(
        [{"id": c["id"], "title": c["title"], "channel": c["channel"], "description": (c.get("description") or "")[:200]} for c in candidates]
    )
    raw = _call_openai(_VIDEO_SYSTEM_PROMPT, payload)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse video ranker response: %s", raw[:500])
        return [{"id": c["id"], "score": 5.0, "reasoning": "parse error"} for c in candidates]


def generate_title(top_stories: list[dict]) -> str:
    """Generate a catchy issue title from the week's top stories."""
    if not OPENAI_API_KEY:
        return "This Week in AI"

    summaries = "\n".join(f"- {s['title']}" for s in top_stories)
    return _call_openai(_TITLE_SYSTEM_PROMPT, summaries)
