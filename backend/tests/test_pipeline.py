from unittest.mock import patch

from app.database import SessionLocal
from app.models import CandidateStory, CandidateVideo, Issue
from app.services.pipeline import (
    _dedup_stories,
    _dedup_videos,
    _heuristic_filter_stories,
    collect_candidates,
    publish_issue,
)


def test_publish_issue_skips_without_stories():
    db = SessionLocal()
    try:
        out = publish_issue(db)
        assert out == {"status": "skipped", "reason": "no story candidates"}
    finally:
        db.close()


def _add_story(db, title, url, tavily_score=0.8, importance_score=7.0):
    s = CandidateStory(
        title=title,
        summary=f"Summary about {title}",
        source="TestSource",
        url=url,
        date="2026-04-01",
        search_query="q",
        processed=False,
        tavily_score=tavily_score,
        importance_score=importance_score,
    )
    db.add(s)
    return s


def _add_video(db, youtube_id, title, view_count=10000, importance_score=7.0):
    v = CandidateVideo(
        youtube_id=youtube_id,
        title=title,
        channel="TestChannel",
        thumbnail_url=f"https://t.example/{youtube_id}",
        published_at="2026-04-01",
        search_query="vq",
        processed=False,
        view_count=view_count,
        importance_score=importance_score,
    )
    db.add(v)
    return v


# ---------------------------------------------------------------------------
# Dedup tests
# ---------------------------------------------------------------------------

def test_dedup_stories_removes_similar_titles():
    db = SessionLocal()
    try:
        s1 = _add_story(db, "OpenAI releases GPT-5 model", "https://a.example", tavily_score=0.9)
        s2 = _add_story(db, "OpenAI releases GPT-5 model today", "https://b.example", tavily_score=0.7)
        s3 = _add_story(db, "New robotics breakthrough at MIT", "https://c.example", tavily_score=0.8)
        db.commit()

        candidates = db.query(CandidateStory).all()
        survivors, rejects = _dedup_stories(candidates)
        survivor_urls = {s.url for s in survivors}

        assert len(survivors) == 2
        assert "https://a.example" in survivor_urls
        assert "https://c.example" in survivor_urls
        assert len(rejects) == 1
    finally:
        db.close()


def test_dedup_videos_removes_similar_titles():
    db = SessionLocal()
    try:
        _add_video(db, "yt1", "AI News This Week Highlights", view_count=50000)
        _add_video(db, "yt2", "AI News This Week Highlights Recap", view_count=20000)
        _add_video(db, "yt3", "Robotics Foundation Model Demo", view_count=30000)
        db.commit()

        candidates = db.query(CandidateVideo).all()
        survivors, rejects = _dedup_videos(candidates)

        assert len(survivors) == 2
        assert len(rejects) == 1
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Heuristic filter tests
# ---------------------------------------------------------------------------

def test_heuristic_filter_stories_keeps_top_half():
    db = SessionLocal()
    try:
        for i in range(10):
            _add_story(db, f"Story {i}", f"https://{i}.example",
                       tavily_score=0.3 + i * 0.05, importance_score=None)
        db.commit()

        candidates = db.query(CandidateStory).all()
        survivors, rejects = _heuristic_filter_stories(candidates)

        assert len(survivors) == 5
        assert len(rejects) == 5
        assert all((s.tavily_score or 0) >= 0.3 for s in survivors)
    finally:
        db.close()


def test_heuristic_filter_rejects_low_tavily():
    db = SessionLocal()
    try:
        _add_story(db, "Good", "https://g.example", tavily_score=0.9, importance_score=None)
        _add_story(db, "Bad", "https://b.example", tavily_score=0.1, importance_score=None)
        db.commit()

        candidates = db.query(CandidateStory).all()
        survivors, rejects = _heuristic_filter_stories(candidates)

        assert len(survivors) == 1
        assert survivors[0].title == "Good"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# End-to-end publish tests
# ---------------------------------------------------------------------------

@patch("app.services.pipeline.tight_bullets", return_value=["x", "y", "z"])
@patch("app.services.pipeline.generate_title", return_value="Mock Title")
@patch("app.services.pipeline.comparative_select_videos")
@patch("app.services.pipeline.comparative_select_stories")
def test_publish_creates_issue(mock_comp_s, mock_comp_v, mock_title, _mock_bullets):
    db = SessionLocal()
    try:
        s1 = _add_story(db, "Story A", "https://a.example", importance_score=9.0)
        s2 = _add_story(db, "Story B", "https://b.example", importance_score=8.0)
        v1 = _add_video(db, "vid1", "Video A", importance_score=8.0)
        db.commit()

        db.refresh(s1)
        db.refresh(s2)
        db.refresh(v1)

        mock_comp_s.return_value = [
            {"id": s1.id, "rank": 1, "topic": "topic-a"},
            {"id": s2.id, "rank": 2, "topic": "topic-b"},
        ]
        mock_comp_v.return_value = [
            {"id": v1.id, "rank": 1, "topic": "vid-topic"},
        ]

        out = publish_issue(db)
        assert out["status"] == "published"
        assert out["title"] == "Mock Title"
        assert out["stories"] == 2
        assert out["videos"] == 1

        issue = db.query(Issue).one()
        assert issue.title == "Mock Title"
        assert len(issue.stories) == 2
        assert issue.stories[0].bullet_points == ["x", "y", "z"]
        assert len(issue.featured_videos) == 1
        assert all(s.processed for s in db.query(CandidateStory).all())
        assert all(v.processed for v in db.query(CandidateVideo).all())
    finally:
        db.close()


@patch("app.services.pipeline.tight_bullets", return_value=["x", "y"])
@patch("app.services.pipeline.generate_title", return_value="T")
@patch("app.services.pipeline.comparative_select_videos")
@patch("app.services.pipeline.comparative_select_stories")
@patch("app.services.pipeline.quick_rank_stories")
def test_publish_scores_stragglers(mock_qr, mock_comp_s, mock_comp_v, _title, _bullets):
    """Candidates with importance_score=None should be scored inline during publish."""
    db = SessionLocal()
    try:
        s = _add_story(db, "Unscored Story", "https://u.example", importance_score=None, tavily_score=0.5)
        db.commit()
        db.refresh(s)

        mock_qr.return_value = [{"id": s.id, "score": 7.0}]
        mock_comp_s.return_value = [{"id": s.id, "rank": 1, "topic": "t"}]
        mock_comp_v.return_value = []

        out = publish_issue(db)
        assert out["status"] == "published"
        mock_qr.assert_called_once()
    finally:
        db.close()


@patch("app.services.pipeline._score_unscored")
@patch("app.services.pipeline.search_videos", return_value=3)
@patch("app.services.pipeline.search_news", return_value=5)
def test_collect_calls_score_unscored(mock_news, mock_vids, mock_score):
    db = SessionLocal()
    try:
        out = collect_candidates(db)
        assert out["stories_added"] == 5
        assert out["videos_added"] == 3
        mock_score.assert_called_once_with(db)
    finally:
        db.close()
