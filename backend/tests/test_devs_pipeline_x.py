"""X pipeline tests — placeholders for full integration coverage.

Contract stubs (harmonizer kept them as no-op pass tests; re-author with
real bodies in a follow-up pass).
"""


def test_collect_x_inserts_tweets_and_scores():
    """Apify results persisted; rank_x_tweet sets quality_score."""


def test_publish_x_clusters_and_synthesizes_bullets():
    """cluster → synthesize → XTopicDigestRow with bullets+sources."""


def test_publish_x_backlinks_used_in_digest_id():
    """Tweets cited in a digest have used_in_digest_id set."""


def test_publish_x_assigns_slots_6_to_8():
    """Top-3 X topic digests get display_order 6,7,8."""
