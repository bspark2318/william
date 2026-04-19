"""HN pipeline tests — placeholders for full integration coverage.

Contract stubs (harmonizer kept them as no-op pass tests; re-author with
real bodies in a follow-up pass).
"""


def test_collect_hn_inserts_rows_and_scores():
    """Happy path: ingest + score new HN candidates, rank_features populated."""


def test_collect_hn_dedups_by_url():
    """Re-running collect should not duplicate existing URL rows."""


def test_publish_hn_populates_bullets_and_flips_active():
    """publish_hn picks top finalists, generates bullets, assigns display_order 1..3."""


def test_publish_hn_sets_top_comment_excerpt():
    """Top-scored comment text is stored (first 280 chars)."""


def test_publish_dev_feed_deactivates_previous_issue():
    """All prior active rows flipped to is_active=False before new publish."""
