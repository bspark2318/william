from datetime import date

from app.query_rotation import queries_for_collect


def test_queries_for_collect_all_when_no_cap():
    q = ["a", "b", "c"]
    assert queries_for_collect(q, None, date(2026, 4, 1)) == q
    assert queries_for_collect(q, 10, date(2026, 4, 1)) == q


def test_queries_for_collect_rotates_and_caps():
    q = ["a", "b", "c", "d", "e"]
    d = date(2026, 4, 9)
    start = d.toordinal() % 5
    expected = [q[(start + i) % 5] for i in range(3)]
    assert queries_for_collect(q, 3, d) == expected


def test_queries_for_collect_zero_returns_empty():
    assert queries_for_collect(["a", "b"], 0, date(2026, 1, 1)) == []
