from app.services.tavily_search import _normalize_published_date


def test_normalize_iso_date_prefix():
    assert _normalize_published_date("2026-04-06T14:30:00Z") == "2026-04-06"
    assert _normalize_published_date("2026-04-06") == "2026-04-06"


def test_normalize_rfc2822():
    assert _normalize_published_date("Mon, 06 Apr 2026 12:00:00 GMT") == "2026-04-06"


def test_normalize_empty():
    assert _normalize_published_date(None) == ""
    assert _normalize_published_date("") == ""
    assert _normalize_published_date("   ") == ""
