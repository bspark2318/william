"""Rotate which search queries run each collect so a large pool stays under a daily API budget."""

from datetime import date


def queries_for_collect(
    all_queries: list[str],
    max_calls: int | None,
    today: date,
) -> list[str]:
    """
    Return up to `max_calls` queries, starting at a day-dependent offset (wraps).

    If max_calls is None or >= len(all_queries), returns all_queries unchanged.
    """
    if not all_queries:
        return []
    n = len(all_queries)
    if max_calls is None or max_calls >= n:
        return list(all_queries)
    if max_calls <= 0:
        return []
    start = today.toordinal() % n
    return [all_queries[(start + i) % n] for i in range(max_calls)]
