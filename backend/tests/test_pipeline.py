from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.database import SessionLocal
from app.models import CandidateStory, CandidateVideo, ChannelReputation, Issue
from app.services.pipeline import (
    _compute_video_heuristic,
    _dedup_stories,
    _dedup_videos,
    _duration_preference,
    _freshness_decay,
    _heuristic_filter_stories,
    _heuristic_filter_videos,
    _recompute_tier,
    _update_channel_seen,
    _update_channel_selected,
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


def _add_video(
    db,
    youtube_id,
    title,
    view_count=10000,
    importance_score=7.0,
    channel="TestChannel",
    like_count=100,
    comment_count=10,
    engagement_rate=0.011,
    view_velocity=200.0,
    duration_seconds=600,
    content_type="deep_analysis",
):
    v = CandidateVideo(
        youtube_id=youtube_id,
        title=title,
        channel=channel,
        thumbnail_url=f"https://t.example/{youtube_id}",
        published_at="2026-04-09",
        search_query="vq",
        processed=False,
        view_count=view_count,
        importance_score=importance_score,
        like_count=like_count,
        comment_count=comment_count,
        engagement_rate=engagement_rate,
        view_velocity=view_velocity,
        duration_seconds=duration_seconds,
        content_type=content_type,
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
        assert all(not v.processed for v in db.query(CandidateVideo).all())
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


@patch("app.services.pipeline.tight_bullets", return_value=["x", "y", "z"])
@patch("app.services.pipeline.generate_title", return_value="Mock Title")
@patch("app.services.pipeline.comparative_select_videos")
@patch("app.services.pipeline.comparative_select_stories")
def test_publish_does_not_mark_videos_processed(
    mock_comp_s, mock_comp_v, _mock_title, _mock_bullets
):
    """Featured picks stay in the rolling pool; videos are not marked processed on publish."""
    db = SessionLocal()
    try:
        s1 = _add_story(db, "Story A", "https://a.example", importance_score=9.0)
        v_win = _add_video(db, "vid1", "Video A", importance_score=9.0)
        v_lose = _add_video(db, "vid2", "Video B", importance_score=7.0)
        db.commit()
        db.refresh(s1)
        db.refresh(v_win)
        db.refresh(v_lose)

        mock_comp_s.return_value = [{"id": s1.id, "rank": 1, "topic": "t"}]
        mock_comp_v.return_value = [{"id": v_win.id, "rank": 1, "topic": "v"}]

        out = publish_issue(db)
        assert out["status"] == "published"
        assert out["videos"] == 1

        db.refresh(v_win)
        db.refresh(v_lose)
        assert v_win.processed is False
        assert v_lose.processed is False
    finally:
        db.close()


@patch("app.services.pipeline.tight_bullets", return_value=["x", "y", "z"])
@patch("app.services.pipeline.generate_title", return_value="Mock Title")
@patch("app.services.pipeline.comparative_select_videos")
@patch("app.services.pipeline.comparative_select_stories")
def test_publish_excludes_videos_outside_lookback(
    mock_comp_s, mock_comp_v, _mock_title, _mock_bullets
):
    db = SessionLocal()
    try:
        s1 = _add_story(db, "Story A", "https://a.example", importance_score=9.0)
        v_old = _add_video(db, "vid-old", "Old pool video", importance_score=9.0)
        v_old.collected_at = datetime.now(timezone.utc) - timedelta(days=10)
        db.commit()
        db.refresh(s1)
        db.refresh(v_old)

        mock_comp_s.return_value = [{"id": s1.id, "rank": 1, "topic": "t"}]
        mock_comp_v.return_value = []

        out = publish_issue(db)
        assert out["status"] == "published"
        assert out["videos"] == 0

        db.refresh(v_old)
        assert v_old.processed is False
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Multi-signal heuristic scoring
# ---------------------------------------------------------------------------

def test_duration_preference_ideal_range():
    assert _duration_preference(600) == 10.0
    assert _duration_preference(300) == 10.0
    assert _duration_preference(1500) == 10.0


def test_duration_preference_outside_range():
    assert _duration_preference(30) < 10.0
    assert _duration_preference(5000) < 10.0
    assert _duration_preference(0) == 0.0


def test_freshness_decay():
    from datetime import date, datetime, timedelta, timezone

    today = date.today().isoformat()
    assert _freshness_decay(today) > 8.0

    old = (date.today() - timedelta(days=10)).isoformat()
    assert _freshness_decay(old) == 0.0


def test_compute_video_heuristic_returns_bounded_score():
    class FakeVideo:
        view_velocity = 500.0
        engagement_rate = 0.01
        view_count = 100000
        duration_seconds = 600
        published_at = "2026-04-09"

    score = _compute_video_heuristic(FakeVideo(), "top")
    assert 0.0 <= score <= 10.0


def test_heuristic_filter_videos_rejects_bottom():
    db = SessionLocal()
    try:
        for i in range(8):
            _add_video(
                db, f"yt{i}", f"Video {i}",
                view_count=(i + 1) * 10000,
                view_velocity=(i + 1) * 100,
                importance_score=None,
            )
        db.commit()

        candidates = db.query(CandidateVideo).all()
        survivors, rejects = _heuristic_filter_videos(candidates, {})

        assert len(survivors) == 6
        assert len(rejects) == 2
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Channel reputation
# ---------------------------------------------------------------------------

def test_recompute_tier():
    rep = ChannelReputation(channel_name="X", times_seen=10, times_selected=5, avg_importance_score=8.0)
    assert _recompute_tier(rep) == "top"

    rep2 = ChannelReputation(channel_name="Y", times_seen=10, times_selected=1, avg_importance_score=6.0)
    assert _recompute_tier(rep2) == "good"

    rep3 = ChannelReputation(channel_name="Z", times_seen=10, times_selected=0, avg_importance_score=2.0)
    assert _recompute_tier(rep3) == "low"

    rep4 = ChannelReputation(channel_name="W", times_seen=1, times_selected=0, avg_importance_score=5.0)
    assert _recompute_tier(rep4) == "unknown"


def test_update_channel_seen_creates_and_updates():
    db = SessionLocal()
    try:
        _update_channel_seen(db, "NewChannel", 8.0)
        db.commit()

        rep = db.query(ChannelReputation).filter_by(channel_name="NewChannel").one()
        assert rep.times_seen == 1
        assert rep.avg_importance_score == 8.0

        _update_channel_seen(db, "NewChannel", 6.0)
        db.commit()
        db.refresh(rep)

        assert rep.times_seen == 2
        assert rep.avg_importance_score == 7.0
    finally:
        db.close()


def test_update_channel_selected():
    db = SessionLocal()
    try:
        _update_channel_selected(db, "SelChannel")
        db.commit()

        rep = db.query(ChannelReputation).filter_by(channel_name="SelChannel").one()
        assert rep.times_selected == 1

        _update_channel_selected(db, "SelChannel")
        db.commit()
        db.refresh(rep)
        assert rep.times_selected == 2
    finally:
        db.close()
