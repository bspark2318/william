import json
import logging
import time

from openai import APITimeoutError, OpenAI

from ..config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BACKOFF = 2

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
You are an expert AI-content curator. You will receive a JSON array of candidate YouTube videos about artificial intelligence. Each entry includes view count and duration in seconds.

Score each video from 1 to 10 based on:
- Newsworthiness / covers a significant AI development (weight: 3x)
- Educational value for AI practitioners (weight: 2x)
- Production quality signals: channel reputation, view count relative to recency, title clarity (weight: 2x)
- Uniqueness of perspective — penalise generic tutorials and clickbait (weight: 1x)

Prefer videos that cover breaking news, new model releases, benchmark results, policy changes, or novel research over generic explainers.

Return ONLY a JSON array: [{"id": <int>, "score": <float>, "reasoning": "<one sentence>"}]
No markdown fences, no extra text."""

_TITLE_SYSTEM_PROMPT = """\
You are a newspaper headline writer for "The Context Window", an AI-focused weekly newsletter.
Given the top stories of the week, generate a single punchy issue title (3-8 words).
Return ONLY the title string, no quotes, no extra text."""

_BULLETS_SYSTEM_PROMPT = """\
You extract the key facts from an AI news article into 2-4 informative bullet points.

Each bullet must be a discrete, standalone fact with enough context that a reader unfamiliar with the story understands what happened and why it matters.

Format rules:
- Return ONLY a JSON array of 2-4 strings. No markdown, no keys, no extra text.
- 10-20 words per bullet. Full sentences are fine; fragments are fine too.
- Lead with the specific fact, number, or name — never start with "The company" / "Researchers" / "The model".
- At least one bullet should convey impact or consequence ("...enabling X", "...which means Y").
- Include concrete numbers, benchmarks, or comparisons when they appear in the source.
- No opinions, no "significant", no "groundbreaking", no filler adjectives.

Good: ["GPT-5 processes text, image, and audio natively — first unified multimodal model from OpenAI", "Scores 3× higher on GPQA science benchmark, closing the gap with domain experts", "Code-gen Elo jumps 200 pts over GPT-4o, reaching top-5 on LiveCodeBench"]
Bad: ["OpenAI has released a new model that can handle multiple types of input simultaneously"]"""


def _fallback_bullets(raw: str) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return []
    parts = []
    for chunk in text.replace("?", ".").replace("!", ".").split("."):
        c = chunk.strip()
        if len(c) > 8:
            parts.append(c[:120] + ("…" if len(c) > 120 else ""))
        if len(parts) >= 4:
            break
    return parts[:4] if parts else [text[:200]]


def _call_openai(system: str, user: str) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=30.0)
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.3,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content.strip()
        except APITimeoutError:
            if attempt == _MAX_RETRIES - 1:
                raise
            wait = _RETRY_BACKOFF ** attempt
            logger.warning("OpenAI timeout (attempt %d/%d), retrying in %ds", attempt + 1, _MAX_RETRIES, wait)
            time.sleep(wait)
    raise RuntimeError("unreachable")


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
        [
            {
                "id": c["id"],
                "title": c["title"],
                "channel": c["channel"],
                "description": (c.get("description") or "")[:300],
                "view_count": c.get("view_count", 0),
                "duration_seconds": c.get("duration_seconds", 0),
            }
            for c in candidates
        ]
    )
    raw = _call_openai(_VIDEO_SYSTEM_PROMPT, payload)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse video ranker response: %s", raw[:500])
        return [{"id": c["id"], "score": 5.0, "reasoning": "parse error"} for c in candidates]


def tight_bullets(title: str, raw_content: str) -> list[str]:
    """Turn Tavily-style prose into 3–4 terse bullet strings for the issue."""
    body = (raw_content or "").strip()[:4000]
    if not body and not (title or "").strip():
        return []

    if not OPENAI_API_KEY:
        return _fallback_bullets(body or title)

    user = f"Title: {title}\n\nBody:\n{body}"
    raw = _call_openai(_BULLETS_SYSTEM_PROMPT, user)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list) and all(isinstance(x, str) and x.strip() for x in parsed):
            out = [x.strip() for x in parsed[:4]]
            return out if len(out) >= 2 else _fallback_bullets(body)
    except json.JSONDecodeError:
        logger.warning("tight_bullets JSON parse failed: %s", raw[:200])
    return _fallback_bullets(body)


def generate_title(top_stories: list[dict]) -> str:
    """Generate a catchy issue title from the week's top stories."""
    if not OPENAI_API_KEY:
        return "This Week in AI"

    summaries = "\n".join(f"- {s['title']}" for s in top_stories)
    return _call_openai(_TITLE_SYSTEM_PROMPT, summaries)
