"""GitHub ingestion: trending (Search API) + releases (curated repo list).

Two passes per run:
  1. Trending: for each configured language, GET /search/repositories with a
     recent-push + high-star filter. These feed `dev_posts` as
     "activity"-shaped rows (no version/release_notes).
  2. Releases: for each curated repo, GET /releases?per_page=3. Kept if the
     release is within the last RELEASE_LOOKBACK_DAYS.

Every run also writes a RepoStarSnapshot for each touched repo so the pipeline
can compute stars_velocity_7d from prior snapshots.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import yaml
from sqlalchemy.orm import Session

try:  # pragma: no cover — real fetch path
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

from ..models import DevPost, RepoStarSnapshot

logger = logging.getLogger(__name__)

_GITHUB_BASE = "https://api.github.com"
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH = _BACKEND_ROOT / "devs_config.yaml"

RELEASE_LOOKBACK_DAYS = 14
TRENDING_PUSHED_LOOKBACK_DAYS = 7
TRENDING_STARS_FLOOR = 50
TRENDING_PER_LANGUAGE = 10
TOPIC_SEARCH_CAP = 50
TOPIC_PUSHED_LOOKBACK_DAYS = 30


def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


def _headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_iso(dt: str | None) -> datetime | None:
    if not dt:
        return None
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except ValueError:
        return None


def _get_json(client, url: str, *, headers: dict, params: dict | None = None):
    resp = client.get(url, headers=headers, params=params, timeout=15.0)
    resp.raise_for_status()
    return resp.json()


def fetch_trending(
    languages: Iterable[str],
    *,
    token: str | None = None,
    client=None,
    today: datetime | None = None,
) -> list[dict]:
    """Search API trending-repo pull. Returns normalized candidate dicts."""
    if client is None:
        if httpx is None:
            logger.warning("httpx not installed — cannot fetch GitHub trending")
            return []
        client = httpx.Client(timeout=15.0)
        own_client = True
    else:
        own_client = False

    now = today or datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=TRENDING_PUSHED_LOOKBACK_DAYS)).date().isoformat()
    results: list[dict] = []
    headers = _headers(token)

    try:
        for lang in languages:
            q = f"pushed:>{cutoff} stars:>{TRENDING_STARS_FLOOR} language:{lang}"
            try:
                payload = _get_json(
                    client,
                    f"{_GITHUB_BASE}/search/repositories",
                    headers=headers,
                    params={"q": q, "sort": "stars", "order": "desc", "per_page": TRENDING_PER_LANGUAGE},
                )
            except Exception:
                logger.exception("GitHub trending search failed for language=%s", lang)
                continue

            for item in (payload or {}).get("items") or []:
                full_name = item.get("full_name")
                html_url = item.get("html_url")
                if not full_name or not html_url:
                    continue
                results.append(
                    {
                        "kind": "trending",
                        "repo": full_name,
                        "url": html_url,
                        "title": item.get("description") or full_name,
                        "stars": int(item.get("stargazers_count") or 0),
                        "published_at": _parse_iso(item.get("pushed_at")) or now,
                        "language": lang,
                        "topics": list(item.get("topics") or []),
                    }
                )
        return results
    finally:
        if own_client:
            try:
                client.close()
            except Exception:  # pragma: no cover
                pass


def fetch_topic_candidates(
    topics: Iterable[str],
    *,
    stars_floor: int = TRENDING_STARS_FLOOR,
    forks_floor: int = 0,
    cap: int = TOPIC_SEARCH_CAP,
    lang_allowlist: Iterable[str] | None = None,
    topic_blocklist: Iterable[str] | None = None,
    token: str | None = None,
    client=None,
    today: datetime | None = None,
) -> list[dict]:
    """Topic-driven repo search. Returns up to `cap` normalized candidate dicts.

    Deduplicates across topics (first-seen wins) then sorts by stars descending
    as a cold-start proxy until velocity baselines accumulate.
    """
    if client is None:
        if httpx is None:
            logger.warning("httpx not installed — cannot fetch GitHub topic candidates")
            return []
        client = httpx.Client(timeout=15.0)
        own_client = True
    else:
        own_client = False

    now = today or datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=TOPIC_PUSHED_LOOKBACK_DAYS)).date().isoformat()
    headers = _headers(token)
    seen: dict[str, dict] = {}
    lang_allow = {l.lower() for l in (lang_allowlist or [])}
    blocked_topics = {t.lower() for t in (topic_blocklist or [])}

    try:
        for topic in topics:
            q = f"topic:{topic} stars:>{stars_floor} pushed:>{cutoff}"
            if forks_floor:
                q += f" forks:>{forks_floor}"
            try:
                payload = _get_json(
                    client,
                    f"{_GITHUB_BASE}/search/repositories",
                    headers=headers,
                    params={"q": q, "sort": "stars", "order": "desc", "per_page": 30},
                )
            except Exception:
                logger.exception("GitHub topic search failed for topic=%s", topic)
                continue

            for item in (payload or {}).get("items") or []:
                full_name = item.get("full_name")
                html_url = item.get("html_url")
                if not full_name or not html_url or full_name in seen:
                    continue
                if lang_allow and (item.get("language") or "").lower() not in lang_allow:
                    continue
                repo_topics = [t.lower() for t in (item.get("topics") or [])]
                if blocked_topics and any(t in blocked_topics for t in repo_topics):
                    continue
                seen[full_name] = {
                    "kind": "trending",
                    "repo": full_name,
                    "url": html_url,
                    "title": item.get("description") or full_name,
                    "stars": int(item.get("stargazers_count") or 0),
                    "forks": int(item.get("forks_count") or 0),
                    "published_at": _parse_iso(item.get("pushed_at")) or now,
                    "topics": repo_topics,
                }

        sorted_candidates = sorted(seen.values(), key=lambda x: x["stars"], reverse=True)
        return sorted_candidates[:cap]
    finally:
        if own_client:
            try:
                client.close()
            except Exception:  # pragma: no cover
                pass


def fetch_releases(
    repos: Iterable[str],
    *,
    token: str | None = None,
    client=None,
    today: datetime | None = None,
) -> list[dict]:
    """For each repo, pull up to 3 recent releases within the lookback."""
    if client is None:
        if httpx is None:
            logger.warning("httpx not installed — cannot fetch GitHub releases")
            return []
        client = httpx.Client(timeout=15.0)
        own_client = True
    else:
        own_client = False

    now = today or datetime.now(timezone.utc)
    cutoff_dt = now - timedelta(days=RELEASE_LOOKBACK_DAYS)
    headers = _headers(token)
    results: list[dict] = []

    try:
        for repo in repos:
            # Releases list + repo stars in parallel would be nicer; keep simple
            # and sequential for now — 15 repos × 2 calls is tiny.
            try:
                releases = _get_json(
                    client,
                    f"{_GITHUB_BASE}/repos/{repo}/releases",
                    headers=headers,
                    params={"per_page": 3},
                )
            except Exception:
                logger.warning("GitHub releases fetch failed for %s", repo)
                continue

            try:
                repo_meta = _get_json(
                    client,
                    f"{_GITHUB_BASE}/repos/{repo}",
                    headers=headers,
                )
            except Exception:
                repo_meta = {}

            stars = int((repo_meta or {}).get("stargazers_count") or 0)
            topics = list((repo_meta or {}).get("topics") or [])

            for rel in releases or []:
                if rel.get("draft") or rel.get("prerelease"):
                    continue
                published = _parse_iso(rel.get("published_at") or rel.get("created_at"))
                if published is None or published < cutoff_dt:
                    continue
                html_url = rel.get("html_url")
                if not html_url:
                    continue
                tag = rel.get("tag_name") or rel.get("name") or ""
                title = rel.get("name") or f"{repo} {tag}".strip()
                notes = (rel.get("body") or "").strip()
                results.append(
                    {
                        "kind": "release",
                        "repo": repo,
                        "url": html_url,
                        "title": title,
                        "version": tag or None,
                        "release_notes": notes,
                        "stars": stars,
                        "published_at": published,
                        "topics": topics,
                    }
                )
        return results
    finally:
        if own_client:
            try:
                client.close()
            except Exception:  # pragma: no cover
                pass


def write_star_snapshots(
    db: Session,
    repo_stars: dict[str, int],
    *,
    observed_at: datetime | None = None,
) -> int:
    """Write one RepoStarSnapshot row per repo for velocity tracking."""
    if not repo_stars:
        return 0
    ts = observed_at or datetime.now(timezone.utc)
    for repo, stars in repo_stars.items():
        db.add(RepoStarSnapshot(repo=repo, stars=int(stars or 0), observed_at=ts))
    db.commit()
    return len(repo_stars)


def ingest_github(
    db: Session,
    *,
    token: str | None = None,
    client=None,
    today: datetime | None = None,
) -> int:
    """Run trending + releases pass, write snapshots, insert new dev_posts rows.

    Returns count of new rows. Dedups by `url`.
    """
    cfg = _load_config()
    topics = cfg.get("github_topics") or []
    cap = int(cfg.get("topic_search_cap") or TOPIC_SEARCH_CAP)
    curated = cfg.get("github_curated_repos") or []

    lang_allowlist = cfg.get("github_topic_language_allowlist") or cfg.get("github_languages") or []
    topic_blocklist = cfg.get("github_topic_blocklist") or []
    forks_floor = int(cfg.get("github_topic_min_forks") or 0)
    topic_candidates = fetch_topic_candidates(
        topics, cap=cap,
        stars_floor=TRENDING_STARS_FLOOR,
        forks_floor=forks_floor,
        lang_allowlist=lang_allowlist,
        topic_blocklist=topic_blocklist,
        token=token, client=client, today=today,
    )

    # Releases: topic pool repos + curated floor (order-preserving dedup)
    release_repos = list(dict.fromkeys([c["repo"] for c in topic_candidates] + curated))
    releases = fetch_releases(release_repos, token=token, client=client, today=today)
    candidates = topic_candidates + releases

    if not candidates:
        return 0

    # Snapshot every repo we touched, regardless of whether we insert a row.
    repo_stars: dict[str, int] = {}
    for c in candidates:
        repo = c.get("repo")
        if repo and repo not in repo_stars:
            repo_stars[repo] = int(c.get("stars") or 0)
    write_star_snapshots(db, repo_stars, observed_at=today)

    urls = [c["url"] for c in candidates]
    existing = {
        row.url
        for row in db.query(DevPost.url)
        .filter(DevPost.source == "github", DevPost.url.in_(urls))
        .all()
    }

    added = 0
    for c in candidates:
        if c["url"] in existing:
            continue

        row = DevPost(
            source="github",
            url=c["url"],
            title=c["title"],
            published_at=c["published_at"],
            repo=c["repo"],
            stars=c.get("stars"),
            topics=c.get("topics") or None,
            is_active=False,
        )
        if c["kind"] == "release":
            row.version = c.get("version")
            row.release_notes_excerpt = (c.get("release_notes") or "")[:2000] or None
        db.add(row)
        added += 1

    db.commit()
    logger.info("GitHub ingest complete — %d new candidates", added)
    return added


def compute_stars_velocity_7d(
    db: Session,
    repo: str,
    *,
    now: datetime | None = None,
) -> int | None:
    """Δ stars in the last 7 days, using the earliest snapshot in that window.

    Returns None if we don't have at least one snapshot from ≥7 days ago
    (can't compute velocity without a baseline).
    """
    now = now or datetime.now(timezone.utc)
    window_start = now - timedelta(days=7)

    latest = (
        db.query(RepoStarSnapshot)
        .filter(RepoStarSnapshot.repo == repo)
        .order_by(RepoStarSnapshot.observed_at.desc())
        .first()
    )
    if not latest:
        return None

    baseline = (
        db.query(RepoStarSnapshot)
        .filter(RepoStarSnapshot.repo == repo)
        .filter(RepoStarSnapshot.observed_at <= window_start)
        .order_by(RepoStarSnapshot.observed_at.desc())
        .first()
    )
    if not baseline:
        return None

    delta = int((latest.stars or 0) - (baseline.stars or 0))
    return max(delta, 0)
