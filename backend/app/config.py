import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")
_env_specific = os.getenv("DOTENV_FILE", ".env.dev")
load_dotenv(_BACKEND_ROOT / _env_specific, override=True)

_CONFIG_PATH = _BACKEND_ROOT / "search_config.yaml"


def _load_search_config() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


_cfg = _load_search_config()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

NEWS_QUERIES: list[str] = _cfg.get("news_queries", ["artificial intelligence news"])
VIDEO_QUERIES: list[str] = _cfg.get("video_queries", ["AI news this week"])

_settings = _cfg.get("settings") or {}

NEWS_RESULTS_PER_QUERY: int = _settings.get("news_results_per_query", 10)
VIDEO_RESULTS_PER_QUERY: int = _settings.get("video_results_per_query", 8)

MIN_VIDEO_VIEWS: int = _settings.get("min_video_views", 500)
MIN_VIDEO_DURATION_SECS: int = _settings.get("min_video_duration_seconds", 60)
MAX_VIDEO_DURATION_SECS: int = _settings.get("max_video_duration_seconds", 5400)


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
PUBLISH_HOUR: int = int(os.getenv("PUBLISH_HOUR", "8"))
