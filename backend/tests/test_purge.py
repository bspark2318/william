from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.database import SessionLocal
from app.models import CandidateStory, CandidateVideo, Issue, Story, FeaturedVideo
from app.services.pipeline import purge_old_data


def _old_dt(days: int = 45):
    return datetime.now(timezone.utc) - timedelta(days=days)


def _recent_dt(days: int = 5):
    return datetime.now(timezone.utc) - timedelta(days=days)


def test_purge_deletes_old_issues_and_candidates():
    db = SessionLocal()
    try:
        old_issue = Issue(week_of="2026-02-01", title="Old", created_at=_old_dt())
        new_issue = Issue(week_of="2026-04-01", title="New", created_at=_recent_dt())
        db.add_all([old_issue, new_issue])
        db.flush()

        db.add(Story(issue_id=old_issue.id, title="OS", summary="s", source="x",
                      url="https://old.example", date="2026-02-01", display_order=1))
        db.add(Story(issue_id=new_issue.id, title="NS", summary="s", source="x",
                      url="https://new.example", date="2026-04-01", display_order=1))

        db.add(CandidateStory(title="OC", summary="s", source="x",
                               url="https://oc.example", date="2026-02-01",
                               search_query="q", collected_at=_old_dt()))
        db.add(CandidateStory(title="NC", summary="s", source="x",
                               url="https://nc.example", date="2026-04-01",
                               search_query="q", collected_at=_recent_dt()))

        db.add(CandidateVideo(youtube_id="old-v", title="OV", channel="c",
                               thumbnail_url="https://t.example",
                               published_at="2026-02-01", search_query="q",
                               collected_at=_old_dt()))
        db.add(CandidateVideo(youtube_id="new-v", title="NV", channel="c",
                               thumbnail_url="https://t.example",
                               published_at="2026-04-01", search_query="q",
                               collected_at=_recent_dt()))
        db.commit()

        result = purge_old_data(db)

        assert result["issues_deleted"] == 1
        assert result["candidate_stories_deleted"] == 1
        assert result["candidate_videos_deleted"] == 1

        assert db.query(Issue).count() == 1
        assert db.query(Issue).one().title == "New"
        assert db.query(Story).count() == 1
        assert db.query(CandidateStory).count() == 1
        assert db.query(CandidateVideo).count() == 1
    finally:
        db.close()


def test_purge_noop_when_nothing_old():
    db = SessionLocal()
    try:
        db.add(Issue(week_of="2026-04-01", title="Recent", created_at=_recent_dt()))
        db.add(CandidateStory(title="RC", summary="s", source="x",
                               url="https://rc.example", date="2026-04-01",
                               search_query="q", collected_at=_recent_dt()))
        db.commit()

        result = purge_old_data(db)

        assert result["issues_deleted"] == 0
        assert result["candidate_stories_deleted"] == 0
        assert result["candidate_videos_deleted"] == 0
        assert db.query(Issue).count() == 1
        assert db.query(CandidateStory).count() == 1
    finally:
        db.close()


@patch("app.services.pipeline.RETENTION_DAYS", 10)
def test_purge_respects_retention_days_override():
    db = SessionLocal()
    try:
        db.add(Issue(week_of="2026-03-20", title="15d old",
                     created_at=datetime.now(timezone.utc) - timedelta(days=15)))
        db.add(Issue(week_of="2026-04-05", title="3d old",
                     created_at=datetime.now(timezone.utc) - timedelta(days=3)))
        db.commit()

        result = purge_old_data(db)

        assert result["issues_deleted"] == 1
        assert db.query(Issue).one().title == "3d old"
    finally:
        db.close()
