import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")
_env_specific = os.getenv("DOTENV_FILE", ".env.dev")
load_dotenv(_BACKEND_ROOT / _env_specific, override=True)

_CONFIG_PATH = _BACKEND_ROOT / "search_config.yaml"
_DEVS_CONFIG_PATH = _BACKEND_ROOT / "devs_config.yaml"


def _load_search_config() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


def _load_devs_config() -> dict:
    if _DEVS_CONFIG_PATH.exists():
        with open(_DEVS_CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


_cfg = _load_search_config()
_devs_cfg = _load_devs_config()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

NEWS_QUERIES: list[str] = _cfg.get("news_queries", ["artificial intelligence news"])
VIDEO_QUERIES: list[str] = _cfg.get("video_queries", ["AI news today"])

_settings = _cfg.get("settings") or {}

NEWS_RESULTS_PER_QUERY: int = _settings.get("news_results_per_query", 10)
VIDEO_RESULTS_PER_QUERY: int = _settings.get("video_results_per_query", 8)

MIN_VIDEO_VIEWS: int = _settings.get("min_video_views", 500)
MIN_VIDEO_DURATION_SECS: int = _settings.get("min_video_duration_seconds", 60)
MAX_VIDEO_DURATION_SECS: int = _settings.get("max_video_duration_seconds", 5400)

HEURISTIC_REJECT_BOTTOM_PCT: int = _settings.get("heuristic_reject_bottom_pct", 25)
VIDEO_FINALISTS: int = _settings.get("video_finalists", 10)
VIDEO_PUBLISH_LOOKBACK_DAYS: int = int(
    os.getenv(
        "VIDEO_PUBLISH_LOOKBACK_DAYS",
        str(_settings.get("video_publish_lookback_days", 7)),
    )
)
IDEAL_VIDEO_DURATION_MIN: int = _settings.get("ideal_video_duration_min", 300)
IDEAL_VIDEO_DURATION_MAX: int = _settings.get("ideal_video_duration_max", 1500)


def _max_searches_setting(env_key: str, yaml_key: str) -> int | None:
    raw = os.getenv(env_key)
    if raw is not None and raw.strip() != "":
        return int(raw)
    v = _settings.get(yaml_key)
    if v is None:
        return None
    return int(v)


# Cap Tavily / YouTube search invocations per daily collect (rotation over full query lists).
# None = run every query in YAML each collect. Env overrides YAML (including 0).
MAX_NEWS_SEARCHES_PER_COLLECT: int | None = _max_searches_setting(
    "MAX_NEWS_SEARCHES_PER_COLLECT", "max_news_searches_per_collect"
)
MAX_VIDEO_SEARCHES_PER_COLLECT: int | None = _max_searches_setting(
    "MAX_VIDEO_SEARCHES_PER_COLLECT", "max_video_searches_per_collect"
)

RETENTION_DAYS: int = int(os.getenv("RETENTION_DAYS", "30"))
COLLECT_HOUR: int = int(os.getenv("COLLECT_HOUR", "6"))
# Publish runs every day at this hour (UTC). Set after COLLECT_HOUR so candidates are scored first.
PUBLISH_HOUR: int = int(os.getenv("PUBLISH_HOUR", "8"))
# Unused (legacy env): weekly publish was keyed by day; publish is now daily.
PUBLISH_DAY: str = os.getenv("PUBLISH_DAY", "monday")

# ---------------------------------------------------------------------------
# /api/devs feed — skill-development feed for agentic coders
# ---------------------------------------------------------------------------

APIFY_TOKEN: str = os.getenv("APIFY_TOKEN", "")
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

_devs_slots = (_devs_cfg.get("slot_allocation") or {}) if _devs_cfg else {}

DEV_FEED_SIZE_HN: int = int(os.getenv("DEV_FEED_SIZE_HN", str(_devs_slots.get("hn", 3))))
DEV_FEED_SIZE_GITHUB: int = int(
    os.getenv("DEV_FEED_SIZE_GITHUB", str(_devs_slots.get("github", 2)))
)
DEV_FEED_SIZE_X_TOPICS: int = int(
    os.getenv("DEV_FEED_SIZE_X_TOPICS", str(_devs_slots.get("x_topics", 3)))
)

MAX_X_HANDLES: int = int(os.getenv("MAX_X_HANDLES", "50"))
APIFY_MONTHLY_TWEET_CAP: int = int(os.getenv("APIFY_MONTHLY_TWEET_CAP", "15000"))

# Full devs config dict exposed for pipeline / ranker consumption.
DEVS_CONFIG: dict = _devs_cfg
