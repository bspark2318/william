"""GitHub pipeline tests — integration-heavy, skipped until Slice 1 merges."""

import pytest


@pytest.mark.skip(reason="needs Slice 1 merge (DevPost + RepoStarSnapshot models)")
def test_collect_github_writes_snapshots_for_velocity():
    """Every ingest run writes a RepoStarSnapshot for each touched repo."""


@pytest.mark.skip(reason="needs Slice 1 merge (RepoStarSnapshot model)")
def test_velocity_with_prior_snapshots_computes_delta():
    """compute_stars_velocity_7d returns stars(now) - stars(7d ago)."""


@pytest.mark.skip(reason="needs Slice 1 merge (RepoStarSnapshot model)")
def test_velocity_without_prior_snapshots_returns_none():
    """First-ever snapshot → velocity None (can't compute delta)."""


@pytest.mark.skip(reason="needs Slice 1 merge (DevPost model)")
def test_publish_github_populates_insights():
    """release_bullets, why_it_matters, has_breaking_changes written to finalists."""


@pytest.mark.skip(reason="needs Slice 1 merge (DevPost model)")
def test_publish_github_assigns_slots_4_and_5():
    """Top-2 GH picks get display_order 4,5."""
