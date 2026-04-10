from unittest.mock import patch

from app.models import CandidateStory, CandidateVideo


def test_list_candidates_empty(client):
    r = client.get("/api/admin/candidates")
    assert r.status_code == 200
    data = r.json()
    assert data["stories"] == []
    assert data["videos"] == []


def test_list_candidates_unprocessed_only(client, db_session):
    s = CandidateStory(
        title="t",
        summary="s",
        source="src",
        url="https://u1.example",
        date="2026-04-01",
        search_query="q",
        processed=False,
    )
    s2 = CandidateStory(
        title="t2",
        summary="s2",
        source="src",
        url="https://u2.example",
        date="2026-04-01",
        search_query="q",
        processed=True,
    )
    v = CandidateVideo(
        youtube_id="abc123",
        title="vt",
        channel="c",
        thumbnail_url="https://t.example",
        published_at="2026-04-01",
        search_query="vq",
        processed=False,
    )
    db_session.add_all([s, s2, v])
    db_session.commit()

    r = client.get("/api/admin/candidates")
    assert r.status_code == 200
    data = r.json()
    assert len(data["stories"]) == 1
    assert data["stories"][0]["url"] == "https://u1.example"
    assert len(data["videos"]) == 1
    assert data["videos"][0]["youtube_id"] == "abc123"


@patch("app.routers.admin.collect_candidates")
def test_trigger_collect(mock_collect, client):
    mock_collect.return_value = {"stories_added": 2, "videos_added": 1}
    r = client.post("/api/admin/collect")
    assert r.status_code == 200
    assert r.json() == {"stories_added": 2, "videos_added": 1}
    mock_collect.assert_called_once()


@patch("app.routers.admin.publish_issue")
def test_trigger_publish(mock_publish, client):
    mock_publish.return_value = {"status": "published", "issue_id": 1}
    r = client.post("/api/admin/publish")
    assert r.status_code == 200
    assert r.json()["status"] == "published"
    mock_publish.assert_called_once()
