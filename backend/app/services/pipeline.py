import logging
from datetime import date

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import CandidateStory, CandidateVideo, FeaturedVideo, Issue, Story
from .ranker import generate_title, rank_stories, rank_videos
from .tavily_search import search_news
from .youtube_search import search_videos

logger = logging.getLogger(__name__)


def collect_candidates(db: Session | None = None) -> dict:
    """Daily job: search Tavily + YouTube, store candidates."""
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        news_count = search_news(db)
        video_count = search_videos(db)
        logger.info("Collection complete — %d stories, %d videos", news_count, video_count)
        return {"stories_added": news_count, "videos_added": video_count}
    finally:
        if own_session:
            db.close()


def publish_issue(db: Session | None = None) -> dict:
    """Weekly job: rank unprocessed candidates, create Issue with top 5 stories + top 3 videos."""
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        story_candidates = (
            db.query(CandidateStory)
            .filter(CandidateStory.processed == False)  # noqa: E712
            .all()
        )
        video_candidates = (
            db.query(CandidateVideo)
            .filter(CandidateVideo.processed == False)  # noqa: E712
            .all()
        )

        if not story_candidates:
            logger.warning("No unprocessed story candidates — skipping publish")
            return {"status": "skipped", "reason": "no story candidates"}

        story_dicts = [
            {
                "id": s.id,
                "title": s.title,
                "summary": s.summary,
                "source": s.source,
                "url": s.url,
                "image_url": s.image_url,
                "date": s.date,
                "tavily_score": s.tavily_score,
            }
            for s in story_candidates
        ]
        scored_stories = rank_stories(story_dicts)
        scored_stories.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_story_ids = [s["id"] for s in scored_stories[:5]]

        for sc in scored_stories:
            cand = db.query(CandidateStory).get(sc["id"])
            if cand:
                cand.importance_score = sc.get("score", 0)

        video_dicts = [
            {
                "id": v.id,
                "title": v.title,
                "channel": v.channel,
                "description": v.description,
                "youtube_id": v.youtube_id,
                "thumbnail_url": v.thumbnail_url,
            }
            for v in video_candidates
        ]
        scored_videos = rank_videos(video_dicts) if video_dicts else []
        scored_videos.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_video_ids = [v["id"] for v in scored_videos[:3]]

        for sv in scored_videos:
            cand = db.query(CandidateVideo).get(sv["id"])
            if cand:
                cand.importance_score = sv.get("score", 0)

        top_stories_data = [s for s in story_dicts if s["id"] in top_story_ids]
        title = generate_title(top_stories_data)
        week_of = date.today().isoformat()

        issue = Issue(week_of=week_of, title=title)
        db.add(issue)
        db.flush()

        for order, sid in enumerate(top_story_ids, start=1):
            cand = db.query(CandidateStory).get(sid)
            if not cand:
                continue
            story = Story(
                issue_id=issue.id,
                title=cand.title,
                summary=cand.summary,
                source=cand.source,
                url=cand.url,
                image_url=cand.image_url,
                date=cand.date,
                tags=None,
                display_order=order,
            )
            db.add(story)

        for vid in top_video_ids:
            cand = db.query(CandidateVideo).get(vid)
            if not cand:
                continue
            video = FeaturedVideo(
                issue_id=issue.id,
                title=cand.title,
                video_url=f"https://www.youtube.com/watch?v={cand.youtube_id}",
                thumbnail_url=cand.thumbnail_url,
                description=cand.description,
            )
            db.add(video)

        for c in story_candidates:
            c.processed = True
        for c in video_candidates:
            c.processed = True

        db.commit()
        logger.info("Published issue %d: '%s' with %d stories, %d videos", issue.id, title, len(top_story_ids), len(top_video_ids))
        return {
            "status": "published",
            "issue_id": issue.id,
            "title": title,
            "stories": len(top_story_ids),
            "videos": len(top_video_ids),
        }
    finally:
        if own_session:
            db.close()
