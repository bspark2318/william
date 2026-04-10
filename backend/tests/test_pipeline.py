from unittest.mock import patch

from app.database import SessionLocal
from app.models import CandidateStory, CandidateVideo, Issue
from app.services.pipeline import publish_issue


def test_publish_issue_skips_without_stories():
    db = SessionLocal()
    try:
        out = publish_issue(db)
        assert out == {"status": "skipped", "reason": "no story candidates"}
    finally:
        db.close()


@patch("app.services.pipeline.tight_bullets", return_value=["x", "y", "z"])
@patch("app.services.pipeline.generate_title", return_value="Mock Title")
@patch("app.services.pipeline.rank_videos")
@patch("app.services.pipeline.rank_stories")
def test_publish_issue_creates_issue(mock_rank_s, mock_rank_v, mock_title, _mock_bullets):
    db = SessionLocal()
    try:
        db.add_all(
            [
                CandidateStory(
                    title="A",
                    summary="sa",
                    source="s",
                    url="https://p1.example",
                    date="2026-04-01",
                    search_query="q",
                    processed=False,
                ),
                CandidateStory(
                    title="B",
                    summary="sb",
                    source="s",
                    url="https://p2.example",
                    date="2026-04-01",
                    search_query="q",
                    processed=False,
                ),
                CandidateVideo(
                    youtube_id="vid1",
                    title="V",
                    channel="c",
                    thumbnail_url="https://t.example",
                    published_at="2026-04-01",
                    search_query="vq",
                    processed=False,
                ),
            ]
        )
        db.commit()
        s1, s2 = db.query(CandidateStory).order_by(CandidateStory.id).all()
        v1 = db.query(CandidateVideo).one()
        mock_rank_s.return_value = [
            {"id": s1.id, "score": 9.0, "reasoning": "a"},
            {"id": s2.id, "score": 8.0, "reasoning": "b"},
        ]
        mock_rank_v.return_value = [{"id": v1.id, "score": 8.0, "reasoning": "x"}]

        out = publish_issue(db)
        assert out["status"] == "published"
        assert out["title"] == "Mock Title"
        assert out["stories"] == 2
        assert out["videos"] == 1

        issue = db.query(Issue).one()
        assert issue.title == "Mock Title"
        assert len(issue.stories) == 2
        assert issue.stories[0].bullet_points == ["x", "y", "z"]
        assert issue.stories[0].summary == "x y z"
        assert len(issue.featured_videos) == 1
        assert all(s.processed for s in db.query(CandidateStory).all())
        assert all(v.processed for v in db.query(CandidateVideo).all())
    finally:
        db.close()
