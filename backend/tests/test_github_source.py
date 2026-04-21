"""GitHub source tests — mocks the GitHub HTTP API.

Only the no-DB helpers are exercised here. Ingest + snapshot + velocity tests
need the Slice 1 ORM and are deferred (skip markers).
"""

from datetime import datetime, timedelta, timezone

from app.services import github_source


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class FakeHTTPClient:
    def __init__(self, responses: dict):
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append((url, params or {}))
        data = self.responses.get(url)
        if data is None:
            raise KeyError(f"no mock for {url}")
        if isinstance(data, Exception):
            raise data
        return FakeResponse(data)

    def close(self):
        return None


# ---------------------------------------------------------------------------
# fetch_trending
# ---------------------------------------------------------------------------

def test_fetch_trending_hits_each_language():
    responses = {
        "https://api.github.com/search/repositories": {
            "items": [
                {
                    "full_name": "acme/widget",
                    "html_url": "https://github.com/acme/widget",
                    "description": "A widget",
                    "stargazers_count": 1234,
                    "pushed_at": "2026-04-15T00:00:00Z",
                    "topics": ["rust", "cli"],
                }
            ]
        }
    }
    client = FakeHTTPClient(responses)
    out = github_source.fetch_trending(["Rust", "Go"], client=client)
    assert len(out) == 2  # one per language
    assert out[0]["repo"] == "acme/widget"
    assert out[0]["stars"] == 1234
    assert out[0]["kind"] == "trending"
    assert isinstance(out[0]["published_at"], datetime)
    # Two search calls, one per language.
    search_calls = [c for c in client.calls if c[0].endswith("/search/repositories")]
    assert len(search_calls) == 2


def test_fetch_trending_handles_error_per_language():
    responses = {"https://api.github.com/search/repositories": RuntimeError("rate limit")}
    client = FakeHTTPClient(responses)
    out = github_source.fetch_trending(["Rust"], client=client)
    assert out == []


# ---------------------------------------------------------------------------
# fetch_releases
# ---------------------------------------------------------------------------

def test_fetch_releases_filters_to_lookback_window():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    old = (now - timedelta(days=30)).isoformat().replace("+00:00", "Z")

    responses = {
        "https://api.github.com/repos/acme/widget/releases": [
            {
                "tag_name": "v2.0.0",
                "name": "v2.0.0",
                "html_url": "https://github.com/acme/widget/releases/tag/v2.0.0",
                "body": "# Changelog\n- feature x\n",
                "published_at": recent,
                "draft": False,
                "prerelease": False,
            },
            {
                "tag_name": "v1.0.0",
                "name": "v1.0.0",
                "html_url": "https://github.com/acme/widget/releases/tag/v1.0.0",
                "body": "old",
                "published_at": old,
                "draft": False,
                "prerelease": False,
            },
        ],
        "https://api.github.com/repos/acme/widget": {
            "stargazers_count": 500,
            "topics": ["rust"],
        },
    }
    client = FakeHTTPClient(responses)
    out = github_source.fetch_releases(["acme/widget"], client=client, today=now)
    assert len(out) == 1
    assert out[0]["version"] == "v2.0.0"
    assert out[0]["stars"] == 500
    assert "feature x" in out[0]["release_notes"]


def test_fetch_releases_skips_drafts_and_prereleases():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    responses = {
        "https://api.github.com/repos/a/b/releases": [
            {
                "tag_name": "draft-1",
                "html_url": "https://github.com/a/b/releases/tag/draft-1",
                "published_at": recent,
                "draft": True,
                "prerelease": False,
            },
            {
                "tag_name": "pre-1",
                "html_url": "https://github.com/a/b/releases/tag/pre-1",
                "published_at": recent,
                "draft": False,
                "prerelease": True,
            },
        ],
        "https://api.github.com/repos/a/b": {"stargazers_count": 10, "topics": []},
    }
    client = FakeHTTPClient(responses)
    out = github_source.fetch_releases(["a/b"], client=client, today=now)
    assert out == []


def test_fetch_releases_continues_past_repo_failure():
    responses = {
        "https://api.github.com/repos/good/repo/releases": [],
        "https://api.github.com/repos/bad/repo/releases": RuntimeError("500"),
    }
    client = FakeHTTPClient(responses)
    out = github_source.fetch_releases(["bad/repo", "good/repo"], client=client)
    assert out == []  # both empty, but no raise


# ---------------------------------------------------------------------------
# _parse_iso
# ---------------------------------------------------------------------------

def test_parse_iso_handles_z_suffix():
    dt = github_source._parse_iso("2026-04-15T12:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None


def test_parse_iso_returns_none_on_garbage():
    assert github_source._parse_iso("not-a-date") is None
    assert github_source._parse_iso(None) is None


# ---------------------------------------------------------------------------
# ingest_github + compute_stars_velocity_7d — DB integration
# ---------------------------------------------------------------------------


def test_ingest_github_writes_rows_and_snapshots(db_session, monkeypatch):
    from app.models import DevPost, RepoStarSnapshot

    now = datetime.now(timezone.utc)

    monkeypatch.setattr(
        github_source,
        "_load_config",
        lambda: {"github_languages": ["Rust"], "github_curated_repos": ["acme/widget"]},
    )
    monkeypatch.setattr(
        github_source,
        "fetch_trending",
        lambda langs, *, token=None, client=None, today=None: [
            {
                "kind": "trending",
                "repo": "acme/widget",
                "url": "https://github.com/acme/widget",
                "title": "widget",
                "stars": 1500,
                "published_at": now,
                "language": "Rust",
                "topics": ["rust"],
            }
        ],
    )
    monkeypatch.setattr(
        github_source,
        "fetch_releases",
        lambda repos, *, token=None, client=None, today=None: [
            {
                "kind": "release",
                "repo": "acme/widget",
                "url": "https://github.com/acme/widget/releases/tag/v1",
                "title": "widget v1",
                "version": "v1",
                "release_notes": "new feature",
                "stars": 1500,
                "published_at": now,
                "topics": ["rust"],
            }
        ],
    )

    added = github_source.ingest_github(db_session)
    assert added == 2

    rows = db_session.query(DevPost).filter_by(source="github").all()
    assert len(rows) == 2
    kinds = {r.url: r for r in rows}
    release = kinds["https://github.com/acme/widget/releases/tag/v1"]
    assert release.version == "v1"
    assert release.release_notes_excerpt == "new feature"

    # One snapshot per touched repo, regardless of trending+release split.
    snaps = db_session.query(RepoStarSnapshot).filter_by(repo="acme/widget").all()
    assert len(snaps) == 1
    assert snaps[0].stars == 1500

    # Rerun: URLs dedup → 0 new DevPost rows. Snapshots are append-only by design.
    added = github_source.ingest_github(db_session)
    assert added == 0
    assert db_session.query(DevPost).filter_by(source="github").count() == 2


def test_compute_stars_velocity_with_prior_snapshots(db_session):
    from app.models import RepoStarSnapshot

    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            RepoStarSnapshot(
                repo="a/b", stars=500, observed_at=now - timedelta(days=10)
            ),
            RepoStarSnapshot(
                repo="a/b", stars=700, observed_at=now - timedelta(days=8)
            ),
            RepoStarSnapshot(
                repo="a/b", stars=900, observed_at=now - timedelta(minutes=1)
            ),
        ]
    )
    db_session.commit()

    # Baseline = most recent snapshot at least 7 days old (700).
    # Latest = 900. Δ = 200.
    vel = github_source.compute_stars_velocity_7d(db_session, "a/b", now=now)
    assert vel == 200


def test_compute_stars_velocity_no_baseline_returns_none(db_session):
    from app.models import RepoStarSnapshot

    now = datetime.now(timezone.utc)
    # Only a recent snapshot — no baseline ≥7 days old.
    db_session.add(
        RepoStarSnapshot(repo="a/b", stars=100, observed_at=now - timedelta(days=2))
    )
    db_session.commit()

    assert github_source.compute_stars_velocity_7d(db_session, "a/b", now=now) is None

    # No snapshots at all → also None.
    assert (
        github_source.compute_stars_velocity_7d(db_session, "never/seen", now=now)
        is None
    )
