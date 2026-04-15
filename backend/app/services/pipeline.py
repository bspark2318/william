import logging
import math
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..config import (
    HEURISTIC_REJECT_BOTTOM_PCT,
    IDEAL_VIDEO_DURATION_MAX,
    IDEAL_VIDEO_DURATION_MIN,
    RETENTION_DAYS,
    VIDEO_FINALISTS,
    VIDEO_PUBLISH_LOOKBACK_DAYS,
)
from ..database import SessionLocal
from ..models import (
    CandidateStory,
    CandidateVideo,
    ChannelReputation,
    FeaturedVideo,
    Issue,
    Story,
)
from .ranker import (
    classify_video_content,
    comparative_select_stories,
    comparative_select_videos,
    generate_title,
    quick_rank_stories,
    quick_rank_videos,
    tight_bullets,
)
from .tavily_search import search_news
from .youtube_search import search_videos

logger = logging.getLogger(__name__)

_JACCARD_THRESHOLD = 0.5
_STORY_FINALISTS = 12
_MIN_TAVILY_SCORE = 0.3


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _title_words(title: str) -> set[str]:
    return set(title.strip().lower().split())


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _dedup_stories(candidates: list) -> tuple[list, list]:
    """Cluster stories by title similarity. Returns (survivors, rejects)."""
    if not candidates:
        return [], []

    by_score = sorted(candidates, key=lambda s: s.tavily_score or 0, reverse=True)
    survivors: list = []
    rejects: list = []
    survivor_words: list[set[str]] = []

    for cand in by_score:
        words = _title_words(cand.title)
        is_dup = any(_jaccard(words, sw) >= _JACCARD_THRESHOLD for sw in survivor_words)
        if is_dup:
            rejects.append(cand)
        else:
            survivors.append(cand)
            survivor_words.append(words)

    if rejects:
        logger.info("Dedup: %d stories survived, %d duplicates rejected", len(survivors), len(rejects))
    return survivors, rejects


def _dedup_videos(candidates: list) -> tuple[list, list]:
    """Cluster videos by title similarity. Returns (survivors, rejects)."""
    if not candidates:
        return [], []

    by_views = sorted(candidates, key=lambda v: v.view_count or 0, reverse=True)
    survivors: list = []
    rejects: list = []
    survivor_words: list[set[str]] = []

    for cand in by_views:
        words = _title_words(cand.title)
        is_dup = any(_jaccard(words, sw) >= _JACCARD_THRESHOLD for sw in survivor_words)
        if is_dup:
            rejects.append(cand)
        else:
            survivors.append(cand)
            survivor_words.append(words)

    if rejects:
        logger.info("Dedup: %d videos survived, %d duplicates rejected", len(survivors), len(rejects))
    return survivors, rejects


# ---------------------------------------------------------------------------
# Heuristic pre-filter
# ---------------------------------------------------------------------------

def _heuristic_filter_stories(candidates: list) -> tuple[list, list]:
    """Filter stories by tavily_score. Returns (survivors, rejects)."""
    above_min = [c for c in candidates if (c.tavily_score or 0) >= _MIN_TAVILY_SCORE]
    below_min = [c for c in candidates if (c.tavily_score or 0) < _MIN_TAVILY_SCORE]

    above_min.sort(key=lambda s: s.tavily_score or 0, reverse=True)
    cutoff = max(len(above_min) // 2, 1)
    survivors = above_min[:cutoff]
    rejects = above_min[cutoff:] + below_min

    logger.info(
        "Heuristic filter: %d story survivors, %d rejected (min tavily=%.2f)",
        len(survivors), len(rejects), _MIN_TAVILY_SCORE,
    )
    return survivors, rejects


def _duration_preference(seconds: int) -> float:
    """Bell-curve score favouring IDEAL_VIDEO_DURATION_MIN..MAX range."""
    if seconds <= 0:
        return 0.0
    lo, hi = IDEAL_VIDEO_DURATION_MIN, IDEAL_VIDEO_DURATION_MAX
    mid = (lo + hi) / 2
    if lo <= seconds <= hi:
        return 10.0
    dist = min(abs(seconds - lo), abs(seconds - hi))
    return max(10.0 * math.exp(-((dist / mid) ** 2)), 0.5)


def _freshness_decay(published_at: str) -> float:
    """Linear decay: 10 for just-published, 0 at 7+ days old."""
    try:
        pub = datetime.fromisoformat(published_at + "T00:00:00+00:00")
        hours = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
    except Exception:
        hours = 168.0
    return max(10.0 * (1.0 - hours / 168.0), 0.0)


_TIER_SCORES = {"top": 10, "good": 7, "mid": 5, "low": 2, "unknown": 4}


def _compute_video_heuristic(v, channel_tier: str) -> float:
    """Weighted composite score across multiple signals (0-10 scale)."""
    velocity_score = min((v.view_velocity or 0) / 500, 10.0)
    engagement_score = min((v.engagement_rate or 0) * 1000, 10.0)
    views_score = min((v.view_count or 0) / 100_000, 10.0)
    dur_score = _duration_preference(v.duration_seconds or 0)
    ch_score = _TIER_SCORES.get(channel_tier, 4)
    fresh_score = _freshness_decay(v.published_at or "")

    return (
        velocity_score * 0.25
        + engagement_score * 0.20
        + views_score * 0.10
        + dur_score * 0.10
        + ch_score * 0.20
        + fresh_score * 0.15
    )


def _heuristic_filter_videos(
    candidates: list, channel_tiers: dict[str, str]
) -> tuple[list, list]:
    """Multi-signal heuristic filter. Returns (survivors, rejects)."""
    if not candidates:
        return [], []

    scored = [
        (c, _compute_video_heuristic(c, channel_tiers.get(c.channel, "unknown")))
        for c in candidates
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    reject_count = max(int(len(scored) * HEURISTIC_REJECT_BOTTOM_PCT / 100), 0)
    cutoff = len(scored) - reject_count
    cutoff = max(cutoff, 1)

    survivors = [s[0] for s in scored[:cutoff]]
    rejects = [s[0] for s in scored[cutoff:]]

    logger.info(
        "Heuristic filter: %d video survivors, %d rejected (bottom %d%%)",
        len(survivors), len(rejects), HEURISTIC_REJECT_BOTTOM_PCT,
    )
    return survivors, rejects


# ---------------------------------------------------------------------------
# Channel reputation helpers
# ---------------------------------------------------------------------------

def _get_channel_tiers(db: Session, channels: list[str]) -> dict[str, str]:
    """Look up quality_tier for a list of channel names."""
    if not channels:
        return {}
    reps = (
        db.query(ChannelReputation)
        .filter(ChannelReputation.channel_name.in_(channels))
        .all()
    )
    return {r.channel_name: r.quality_tier for r in reps}


def _recompute_tier(rep: ChannelReputation) -> str:
    seen = rep.times_seen or 0
    selected = rep.times_selected or 0
    avg = rep.avg_importance_score or 0.0

    if selected >= 3 and avg >= 7.0:
        return "top"
    if selected >= 1 and avg >= 5.0:
        return "good"
    if seen >= 3 and avg >= 3.0:
        return "mid"
    if seen >= 5 and (selected == 0 or avg < 3.0):
        return "low"
    return "unknown"


def _update_channel_seen(db: Session, channel: str, score: float) -> None:
    """Upsert channel reputation after scoring a video."""
    rep = (
        db.query(ChannelReputation)
        .filter(ChannelReputation.channel_name == channel)
        .first()
    )
    if rep is None:
        rep = ChannelReputation(
            channel_name=channel,
            times_seen=1,
            avg_importance_score=score,
        )
        db.add(rep)
    else:
        total = rep.avg_importance_score * rep.times_seen + score
        rep.times_seen += 1
        rep.avg_importance_score = total / rep.times_seen
    rep.quality_tier = _recompute_tier(rep)


def _update_channel_selected(db: Session, channel: str) -> None:
    """Increment times_selected when a video is published."""
    rep = (
        db.query(ChannelReputation)
        .filter(ChannelReputation.channel_name == channel)
        .first()
    )
    if rep is None:
        rep = ChannelReputation(
            channel_name=channel, times_seen=1, times_selected=1
        )
        db.add(rep)
    else:
        rep.times_selected += 1
    rep.quality_tier = _recompute_tier(rep)


# ---------------------------------------------------------------------------
# Stage 1 — score unscored candidates (called during daily collect)
# ---------------------------------------------------------------------------

def _score_unscored(db: Session) -> None:
    """Dedup + heuristic filter + title-only LLM scoring for today's candidates."""
    unscored_stories = (
        db.query(CandidateStory)
        .filter(CandidateStory.importance_score.is_(None))
        .all()
    )
    unscored_videos = (
        db.query(CandidateVideo)
        .filter(CandidateVideo.importance_score.is_(None))
        .all()
    )

    if not unscored_stories and not unscored_videos:
        return

    # --- Stories ---
    if unscored_stories:
        story_survivors, story_rejects = _dedup_stories(unscored_stories)
        for r in story_rejects:
            r.importance_score = 0.0

        story_survivors, more_rejects = _heuristic_filter_stories(story_survivors)
        for r in more_rejects:
            r.importance_score = 0.0

        if story_survivors:
            dicts = [{"id": s.id, "title": s.title, "source": s.source, "tavily_score": s.tavily_score} for s in story_survivors]
            try:
                scored = quick_rank_stories(dicts)
                score_map = {s["id"]: s.get("score", 5.0) for s in scored}
                for s in story_survivors:
                    s.importance_score = score_map.get(s.id, 5.0)
                logger.info("Scored %d stories via LLM", len(story_survivors))
            except Exception:
                logger.exception("LLM story scoring failed — using tavily_score fallback")
                for s in story_survivors:
                    s.importance_score = (s.tavily_score or 0) * 10

    # --- Videos ---
    if unscored_videos:
        video_survivors, video_rejects = _dedup_videos(unscored_videos)
        for r in video_rejects:
            r.importance_score = 0.0

        # Classify content types before heuristic filtering
        if video_survivors:
            classify_dicts = [
                {
                    "id": v.id,
                    "title": v.title,
                    "channel": v.channel,
                    "description": v.description,
                    "transcript_excerpt": v.transcript_excerpt,
                }
                for v in video_survivors
            ]
            try:
                classified = classify_video_content(classify_dicts)
                type_map = {c["id"]: c.get("content_type", "other") for c in classified}
                for v in video_survivors:
                    v.content_type = type_map.get(v.id, "other")
            except Exception:
                logger.exception("Content classification failed — defaulting to 'other'")
                for v in video_survivors:
                    v.content_type = "other"

        channels = list({v.channel for v in video_survivors})
        channel_tiers = _get_channel_tiers(db, channels)

        video_survivors, more_rejects = _heuristic_filter_videos(
            video_survivors, channel_tiers
        )
        for r in more_rejects:
            r.importance_score = 0.0

        if video_survivors:
            dicts = [
                {
                    "id": v.id,
                    "title": v.title,
                    "channel": v.channel,
                    "description": v.description,
                    "view_count": v.view_count,
                    "duration_seconds": v.duration_seconds,
                    "view_velocity": v.view_velocity,
                    "engagement_rate": v.engagement_rate,
                    "channel_tier": channel_tiers.get(v.channel, "unknown"),
                    "content_type": v.content_type,
                }
                for v in video_survivors
            ]
            try:
                scored = quick_rank_videos(dicts)
                score_map = {v["id"]: v.get("score", 5.0) for v in scored}
                for v in video_survivors:
                    v.importance_score = score_map.get(v.id, 5.0)
                    _update_channel_seen(db, v.channel, v.importance_score)
                logger.info("Scored %d videos via LLM", len(video_survivors))
            except Exception:
                logger.exception("LLM video scoring failed — using view_count fallback")
                for v in video_survivors:
                    v.importance_score = min((v.view_count or 0) / 10000, 10.0)
                    _update_channel_seen(db, v.channel, v.importance_score)

    db.commit()


# ---------------------------------------------------------------------------
# Finalist diversification
# ---------------------------------------------------------------------------

def _diversify_story_finalists(candidates: list, n: int) -> list:
    """Pick up to `n` finalists with topic diversity.

    Groups candidates by search_query and round-robins across groups
    (each sorted by importance_score descending) so every query category
    contributes to the finalist pool rather than one hot topic dominating.
    """
    from collections import defaultdict

    groups: dict[str, list] = defaultdict(list)
    for c in candidates:
        key = c.search_query or "unknown"
        groups[key].append(c)

    for g in groups.values():
        g.sort(key=lambda s: s.importance_score or 0, reverse=True)

    # Lead with the group whose best story scored highest
    ordered_groups = sorted(
        groups.values(), key=lambda g: g[0].importance_score or 0, reverse=True
    )

    result: list = []
    i = 0
    while len(result) < n:
        added_any = False
        for group in ordered_groups:
            if i < len(group):
                result.append(group[i])
                added_any = True
                if len(result) >= n:
                    break
        if not added_any:
            break
        i += 1
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def collect_candidates(db: Session | None = None) -> dict:
    """Daily job: search Tavily + YouTube, store candidates, dedup + score."""
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        news_count = search_news(db)
        video_count = search_videos(db)
        logger.info("Collection complete — %d stories, %d videos", news_count, video_count)
        _score_unscored(db)
        return {"stories_added": news_count, "videos_added": video_count}
    finally:
        if own_session:
            db.close()


def publish_issue(db: Session | None = None) -> dict:
    """Comparative-select from pre-scored candidates, create Issue.

    Video pool: all candidates with collected_at within VIDEO_PUBLISH_LOOKBACK_DAYS
    (rolling window), including any already featured in a prior issue — comparative
    selection may keep strong picks. CandidateVideo.processed is not used for videos.
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        window_start = datetime.now(timezone.utc) - timedelta(days=7)
        story_candidates = (
            db.query(CandidateStory)
            .filter(CandidateStory.collected_at >= window_start)
            .all()
        )
        video_cutoff = datetime.now(timezone.utc) - timedelta(days=VIDEO_PUBLISH_LOOKBACK_DAYS)
        video_candidates = (
            db.query(CandidateVideo)
            .filter(CandidateVideo.collected_at >= video_cutoff)
            .all()
        )

        if not story_candidates:
            logger.warning("No story candidates in the last 7 days — skipping publish")
            return {"status": "skipped", "reason": "no story candidates"}

        # Score any stragglers that missed daily scoring
        stragglers = [c for c in story_candidates if c.importance_score is None]
        if stragglers:
            logger.info("Scoring %d straggler stories inline", len(stragglers))
            dicts = [{"id": s.id, "title": s.title, "source": s.source, "tavily_score": s.tavily_score} for s in stragglers]
            try:
                scored = quick_rank_stories(dicts)
                score_map = {s["id"]: s.get("score", 5.0) for s in scored}
                for s in stragglers:
                    s.importance_score = score_map.get(s.id, 5.0)
            except Exception:
                logger.exception("Straggler scoring failed — using tavily_score")
                for s in stragglers:
                    s.importance_score = (s.tavily_score or 0) * 10

        video_stragglers = [c for c in video_candidates if c.importance_score is None]
        if video_stragglers:
            logger.info("Scoring %d straggler videos inline", len(video_stragglers))
            straggler_channels = list({v.channel for v in video_stragglers})
            straggler_tiers = _get_channel_tiers(db, straggler_channels)
            dicts = [
                {
                    "id": v.id,
                    "title": v.title,
                    "channel": v.channel,
                    "description": v.description,
                    "view_count": v.view_count,
                    "duration_seconds": v.duration_seconds,
                    "view_velocity": v.view_velocity,
                    "engagement_rate": v.engagement_rate,
                    "channel_tier": straggler_tiers.get(v.channel, "unknown"),
                    "content_type": v.content_type or "other",
                }
                for v in video_stragglers
            ]
            try:
                scored = quick_rank_videos(dicts)
                score_map = {v["id"]: v.get("score", 5.0) for v in scored}
                for v in video_stragglers:
                    v.importance_score = score_map.get(v.id, 5.0)
            except Exception:
                logger.exception("Straggler video scoring failed — using view_count")
                for v in video_stragglers:
                    v.importance_score = min((v.view_count or 0) / 10000, 10.0)

        # --- Comparative finals: stories ---
        story_candidates.sort(key=lambda s: s.importance_score or 0, reverse=True)
        finalists = _diversify_story_finalists(story_candidates, _STORY_FINALISTS)
        finalist_dicts = [
            {
                "id": s.id,
                "title": s.title,
                "summary": s.summary,
                "source": s.source,
                "importance_score": s.importance_score,
            }
            for s in finalists
        ]

        # Fetch titles from the 2 most recently published issues so the LLM
        # can semantically avoid repeating topics that just ran.
        recent_issues = (
            db.query(Issue)
            .order_by(Issue.created_at.desc())
            .limit(2)
            .all()
        )
        recent_titles = [s.title for iss in recent_issues for s in iss.stories]

        try:
            selections = comparative_select_stories(finalist_dicts, recent_story_titles=recent_titles)
        except Exception:
            logger.exception("Comparative story selection failed — falling back to top by score")
            selections = [{"id": s.id, "rank": i + 1, "topic": "unknown"} for i, s in enumerate(finalists[:5])]

        selections.sort(key=lambda x: x.get("rank", 99))
        top_story_ids = [s["id"] for s in selections[:5]]

        # --- Comparative finals: videos ---
        video_candidates.sort(key=lambda v: v.importance_score or 0, reverse=True)
        video_finalists = video_candidates[:VIDEO_FINALISTS]

        seen_youtube: set[str] = set()
        deduped_video_finalists = []
        for v in video_finalists:
            if v.youtube_id not in seen_youtube:
                seen_youtube.add(v.youtube_id)
                deduped_video_finalists.append(v)

        finalist_channels = list({v.channel for v in deduped_video_finalists})
        finalist_tiers = _get_channel_tiers(db, finalist_channels)

        top_video_ids: list[int] = []
        if deduped_video_finalists:
            vid_dicts = [
                {
                    "id": v.id,
                    "title": v.title,
                    "channel": v.channel,
                    "description": v.description,
                    "youtube_id": v.youtube_id,
                    "importance_score": v.importance_score,
                    "content_type": v.content_type or "other",
                    "view_velocity": v.view_velocity,
                    "engagement_rate": v.engagement_rate,
                    "duration_seconds": v.duration_seconds,
                    "channel_tier": finalist_tiers.get(v.channel, "unknown"),
                    "transcript_excerpt": v.transcript_excerpt,
                }
                for v in deduped_video_finalists
            ]
            try:
                vid_selections = comparative_select_videos(vid_dicts)
            except Exception:
                logger.exception("Comparative video selection failed — falling back to top by score")
                vid_selections = [{"id": v.id, "rank": i + 1, "topic": "unknown"} for i, v in enumerate(deduped_video_finalists[:3])]

            vid_selections.sort(key=lambda x: x.get("rank", 99))
            top_video_ids = [v["id"] for v in vid_selections[:3]]

        # --- Build Issue ---
        top_stories_data = [
            {"id": s.id, "title": s.title, "summary": s.summary, "source": s.source}
            for s in story_candidates if s.id in top_story_ids
        ]
        title = generate_title(top_stories_data).strip('"').strip("'")
        week_of = date.today().isoformat()

        issue = Issue(week_of=week_of, title=title)
        db.add(issue)
        db.flush()

        for order, sid in enumerate(top_story_ids, start=1):
            cand = db.query(CandidateStory).get(sid)
            if not cand:
                continue
            bullets = tight_bullets(cand.title, cand.summary)
            story = Story(
                issue_id=issue.id,
                title=cand.title,
                summary=" ".join(bullets) if bullets else cand.summary,
                bullet_points=bullets or None,
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
            _update_channel_selected(db, cand.channel)

        for c in story_candidates:
            c.processed = True

        db.commit()
        logger.info(
            "Published issue %d: '%s' with %d stories, %d videos",
            issue.id, title, len(top_story_ids), len(top_video_ids),
        )
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


def purge_old_data(db: Session | None = None) -> dict:
    """Delete issues and candidate rows older than RETENTION_DAYS."""
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        old_issues = db.query(Issue).filter(Issue.created_at < cutoff).all()
        for issue in old_issues:
            db.delete(issue)
        issues_deleted = len(old_issues)
        stories_deleted = db.query(CandidateStory).filter(CandidateStory.collected_at < cutoff).delete()
        videos_deleted = db.query(CandidateVideo).filter(CandidateVideo.collected_at < cutoff).delete()
        db.commit()
        logger.info(
            "Purged %d issues, %d candidate stories, %d candidate videos older than %d days",
            issues_deleted, stories_deleted, videos_deleted, RETENTION_DAYS,
        )
        return {
            "issues_deleted": issues_deleted,
            "candidate_stories_deleted": stories_deleted,
            "candidate_videos_deleted": videos_deleted,
        }
    finally:
        if own_session:
            db.close()
