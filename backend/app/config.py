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

NEWS_RESULTS_PER_QUERY: int = _cfg.get("settings", {}).get("news_results_per_query", 10)
VIDEO_RESULTS_PER_QUERY: int = _cfg.get("settings", {}).get("video_results_per_query", 5)

COLLECT_HOUR: int = int(os.getenv("COLLECT_HOUR", "6"))
PUBLISH_DAY: str = os.getenv("PUBLISH_DAY", "monday")
PUBLISH_HOUR: int = int(os.getenv("PUBLISH_HOUR", "8"))
