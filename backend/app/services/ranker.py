import json
import logging
import time

from openai import APITimeoutError, OpenAI

from ..config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BACKOFF = 2

# ---------------------------------------------------------------------------
# Stage 1 — cheap daily title-only scoring
# ---------------------------------------------------------------------------

_QUICK_STORY_PROMPT = """\
You are an AI-news editor for a newsletter read by ML engineers and tech executives.
You will receive a JSON array of headlines with source names.

Score each headline 1-10 based on:
- Concrete new development: model release, benchmark, policy action, funding round (weight 3x)
- Primary source or original reporting over rehashed takes (weight 2x)
- Technical substance over hype (weight 2x)

Hard penalties (score 1-2):
- Listicles ("Top 10…", "Best AI tools…")
- Explainers or tutorials ("What is…", "How to…", "A guide to…")
- Opinion pieces or editorials with no new information
- Press-release rewrites that add no analysis

Return ONLY a JSON array: [{"id": <int>, "score": <float>}]
No markdown fences, no extra text."""

_QUICK_VIDEO_PROMPT = """\
You are an AI-content curator for a newsletter read by ML engineers and tech executives.
You will receive a JSON array of YouTube videos with metadata.

Score each video 1-10 based on:
- Covers a concrete AI development: new model, benchmark, demo, policy (weight 3x)
- High engagement velocity (views_per_hour) signals trending content — weight this over raw view count (weight 2x)
- Channel credibility: "top"/"good" tiers are trustworthy; "unknown" is neutral; "low" is suspect (weight 2x)
- Content substance from description — does it promise real analysis or just hype? (weight 2x)
- Content type: reward "deep_analysis" and "demo"; neutral for "news_roundup"/"interview"; penalise "tutorial"/"reaction"/"podcast_clip" (weight 1x)
- Duration sweet spot: 8-25 min for deep dives is ideal; very short (<3 min) or very long (>40 min) less desirable (weight 1x)

Hard penalties (score 1-2):
- Generic tutorials ("How to use ChatGPT", "Learn AI in 10 minutes")
- Clickbait titles with no substance
- Reaction/commentary videos that add nothing new
- Podcast clips without clear standalone value

Return ONLY a JSON array: [{"id": <int>, "score": <float>}]
No markdown fences, no extra text."""

# ---------------------------------------------------------------------------
# Stage 2 — comparative finals (full summaries, topic diversity)
# ---------------------------------------------------------------------------

_COMPARATIVE_STORY_PROMPT = """\
You are the editor of "The Context Window", a daily AI briefing for ML engineers and tech executives.
Below are the past 7 days' finalist articles with full summaries.

Select the 5 best for publication and rank them 1 (top) to 5.

Rules:
- Pick AT MOST 1 story per topic or event — if multiple cover the same story, keep only the strongest one and drop the rest (diversity matters)
- Prefer primary sources and original reporting
- Reject anything that is a listicle, explainer, or opinion piece with no new facts
- If fewer than 5 meet the bar, return fewer

Return ONLY a JSON array: [{"id": <int>, "rank": <int>, "topic": "<2-3 word topic>"}]
No markdown fences, no extra text."""

_COMPARATIVE_VIDEO_PROMPT = """\
You are the editor of "The Context Window", a daily AI briefing for ML engineers and tech executives.
Below are the past 7 days' finalist videos with descriptions, metadata, and transcript excerpts (when available).

Select the 3 best for publication and rank them 1 (top) to 3.

Some entries may have been highlighted in a recent edition; if one is still among the strongest and most substantive choices, you may include it again.

Rules:
- Pick AT MOST 1 video per topic — if multiple cover the same story, keep only the strongest one and drop the rest (diversity matters)
- Prefer deep analysis and original reporting over reaction/commentary
- Avoid selecting 2+ news roundups — at most 1
- If a transcript excerpt is provided, use it to judge actual content quality and depth
- At least one video should be a demo or deep-dive if available
- Higher engagement_pct and views_per_hour signal quality — prefer these over raw views
- Channel tier "top"/"good" adds credibility; "low" is a red flag
- If fewer than 3 meet the bar, return fewer

Return ONLY a JSON array: [{"id": <int>, "rank": <int>, "topic": "<2-3 word topic>"}]
No markdown fences, no extra text."""

# ---------------------------------------------------------------------------
# Content-type classification
# ---------------------------------------------------------------------------

_CLASSIFY_VIDEO_PROMPT = """\
You are classifying YouTube videos about AI/ML into content types.
You will receive a JSON array of videos with title, channel, description, and optionally a transcript excerpt.

Classify each into exactly ONE of these types:
- "deep_analysis": in-depth technical breakdown, paper walkthrough, architecture deep-dive
- "news_roundup": daily AI news compilation covering multiple stories
- "demo": product demo, hands-on walkthrough, showing a tool/model in action
- "tutorial": how-to, educational, step-by-step learning content
- "reaction": commentary/reaction to someone else's work, hot takes
- "interview": conversation, podcast, fireside chat with guests
- "podcast_clip": clip from a longer podcast episode
- "other": anything that doesn't fit above

Return ONLY a JSON array: [{"id": <int>, "content_type": "<type>"}]
No markdown fences, no extra text."""

# ---------------------------------------------------------------------------
# Kept from original: title generation + bullet points
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _call_openai(
    system: str,
    user: str,
    *,
    model: str = "gpt-4o-mini",
    response_format: dict | None = None,
) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=120.0)
    for attempt in range(_MAX_RETRIES):
        try:
            kwargs: dict = {
                "model": model,
                "temperature": 0.3,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            if response_format is not None:
                kwargs["response_format"] = response_format
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()
        except APITimeoutError:
            if attempt == _MAX_RETRIES - 1:
                raise
            wait = _RETRY_BACKOFF ** attempt
            logger.warning("OpenAI timeout (attempt %d/%d), retrying in %ds", attempt + 1, _MAX_RETRIES, wait)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def _parse_json_array(raw: str, candidates: list[dict], default_score: float = 5.0) -> list[dict]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM JSON response: %s", raw[:500])
        return [{"id": c["id"], "score": default_score} for c in candidates]


import re as _re

_CONTENT_TYPE_PATTERNS = [
    ("tutorial", _re.compile(r"(?i)\b(how to|tutorial|learn|beginner|step.by.step|course|guide)\b")),
    ("reaction", _re.compile(r"(?i)\b(react(s|ing|ion)?( to)?|my thoughts on|hot take|response to)\b")),
    ("podcast_clip", _re.compile(r"(?i)\b(podcast|episode|ep\.\s*\d|clip from)\b")),
    ("interview", _re.compile(r"(?i)\b(interview|conversation with|fireside|talks? with|Q&A)\b")),
    ("demo", _re.compile(r"(?i)\b(demo|hands.on|walkthrough|first look|trying|testing)\b")),
    ("news_roundup", _re.compile(r"(?i)\b(this week|weekly|roundup|recap|news.*(update|digest|wrap))\b")),
    ("deep_analysis", _re.compile(r"(?i)\b(paper|explained|deep.dive|analysis|technical|architecture|breakdown)\b")),
]


def _regex_classify(title: str, description: str | None) -> str:
    text = f"{title} {description or ''}"
    for content_type, pattern in _CONTENT_TYPE_PATTERNS:
        if pattern.search(text):
            return content_type
    return "other"


def classify_video_content(candidates: list[dict]) -> list[dict]:
    """Classify videos into content types. Returns [{id, content_type}]."""
    if not candidates:
        return []
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — using regex classification fallback")
        return [
            {"id": c["id"], "content_type": _regex_classify(c["title"], c.get("description"))}
            for c in candidates
        ]
    payload = json.dumps([
        {
            "id": c["id"],
            "title": c["title"],
            "channel": c["channel"],
            "description": (c.get("description") or "")[:200],
            "transcript_excerpt": (c.get("transcript_excerpt") or "")[:300],
        }
        for c in candidates
    ])
    raw = _call_openai(_CLASSIFY_VIDEO_PROMPT, payload)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        logger.error("Classification JSON parse failed: %s", raw[:500])
    return [
        {"id": c["id"], "content_type": _regex_classify(c["title"], c.get("description"))}
        for c in candidates
    ]


# ---------------------------------------------------------------------------
# Stage 1 public API — cheap title-only scoring
# ---------------------------------------------------------------------------

def quick_rank_stories(candidates: list[dict]) -> list[dict]:
    """Title-only scoring for daily collect. Returns [{id, score}]."""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — using tavily_score as fallback")
        return [{"id": c["id"], "score": (c.get("tavily_score") or 0) * 10} for c in candidates]
    if not candidates:
        return []
    payload = json.dumps([{"id": c["id"], "title": c["title"], "source": c["source"]} for c in candidates])
    raw = _call_openai(_QUICK_STORY_PROMPT, payload)
    return _parse_json_array(raw, candidates)


def quick_rank_videos(candidates: list[dict]) -> list[dict]:
    """Multi-signal scoring for daily collect. Returns [{id, score}]."""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — returning zero scores")
        return [{"id": c["id"], "score": 0} for c in candidates]
    if not candidates:
        return []
    payload = json.dumps([
        {
            "id": c["id"],
            "title": c["title"],
            "channel": c["channel"],
            "description": (c.get("description") or "")[:200],
            "views": c.get("view_count", 0),
            "duration_minutes": round((c.get("duration_seconds") or 0) / 60, 1),
            "views_per_hour": round(c.get("view_velocity") or 0, 1),
            "engagement_pct": round((c.get("engagement_rate") or 0) * 100, 2),
            "channel_tier": c.get("channel_tier", "unknown"),
            "content_type": c.get("content_type", "unknown"),
        }
        for c in candidates
    ])
    raw = _call_openai(_QUICK_VIDEO_PROMPT, payload)
    return _parse_json_array(raw, candidates)


# ---------------------------------------------------------------------------
# Stage 2 public API — comparative finals
# ---------------------------------------------------------------------------

def comparative_select_stories(candidates: list[dict]) -> list[dict]:
    """Comparative ranking with full summaries. Returns [{id, rank, topic}]."""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — picking by importance_score")
        by_score = sorted(candidates, key=lambda c: c.get("importance_score", 0), reverse=True)
        return [{"id": c["id"], "rank": i + 1, "topic": "unknown"} for i, c in enumerate(by_score[:5])]
    if not candidates:
        return []
    payload = json.dumps([
        {"id": c["id"], "title": c["title"], "summary": c["summary"][:1500], "source": c["source"]}
        for c in candidates
    ])
    raw = _call_openai(_COMPARATIVE_STORY_PROMPT, payload)
    return _parse_json_array(raw, candidates[:5])


def comparative_select_videos(candidates: list[dict]) -> list[dict]:
    """Comparative ranking for videos. Returns [{id, rank, topic}]."""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — picking by importance_score")
        by_score = sorted(candidates, key=lambda c: c.get("importance_score", 0), reverse=True)
        return [{"id": c["id"], "rank": i + 1, "topic": "unknown"} for i, c in enumerate(by_score[:3])]
    if not candidates:
        return []
    payload = json.dumps([
        {
            "id": c["id"],
            "title": c["title"],
            "channel": c["channel"],
            "description": (c.get("description") or "")[:300],
            "content_type": c.get("content_type", "other"),
            "views_per_hour": round(c.get("view_velocity") or 0, 1),
            "engagement_pct": round((c.get("engagement_rate") or 0) * 100, 2),
            "duration_minutes": round((c.get("duration_seconds") or 0) / 60, 1),
            "channel_tier": c.get("channel_tier", "unknown"),
            "transcript_excerpt": (c.get("transcript_excerpt") or "")[:500],
        }
        for c in candidates
    ])
    raw = _call_openai(_COMPARATIVE_VIDEO_PROMPT, payload)
    return _parse_json_array(raw, candidates[:3])


# ---------------------------------------------------------------------------
# Kept from original (used during publish for final 5 stories)
# ---------------------------------------------------------------------------

def tight_bullets(title: str, raw_content: str) -> list[str]:
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
    if not OPENAI_API_KEY:
        return "Today in AI"
    summaries = "\n".join(f"- {s['title']}" for s in top_stories)
    return _call_openai(_TITLE_SYSTEM_PROMPT, summaries)
