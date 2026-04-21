"""HN source tests — mocks the HN Firebase HTTP client.

Tests `fetch_hn_candidates`/`fetch_hn_comments` directly (no DB) and the
`_matches_allowlist` / `_matches_blocklist` helpers. Integration against the
`ingest_hn(db)` entry point is skipped until Slice 1 lands the DevPost model.
"""

from datetime import datetime, timezone

from app.services import hn_source


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class FakeHTTPClient:
    """Minimal stand-in for httpx.Client."""

    def __init__(self, url_map: dict):
        self.url_map = url_map
        self.calls: list[str] = []

    def get(self, url, timeout=None):
        self.calls.append(url)
        if url in self.url_map:
            data = self.url_map[url]
            if isinstance(data, Exception):
                raise data
            return FakeResponse(data)
        raise KeyError(url)

    def close(self):
        return None


# ---------------------------------------------------------------------------
# Keyword filters
# ---------------------------------------------------------------------------

def test_allowlist_matches_case_insensitively():
    assert hn_source._matches_allowlist("Show HN: Claude Code", ["claude code"]) is True
    assert hn_source._matches_allowlist("cursor is cool", ["cursor"]) is True
    assert hn_source._matches_allowlist("some post about cows", ["claude code"]) is False


def test_blocklist_excludes():
    assert hn_source._matches_blocklist("CEO steps down", ["CEO"]) is True
    assert hn_source._matches_blocklist("MCP patterns", ["CEO", "funding round"]) is False


# ---------------------------------------------------------------------------
# fetch_hn_candidates
# ---------------------------------------------------------------------------

def _item(item_id, **kw):
    base = {
        "id": item_id,
        "type": "story",
        "title": "Show HN: Claude Code patterns",
        "url": f"https://example.com/{item_id}",
        "by": "user",
        "score": 100,
        "descendants": 10,
        "time": 1712000000,
        "kids": [101, 102],
    }
    base.update(kw)
    return base


def test_fetch_hn_candidates_applies_allowlist(monkeypatch, tmp_path):
    # Override the config path to a known fixture.
    cfg_path = tmp_path / "devs_config.yaml"
    cfg_path.write_text(
        "hn_keyword_allowlist:\n  - claude code\nhn_keyword_blocklist:\n  - lawsuit\n"
    )
    monkeypatch.setattr(hn_source, "_CONFIG_PATH", cfg_path)

    url_map = {
        hn_source._TOP_STORIES_URL: [1, 2, 3],
        hn_source._ITEM_URL.format(item_id=1): _item(1, title="Claude Code tips"),
        hn_source._ITEM_URL.format(item_id=2): _item(2, title="Random post about cars"),
        hn_source._ITEM_URL.format(item_id=3): _item(3, title="Lawsuit filed over Claude Code"),
    }
    client = FakeHTTPClient(url_map)

    out = hn_source.fetch_hn_candidates(limit=10, client=client)
    titles = [c["title"] for c in out]
    assert titles == ["Claude Code tips"]


def test_fetch_hn_candidates_skips_non_story_and_dead(monkeypatch, tmp_path):
    cfg_path = tmp_path / "devs_config.yaml"
    cfg_path.write_text("hn_keyword_allowlist:\n  - mcp\n")
    monkeypatch.setattr(hn_source, "_CONFIG_PATH", cfg_path)

    url_map = {
        hn_source._TOP_STORIES_URL: [1, 2, 3, 4],
        hn_source._ITEM_URL.format(item_id=1): _item(1, title="MCP deep dive"),
        hn_source._ITEM_URL.format(item_id=2): _item(2, type="comment", title="MCP"),
        hn_source._ITEM_URL.format(item_id=3): _item(3, dead=True, title="MCP"),
        hn_source._ITEM_URL.format(item_id=4): _item(4, deleted=True, title="MCP"),
    }
    client = FakeHTTPClient(url_map)

    out = hn_source.fetch_hn_candidates(limit=10, client=client)
    assert [c["hn_id"] for c in out] == [1]


def test_fetch_hn_candidates_missing_url_uses_hn_comment_link(monkeypatch, tmp_path):
    cfg_path = tmp_path / "devs_config.yaml"
    cfg_path.write_text("hn_keyword_allowlist:\n  - ask hn\n")
    monkeypatch.setattr(hn_source, "_CONFIG_PATH", cfg_path)

    url_map = {
        hn_source._TOP_STORIES_URL: [1],
        hn_source._ITEM_URL.format(item_id=1): _item(1, title="Ask HN: best MCP tools", url=None),
    }
    client = FakeHTTPClient(url_map)

    out = hn_source.fetch_hn_candidates(limit=10, client=client)
    assert out[0]["url"] == hn_source._hn_item_url(1)


def test_fetch_hn_candidates_handles_top_fetch_error(monkeypatch):
    client = FakeHTTPClient({hn_source._TOP_STORIES_URL: RuntimeError("boom")})
    out = hn_source.fetch_hn_candidates(client=client)
    assert out == []


def test_fetch_hn_candidates_published_at_is_tz_aware(monkeypatch, tmp_path):
    cfg_path = tmp_path / "devs_config.yaml"
    cfg_path.write_text("hn_keyword_allowlist:\n  - mcp\n")
    monkeypatch.setattr(hn_source, "_CONFIG_PATH", cfg_path)

    url_map = {
        hn_source._TOP_STORIES_URL: [1],
        hn_source._ITEM_URL.format(item_id=1): _item(1, title="MCP thing", time=1712000000),
    }
    client = FakeHTTPClient(url_map)
    out = hn_source.fetch_hn_candidates(client=client)
    assert isinstance(out[0]["published_at"], datetime)
    assert out[0]["published_at"].tzinfo is not None


# ---------------------------------------------------------------------------
# fetch_hn_comments
# ---------------------------------------------------------------------------

def test_fetch_hn_comments_returns_top_comments():
    url_map = {
        hn_source._ITEM_URL.format(item_id=100): {"id": 100, "kids": [101, 102, 103]},
        hn_source._ITEM_URL.format(item_id=101): {"id": 101, "text": "first comment", "by": "a"},
        hn_source._ITEM_URL.format(item_id=102): {"id": 102, "text": "second", "by": "b"},
        hn_source._ITEM_URL.format(item_id=103): {"id": 103, "text": "third", "by": "c"},
    }
    client = FakeHTTPClient(url_map)
    out = hn_source.fetch_hn_comments(100, max_comments=2, client=client)
    assert len(out) == 2
    assert out[0]["text"] == "first comment"


def test_fetch_hn_comments_skips_dead_and_deleted():
    url_map = {
        hn_source._ITEM_URL.format(item_id=100): {"id": 100, "kids": [101, 102, 103]},
        hn_source._ITEM_URL.format(item_id=101): {"id": 101, "dead": True, "text": "x"},
        hn_source._ITEM_URL.format(item_id=102): {"id": 102, "deleted": True},
        hn_source._ITEM_URL.format(item_id=103): {"id": 103, "text": "good one", "by": "c"},
    }
    client = FakeHTTPClient(url_map)
    out = hn_source.fetch_hn_comments(100, client=client)
    assert len(out) == 1
    assert out[0]["text"] == "good one"


def test_fetch_hn_comments_handles_fetch_error():
    client = FakeHTTPClient(
        {hn_source._ITEM_URL.format(item_id=100): RuntimeError("nope")}
    )
    assert hn_source.fetch_hn_comments(100, client=client) == []
