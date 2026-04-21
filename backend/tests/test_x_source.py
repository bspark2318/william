"""X source tests — mocks the Apify client.

Direct DB integration tests are skipped until Slice 1 merges CandidateXTweet.
"""

from datetime import datetime, timedelta, timezone

from app.services import x_source


class FakeActor:
    def __init__(self, run_result):
        self.run_result = run_result
        self.run_input: dict | None = None

    def call(self, run_input=None):
        self.run_input = run_input
        return self.run_result


class FakeDataset:
    def __init__(self, items):
        self._items = items

    def iterate_items(self):
        return iter(self._items)


class FakeApifyClient:
    def __init__(self, items, dataset_id="ds-1"):
        self.items = items
        self.dataset_id = dataset_id
        self.last_actor: str | None = None

    def actor(self, actor_id):
        self.last_actor = actor_id
        return FakeActor({"defaultDatasetId": self.dataset_id})

    def dataset(self, ds_id):
        assert ds_id == self.dataset_id
        return FakeDataset(self.items)


def _now():
    return datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)


def _tweet(id_, handle="karpathy", minutes_ago=10, **kw):
    created = _now() - timedelta(minutes=minutes_ago)
    base = {
        "id": str(id_),
        "url": f"https://twitter.com/{handle}/status/{id_}",
        "author": {"userName": handle, "name": handle.title()},
        "text": f"Tweet {id_}",
        "createdAt": created.isoformat().replace("+00:00", "Z"),
        "likeCount": 100,
        "retweetCount": 20,
        "replyCount": 5,
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# _extract_tweet
# ---------------------------------------------------------------------------

def test_extract_tweet_basic_fields():
    out = x_source._extract_tweet(_tweet(1))
    assert out is not None
    assert out["url"] == "https://twitter.com/karpathy/status/1"
    assert out["author_handle"] == "karpathy"
    assert out["likes"] == 100
    assert out["reposts"] == 20
    assert out["replies"] == 5
    assert isinstance(out["published_at"], datetime)


def test_extract_tweet_skips_replies():
    assert x_source._extract_tweet(_tweet(1, isReply=True)) is None
    assert x_source._extract_tweet(_tweet(1, inReplyToId="999")) is None


def test_extract_tweet_skips_retweets_and_quotes():
    assert x_source._extract_tweet(_tweet(1, isRetweet=True)) is None
    assert x_source._extract_tweet(_tweet(1, isQuote=True)) is None


def test_extract_tweet_builds_url_from_id_when_missing():
    t = _tweet(42)
    t["url"] = None
    out = x_source._extract_tweet(t)
    assert out is not None
    assert "status/42" in out["url"]


def test_extract_tweet_requires_text_and_handle():
    assert x_source._extract_tweet({}) is None
    t = _tweet(1)
    t["text"] = ""
    assert x_source._extract_tweet(t) is None
    t = _tweet(1)
    t["author"] = {}
    t["username"] = None
    t["user"] = {}
    assert x_source._extract_tweet(t) is None


def test_parse_tweet_datetime_variants():
    assert isinstance(x_source._parse_tweet_datetime("2026-04-15T12:00:00Z"), datetime)
    assert x_source._parse_tweet_datetime(None) is None
    assert x_source._parse_tweet_datetime("garbage") is None
    # Twitter's classic format.
    assert isinstance(
        x_source._parse_tweet_datetime("Wed Apr 15 14:30:00 +0000 2026"), datetime
    )


# ---------------------------------------------------------------------------
# _flatten_handles
# ---------------------------------------------------------------------------

def test_flatten_handles_strips_at_and_dedups():
    cfg = {
        "x_handles": {
            "tier_a": ["@karpathy", "simonw", "karpathy"],
            "tier_b": ["swyx"],
        }
    }
    out = x_source._flatten_handles(cfg)
    assert out == ["karpathy", "simonw", "swyx"]


def test_flatten_handles_empty():
    assert x_source._flatten_handles({}) == []
    assert x_source._flatten_handles({"x_handles": None}) == []


# ---------------------------------------------------------------------------
# fetch_tweets_via_apify
# ---------------------------------------------------------------------------

def test_fetch_tweets_via_apify_filters_window_and_shape():
    items = [
        _tweet(1, minutes_ago=10),
        _tweet(2, isReply=True),  # skipped
        _tweet(3, minutes_ago=60 * 48),  # outside 30h lookback -> skipped
    ]
    client = FakeApifyClient(items)
    out = x_source.fetch_tweets_via_apify(
        ["karpathy"], token="t", client=client, now=_now()
    )
    assert len(out) == 1
    assert out[0]["url"].endswith("/status/1")
    assert client.last_actor == x_source._APIFY_ACTOR_ID


def test_fetch_tweets_via_apify_empty_handles_returns_empty():
    client = FakeApifyClient([])
    assert x_source.fetch_tweets_via_apify([], token="t", client=client) == []


def test_fetch_tweets_via_apify_handles_actor_error():
    class BrokenActor:
        def call(self, run_input=None):
            raise RuntimeError("actor failed")

    class BrokenClient:
        def actor(self, _):
            return BrokenActor()

    out = x_source.fetch_tweets_via_apify(["karpathy"], token="t", client=BrokenClient())
    assert out == []


def test_fetch_tweets_via_apify_no_dataset_id():
    class NoDS:
        def actor(self, _):
            class A:
                def call(self, run_input=None):
                    return {}  # missing defaultDatasetId

            return A()

    out = x_source.fetch_tweets_via_apify(["a"], token="t", client=NoDS())
    assert out == []


# ---------------------------------------------------------------------------
# ingest_x — DB integration
# ---------------------------------------------------------------------------


def test_ingest_x_writes_rows_and_dedups(db_session, monkeypatch):
    from app.models import CandidateXTweet

    monkeypatch.setattr(x_source, "_flatten_handles", lambda cfg: ["karpathy"])

    now = datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)
    tweet = {
        "url": "https://twitter.com/karpathy/status/1",
        "author_handle": "karpathy",
        "author_name": "Andrej",
        "author_avatar_url": None,
        "text": "hello",
        "likes": 100,
        "reposts": 20,
        "replies": 5,
        "published_at": now,
    }
    monkeypatch.setattr(
        x_source, "fetch_tweets_via_apify", lambda handles, **kw: [tweet]
    )

    added = x_source.ingest_x(db_session, token="fake")
    assert added == 1

    rows = db_session.query(CandidateXTweet).all()
    assert len(rows) == 1
    assert rows[0].author_handle == "karpathy"
    assert rows[0].likes == 100
    # Scoring happens at the pipeline layer, not ingest.
    assert rows[0].quality_score is None

    # Rerun: same URL → dedup.
    added = x_source.ingest_x(db_session, token="fake")
    assert added == 0
    assert db_session.query(CandidateXTweet).count() == 1
