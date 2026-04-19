"""HN pipeline tests — integration-heavy, skipped until Slice 1 merges."""

import pytest


@pytest.mark.skip(reason="needs Slice 1 merge (DevPost ORM model)")
def test_collect_hn_inserts_rows_and_scores():
    """Happy path: ingest + score new HN candidates, rank_features populated."""


@pytest.mark.skip(reason="needs Slice 1 merge (DevPost ORM model)")
def test_collect_hn_dedups_by_url():
    """Re-running collect should not duplicate existing URL rows."""


@pytest.mark.skip(reason="needs Slice 1 merge (DevPost ORM model)")
def test_publish_hn_populates_bullets_and_flips_active():
    """publish_hn picks top finalists, generates bullets, assigns display_order 1..3."""


@pytest.mark.skip(reason="needs Slice 1 merge (DevPost ORM model)")
def test_publish_hn_sets_top_comment_excerpt():
    """Top-scored comment text is stored (first 280 chars)."""


@pytest.mark.skip(reason="needs Slice 1 merge (DevPost + XTopicDigestRow models)")
def test_publish_dev_feed_deactivates_previous_issue():
    """All prior active rows flipped to is_active=False before new publish."""
