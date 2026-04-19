"""LLM rankers + generators for the `/api/devs/posts` feed.

All framing is agentic-coding-centric (see source plan "Framing tilt"). Every
function has a heuristic / None fallback so pipelines never block on LLM
availability.

Reuses `_call_openai` + `_parse_json_array` from the existing `ranker.py`.
"""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

from ..config import OPENAI_API_KEY
from .ranker import _call_openai, _parse_json_array

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o-mini"

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_AGENTIC_FRAMING = """\
You are an editor for "The Context Window" /devs feed — a skill-development
feed for engineers getting better at AGENTIC CODING. The center of gravity is:
coding agents (Claude Code, Cursor, Aider, Cline, Continue), MCP servers/tools,
agent frameworks (LangGraph, OpenAI Agents SDK, Anthropic SDK, AutoGen, Semantic
Kernel), sub-agent orchestration, tool-use patterns, agent evals, IDE integrations,
context management (windows, compaction, worktree isolation, prompt caching),
parallel workflows (fleets, supervisor/swarm orchestration, handoff contracts),
model routing (Opus/Sonnet/Haiku), spec-driven development, bounded autonomy,
long-running + checkpointing, hybrid tool stacks, Anthropic's 5 agent patterns,
AI-driven security. Tier-2 (welcome, secondary): broader AI engineering — RAG,
prompting, evals, inference infra. Penalize pure business/funding/hype with no
technical substance.
"""

_RANK_HN_PROMPT = _AGENTIC_FRAMING + """\

You will receive an HN post (title, points, comments).
Score 1-10 on engineering-skill relevance to agentic coding. Return ONLY a JSON
object: {"score": <float 1-10>, "topics": ["<2-3 topic tags>"]}
No markdown fences, no extra text."""

_RANK_GITHUB_PROMPT = _AGENTIC_FRAMING + """\

You will receive a GitHub repo or release (repo name, title, release notes
excerpt if present).
Score 1-10 on how much an engineer upgrading their agentic-coding skills would
care. Return ONLY a JSON object:
{"score": <float 1-10>, "topics": ["<2-3 topic tags>"]}
No markdown fences, no extra text."""

_RANK_X_TWEET_PROMPT = _AGENTIC_FRAMING + """\

You will receive a JSON array of tweets. Each has id, author, text, likes,
reposts, replies.
Score each 1-10 on SUBSTANCE for engineers improving at agentic coding.
Penalize pure self-promotion, hot takes with no insight, and off-topic content.
Return ONLY a JSON array: [{"id": <int>, "quality_score": <float 1-10>, "topics": ["<tag>"]}]
No markdown fences, no extra text."""

_SUMMARIZE_HN_THREAD_PROMPT = _AGENTIC_FRAMING + """\

You will receive an HN post title + a list of top comments.
Extract 2-4 discussion bullets that capture the most useful, concrete insights
an engineer would want to take away — disagreements, gotchas, tools mentioned,
war stories. Each bullet 12-22 words. No "commenters say" / "someone noted".
Lead with the specific fact or claim.
Return ONLY a JSON array of strings. No markdown fences, no extra text."""

_EXTRACT_GH_INSIGHTS_PROMPT = _AGENTIC_FRAMING + """\

You will receive a GitHub repo name + release notes text.
Produce:
- release_bullets: 2-4 bullets on what actually changed (features, perf, API
  changes). 12-22 words each, concrete.
- why_it_matters: one 15-30 word sentence on practical impact for an engineer
  doing agentic coding.
- has_breaking_changes: true if notes mention breaking changes, removed APIs,
  migration required, or incompatibilities; else false.
Return ONLY a JSON object:
{"release_bullets": [...], "why_it_matters": "...", "has_breaking_changes": <bool>}
No markdown fences, no extra text."""

_CLUSTER_TWEETS_PROMPT = _AGENTIC_FRAMING + """\

You will receive a JSON array of tweets (id, author, text).
Group them into 3-5 AGENTIC-CODING topic clusters. Each cluster gets a short
label (2-4 words, e.g. "MCP patterns", "Agent evals", "Context management",
"Coding agent UX"). Every tweet id must appear in exactly one cluster; if a
tweet is off-topic, put it under label "other".
Return ONLY a JSON object: {"<label>": [<tweet_id>, ...], ...}
No markdown fences, no extra text."""

_SYNTHESIZE_DIGEST_PROMPT = _AGENTIC_FRAMING + """\

You will receive a topic label + a JSON array of tweets (id, author, url, text).
Write 2-4 topic-digest bullets synthesizing what engineers are saying.
Each bullet must:
- Be 15-30 words, concrete, lead with the claim/insight (no "people are saying")
- Cite ≥1 tweet via its url in the "sources" array
- Include author_handle (without @) and author_name (when available) for every source

Return ONLY a JSON array, no markdown fences, no extra text:
[{"text": "<bullet>", "sources": [{"url": "...", "author_handle": "...", "author_name": "..."}, ...]}]"""


# ---------------------------------------------------------------------------
# Heuristic fallbacks
# ---------------------------------------------------------------------------


def _hn_heuristic_score(points: int | None, comments: int | None) -> float:
    p = max(int(points or 0), 0)
    c = max(int(comments or 0), 0)
    return round(math.log1p(p) + 0.8 * math.log1p(c), 3)


def _github_heuristic_score(stars: int | None) -> float:
    s = max(int(stars or 0), 0)
    return round(math.log1p(s), 3)


def _x_heuristic_quality(likes: int | None, reposts: int | None, replies: int | None) -> float:
    # Cap at 10. Reposts/replies are stronger signal than raw likes for substance.
    l = max(int(likes or 0), 0)
    r = max(int(reposts or 0), 0)
    rp = max(int(replies or 0), 0)
    score = math.log1p(l) * 0.5 + math.log1p(r) * 1.2 + math.log1p(rp) * 1.0
    return round(min(score, 10.0), 3)


_BREAKING_PATTERN = re.compile(
    r"(?i)\b(breaking[- ]changes?|backward[- ]incompat|backwards[- ]incompat"
    r"|removed?|migration[- ]required|deprecat(e|ed|ion))\b"
)


def _heuristic_github_insights(repo: str, notes: str) -> dict:
    text = (notes or "").strip()
    if not text:
        return {
            "release_bullets": [f"See release notes for {repo}."],
            "why_it_matters": "",
            "has_breaking_changes": False,
        }
    # Naive bullet extraction: split on newlines, keep lines starting with "-" or "*".
    bullets: list[str] = []
    for line in text.splitlines():
        stripped = line.strip().lstrip("-*•").strip()
        if 8 <= len(stripped) <= 180:
            bullets.append(stripped[:160])
        if len(bullets) >= 4:
            break
    if not bullets:
        bullets = [text[:160].strip()]
    return {
        "release_bullets": bullets[:4],
        "why_it_matters": "",
        "has_breaking_changes": bool(_BREAKING_PATTERN.search(text)),
    }


# ---------------------------------------------------------------------------
# Public ranker API
# ---------------------------------------------------------------------------


def rank_hn_post(post: dict) -> dict:
    """Rank an HN post for agentic-coding relevance. `{score, topics}`."""
    if not OPENAI_API_KEY:
        return {
            "score": _hn_heuristic_score(post.get("points"), post.get("comments")),
            "topics": [],
        }
    payload = json.dumps(
        {
            "title": post.get("title"),
            "points": post.get("points"),
            "comments": post.get("comments"),
        }
    )
    try:
        raw = _call_openai(_RANK_HN_PROMPT, payload, model=_MODEL)
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {
                "score": float(parsed.get("score", 5.0)),
                "topics": list(parsed.get("topics") or []),
            }
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("rank_hn_post: LLM JSON parse failed, using heuristic")
    except Exception:
        logger.exception("rank_hn_post: LLM call failed, using heuristic")
    return {
        "score": _hn_heuristic_score(post.get("points"), post.get("comments")),
        "topics": [],
    }


def rank_github_post(post: dict) -> dict:
    """Rank a GitHub candidate. `{score, topics}`."""
    if not OPENAI_API_KEY:
        return {"score": _github_heuristic_score(post.get("stars")), "topics": []}
    payload = json.dumps(
        {
            "repo": post.get("repo"),
            "title": post.get("title"),
            "release_notes_excerpt": (post.get("release_notes_excerpt") or "")[:1500],
            "stars": post.get("stars"),
        }
    )
    try:
        raw = _call_openai(_RANK_GITHUB_PROMPT, payload, model=_MODEL)
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {
                "score": float(parsed.get("score", 5.0)),
                "topics": list(parsed.get("topics") or []),
            }
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("rank_github_post: LLM JSON parse failed, using heuristic")
    except Exception:
        logger.exception("rank_github_post: LLM call failed, using heuristic")
    return {"score": _github_heuristic_score(post.get("stars")), "topics": []}


def rank_x_tweet(tweet: dict | list[dict]) -> dict | list[dict]:
    """Score a tweet (or batch of tweets) for agentic-coding substance.

    Accepts either a single tweet dict (returns `{quality_score, topics}`) or
    a list of tweet dicts (returns `[{id, quality_score, topics}]`). The
    batched form is what the pipeline uses; the single form keeps the signature
    in the contract literal.
    """
    if isinstance(tweet, list):
        return _rank_x_tweet_batch(tweet)
    return _rank_x_tweet_single(tweet)


def _rank_x_tweet_single(tweet: dict) -> dict:
    if not OPENAI_API_KEY:
        return {
            "quality_score": _x_heuristic_quality(
                tweet.get("likes"), tweet.get("reposts"), tweet.get("replies")
            ),
            "topics": [],
        }
    # Route through the batch path so there's one prompt to maintain.
    res = _rank_x_tweet_batch([{**tweet, "id": tweet.get("id", 0)}])
    if res:
        return {"quality_score": res[0].get("quality_score", 5.0), "topics": res[0].get("topics") or []}
    return {
        "quality_score": _x_heuristic_quality(
            tweet.get("likes"), tweet.get("reposts"), tweet.get("replies")
        ),
        "topics": [],
    }


def _rank_x_tweet_batch(tweets: list[dict]) -> list[dict]:
    if not tweets:
        return []
    if not OPENAI_API_KEY:
        return [
            {
                "id": t.get("id"),
                "quality_score": _x_heuristic_quality(
                    t.get("likes"), t.get("reposts"), t.get("replies")
                ),
                "topics": [],
            }
            for t in tweets
        ]
    payload = json.dumps(
        [
            {
                "id": t.get("id"),
                "author": t.get("author_handle"),
                "text": (t.get("text") or "")[:500],
                "likes": t.get("likes"),
                "reposts": t.get("reposts"),
                "replies": t.get("replies"),
            }
            for t in tweets
        ]
    )
    try:
        raw = _call_openai(_RANK_X_TWEET_PROMPT, payload, model=_MODEL)
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            out: list[dict] = []
            by_id = {int(p.get("id")): p for p in parsed if p.get("id") is not None}
            for t in tweets:
                p = by_id.get(int(t.get("id")))
                if p is None:
                    out.append(
                        {
                            "id": t.get("id"),
                            "quality_score": _x_heuristic_quality(
                                t.get("likes"), t.get("reposts"), t.get("replies")
                            ),
                            "topics": [],
                        }
                    )
                else:
                    out.append(
                        {
                            "id": t.get("id"),
                            "quality_score": float(p.get("quality_score", 5.0)),
                            "topics": list(p.get("topics") or []),
                        }
                    )
            return out
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("rank_x_tweet: LLM JSON parse failed, using heuristic")
    except Exception:
        logger.exception("rank_x_tweet: LLM call failed, using heuristic")
    return [
        {
            "id": t.get("id"),
            "quality_score": _x_heuristic_quality(
                t.get("likes"), t.get("reposts"), t.get("replies")
            ),
            "topics": [],
        }
        for t in tweets
    ]


def summarize_hn_thread(title: str, comments: list[str]) -> list[str]:
    """Generate 2-4 discussion bullets. Empty list if no comments + no LLM."""
    if not comments:
        return []
    if not OPENAI_API_KEY:
        # Heuristic: take the first sentence of the first few comments.
        out: list[str] = []
        for c in comments[:4]:
            text = (c or "").strip()
            if not text:
                continue
            first = re.split(r"[.!?\n]", text, maxsplit=1)[0].strip()
            if 8 <= len(first) <= 200:
                out.append(first[:200])
            if len(out) >= 4:
                break
        return out[:4]
    payload = json.dumps(
        {
            "title": title,
            "comments": [(c or "")[:800] for c in comments[:20]],
        }
    )
    try:
        raw = _call_openai(_SUMMARIZE_HN_THREAD_PROMPT, payload, model=_MODEL)
        parsed = json.loads(raw)
        if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
            out = [x.strip() for x in parsed if x and x.strip()]
            return out[:4] if out else []
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("summarize_hn_thread: LLM JSON parse failed, returning []")
    except Exception:
        logger.exception("summarize_hn_thread: LLM call failed, returning []")
    return []


def extract_github_insights(repo: str, notes: str) -> dict:
    """Derive release_bullets / why_it_matters / has_breaking_changes."""
    if not OPENAI_API_KEY:
        return _heuristic_github_insights(repo, notes)
    payload = json.dumps({"repo": repo, "release_notes": (notes or "")[:3000]})
    try:
        raw = _call_openai(_EXTRACT_GH_INSIGHTS_PROMPT, payload, model=_MODEL)
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            bullets = parsed.get("release_bullets") or []
            if not isinstance(bullets, list):
                bullets = []
            return {
                "release_bullets": [str(b).strip() for b in bullets if str(b).strip()][:4],
                "why_it_matters": str(parsed.get("why_it_matters") or "").strip(),
                "has_breaking_changes": bool(parsed.get("has_breaking_changes")),
            }
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("extract_github_insights: LLM JSON parse failed, using heuristic")
    except Exception:
        logger.exception("extract_github_insights: LLM call failed, using heuristic")
    return _heuristic_github_insights(repo, notes)


def cluster_tweets_into_topics(tweets: list[dict]) -> dict[str, list[int]]:
    """Cluster tweets into 3-5 topic buckets. Fallback = single "general" bucket."""
    if not tweets:
        return {}
    all_ids = [int(t["id"]) for t in tweets if t.get("id") is not None]
    if not OPENAI_API_KEY:
        return {"general": all_ids}
    payload = json.dumps(
        [
            {
                "id": int(t["id"]),
                "author": t.get("author_handle"),
                "text": (t.get("text") or "")[:400],
            }
            for t in tweets
            if t.get("id") is not None
        ]
    )
    try:
        raw = _call_openai(_CLUSTER_TWEETS_PROMPT, payload, model=_MODEL)
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            clusters: dict[str, list[int]] = {}
            for label, ids in parsed.items():
                if not isinstance(ids, list):
                    continue
                clean = [int(i) for i in ids if isinstance(i, (int, float))]
                if clean:
                    clusters[str(label)] = clean
            if clusters:
                return clusters
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("cluster_tweets_into_topics: LLM JSON parse failed, using fallback")
    except Exception:
        logger.exception("cluster_tweets_into_topics: LLM call failed, using fallback")
    return {"general": all_ids}


def synthesize_topic_digest(topic: str, tweets: list[dict]) -> list[dict]:
    """Return [{text, sources: [{url, author_handle, author_name}]}, ...].

    Fallback synthesizes one bullet per top tweet.
    """
    if not tweets:
        return []

    def _fallback() -> list[dict]:
        out: list[dict] = []
        for t in tweets[:3]:
            text = (t.get("text") or "").strip()
            if not text:
                continue
            first = re.split(r"[.!?\n]", text, maxsplit=1)[0].strip()
            if len(first) < 8:
                first = text[:160]
            out.append(
                {
                    "text": first[:220],
                    "sources": [
                        {
                            "url": t.get("url", ""),
                            "author_handle": t.get("author_handle", ""),
                            "author_name": t.get("author_name"),
                        }
                    ],
                }
            )
        return out

    if not OPENAI_API_KEY:
        return _fallback()

    payload = json.dumps(
        {
            "topic": topic,
            "tweets": [
                {
                    "id": t.get("id"),
                    "author": t.get("author_handle"),
                    "author_name": t.get("author_name"),
                    "url": t.get("url"),
                    "text": (t.get("text") or "")[:500],
                }
                for t in tweets
            ],
        }
    )
    try:
        raw = _call_openai(_SYNTHESIZE_DIGEST_PROMPT, payload, model=_MODEL)
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            out: list[dict] = []
            for b in parsed:
                if not isinstance(b, dict):
                    continue
                text = str(b.get("text") or "").strip()
                if not text:
                    continue
                sources = b.get("sources") or []
                clean_sources: list[dict] = []
                for s in sources:
                    if not isinstance(s, dict):
                        continue
                    url = str(s.get("url") or "").strip()
                    handle = str(s.get("author_handle") or "").strip().lstrip("@")
                    if not url or not handle:
                        continue
                    clean_sources.append(
                        {
                            "url": url,
                            "author_handle": handle,
                            "author_name": s.get("author_name"),
                        }
                    )
                if not clean_sources:
                    # Bullet with no sources violates the shape — drop it.
                    continue
                out.append({"text": text, "sources": clean_sources})
            return out[:4] if out else _fallback()
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("synthesize_topic_digest: LLM JSON parse failed, using fallback")
    except Exception:
        logger.exception("synthesize_topic_digest: LLM call failed, using fallback")
    return _fallback()


# Re-export so callers can reuse them via this module too.
__all__ = [
    "rank_hn_post",
    "rank_github_post",
    "rank_x_tweet",
    "summarize_hn_thread",
    "extract_github_insights",
    "cluster_tweets_into_topics",
    "synthesize_topic_digest",
    "_call_openai",
    "_parse_json_array",
]
