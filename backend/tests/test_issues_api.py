from app.models import FeaturedVideo, Issue, Story


def test_list_issues_empty(client):
    r = client.get("/api/issues")
    assert r.status_code == 200
    assert r.json() == []


def test_get_issue_not_found(client):
    r = client.get("/api/issues/999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Issue not found"


def test_list_and_get_issue(client, db_session):
    issue = Issue(week_of="2026-04-07", title="Test Week")
    db_session.add(issue)
    db_session.flush()
    db_session.add_all(
        [
            Story(
                issue_id=issue.id,
                title="S1",
                summary="Sum",
                source="src",
                url="https://a.example",
                date="2026-04-08",
                display_order=1,
            ),
            FeaturedVideo(
                issue_id=issue.id,
                title="V1",
                video_url="https://youtube.com/watch?v=x",
                thumbnail_url="https://img.example/t.jpg",
            ),
        ]
    )
    db_session.commit()

    listed = client.get("/api/issues")
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["week_of"] == "2026-04-07"
    assert body[0]["title"] == "Test Week"
    assert body[0]["edition"] == 1

    detail = client.get(f"/api/issues/{issue.id}")
    assert detail.status_code == 200
    d = detail.json()
    assert d["title"] == "Test Week"
    assert d["edition"] == 1
    assert len(d["stories"]) == 1
    assert d["stories"][0]["title"] == "S1"
    assert len(d["featured_videos"]) == 1
    assert d["featured_videos"][0]["title"] == "V1"
