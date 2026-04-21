"""X (Twitter) ingestion via Apify's twitter-scraper actor.

Runs once/day, pulls ~30h of tweets from the curated handle list, writes into
`candidate_x_tweets`. Dedup by tweet URL. Reply + retweet exclusion happens
here, not downstream.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import yaml
from sqlalchemy.orm import Session

try:  # pragma: no cover — tests monkeypatch ApifyClient
    from apify_client import ApifyClient
except ImportError:  # pragma: no cover
    ApifyClient = None  # type: ignore

from ..models import CandidateXTweet

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH = _BACKEND_ROOT / "devs_config.yaml"

# Apify actor id for the twitter-scraper. Configurable via env if we ever swap.
_APIFY_ACTOR_ID = "apidojo/tweet-scraper"
_DEFAULT_LOOKBACK_HOURS = 30
_DEFAULT_MAX_TWEETS_PER_HANDLE = 20


def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


def _flatten_handles(cfg: dict) -> list[str]:
    """Union of all tiered handle lists in devs_config.yaml."""
    tiers = cfg.get("x_handles") or {}
    if not isinstance(tiers, dict):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for bucket in tiers.values():
        for h in bucket or []:
            h_norm = (h or "").strip().lstrip("@")
            if h_norm and h_norm not in seen:
                seen.add(h_norm)
                out.append(h_norm)
    return out


def _parse_tweet_datetime(raw) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
        # twitter-scraper often returns "Wed Apr 16 14:30:00 +0000 2026"
        for fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S.%f%z"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
    return None


def _extract_tweet(item: dict) -> dict | None:
    """Normalize an Apify twitter-scraper item into our candidate dict shape.

    Returns None for replies/retweets/quote-only items.
    """
    if not isinstance(item, dict):
        return None

    if item.get("isReply") or item.get("is_reply") or item.get("inReplyToId"):
        return None
    if item.get("isRetweet") or item.get("retweeted_status") or item.get("isQuote"):
        return None

    url = item.get("url") or item.get("tweetUrl") or item.get("permalink")
    if not url:
        tid = item.get("id") or item.get("id_str") or item.get("conversationId")
        handle = (
            (item.get("author") or {}).get("userName")
            or item.get("user", {}).get("screen_name")
            or item.get("username")
        )
        if tid and handle:
            url = f"https://twitter.com/{handle}/status/{tid}"
    if not url:
        return None

    author = item.get("author") or {}
    handle = (
        author.get("userName")
        or item.get("username")
        or (item.get("user") or {}).get("screen_name")
    )
    if not handle:
        return None
    name = author.get("name") or (item.get("user") or {}).get("name")
    avatar = (
        author.get("profilePicture")
        or (item.get("user") or {}).get("profile_image_url_https")
    )

    text = (item.get("text") or item.get("fullText") or "").strip()
    if not text:
        return None

    published = _parse_tweet_datetime(
        item.get("createdAt") or item.get("created_at") or item.get("timestamp")
    )
    if published is None:
        return None

    likes = int(item.get("likeCount") or item.get("favorite_count") or 0)
    reposts = int(item.get("retweetCount") or item.get("retweet_count") or 0)
    replies = int(item.get("replyCount") or item.get("reply_count") or 0)

    return {
        "url": url,
        "author_handle": str(handle).lstrip("@"),
        "author_name": name,
        "author_avatar_url": avatar,
        "text": text,
        "likes": likes,
        "reposts": reposts,
        "replies": replies,
        "published_at": published,
    }


def fetch_tweets_via_apify(
    handles: Iterable[str],
    *,
    token: str,
    client=None,
    lookback_hours: int = _DEFAULT_LOOKBACK_HOURS,
    max_per_handle: int = _DEFAULT_MAX_TWEETS_PER_HANDLE,
    now: datetime | None = None,
) -> list[dict]:
    """Run the Apify twitter-scraper actor. Returns normalized candidate dicts.

    `client` is injected by tests — in production it's an ApifyClient. Any
    object with the same `.actor(id).call(run_input=...).get("defaultDatasetId")`
    + `.dataset(id).iterate_items()` surface works.
    """
    handles_list = [h.strip().lstrip("@") for h in handles if h and h.strip()]
    if not handles_list:
        return []

    now = now or datetime.now(timezone.utc)
    since = now - timedelta(hours=lookback_hours)

    if client is None:
        if ApifyClient is None:
            logger.warning("apify-client not installed — cannot fetch X tweets")
            return []
        if not token:
            logger.warning("APIFY_TOKEN empty — cannot fetch X tweets")
            return []
        client = ApifyClient(token)

    run_input = {
        "twitterHandles": handles_list,
        "maxItems": max_per_handle * len(handles_list),
        "sort": "Latest",
        "start": since.date().isoformat(),
    }

    try:
        run = client.actor(_APIFY_ACTOR_ID).call(run_input=run_input)
    except Exception:
        logger.exception("Apify actor call failed")
        return []

    dataset_id = (run or {}).get("defaultDatasetId")
    if not dataset_id:
        logger.warning("Apify run returned no dataset id")
        return []

    try:
        items = list(client.dataset(dataset_id).iterate_items())
    except Exception:
        logger.exception("Apify dataset iteration failed")
        return []

    run_status = (run or {}).get("status")
    logger.info("Apify run completed — %d items, status=%s", len(items), run_status)
    if not items and run_status == "SUCCEEDED":
        logger.warning(
            "Apify returned 0 items despite SUCCEEDED — likely paywall or config "
            "issue; check actor log in Apify console"
        )

    normalized: list[dict] = []
    for raw in items:
        rec = _extract_tweet(raw)
        if rec is None:
            continue
        if rec["published_at"] < since:
            continue
        normalized.append(rec)
    return normalized


def ingest_x(
    db: Session,
    *,
    token: str,
    client=None,
    lookback_hours: int = _DEFAULT_LOOKBACK_HOURS,
    max_per_handle: int = _DEFAULT_MAX_TWEETS_PER_HANDLE,
    now: datetime | None = None,
) -> int:
    """Fetch tweets, dedup, insert into `candidate_x_tweets`. Returns new-row count."""
    cfg = _load_config()
    handles = _flatten_handles(cfg)
    if not handles:
        logger.warning("No X handles configured — skipping")
        return 0

    tweets = fetch_tweets_via_apify(
        handles,
        token=token,
        client=client,
        lookback_hours=lookback_hours,
        max_per_handle=max_per_handle,
        now=now,
    )
    if not tweets:
        return 0

    urls = [t["url"] for t in tweets]
    existing = {
        row.url
        for row in db.query(CandidateXTweet.url)
        .filter(CandidateXTweet.url.in_(urls))
        .all()
    }

    added = 0
    for t in tweets:
        if t["url"] in existing:
            continue
        row = CandidateXTweet(
            url=t["url"],
            author_handle=t["author_handle"],
            author_name=t.get("author_name"),
            author_avatar_url=t.get("author_avatar_url"),
            text=t["text"],
            likes=t.get("likes"),
            reposts=t.get("reposts"),
            replies=t.get("replies"),
            published_at=t["published_at"],
        )
        db.add(row)
        added += 1

    db.commit()
    logger.info("X ingest complete — %d new tweets", added)
    return added
