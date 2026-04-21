from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from .database import Base


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    week_of = Column(String, nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())

    stories = relationship("Story", back_populates="issue", cascade="all, delete-orphan")
    featured_videos = relationship(
        "FeaturedVideo", back_populates="issue", cascade="all, delete-orphan"
    )


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    bullet_points = Column(JSON, nullable=True)
    source = Column(String, nullable=False)
    url = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    date = Column(String, nullable=False)
    tags = Column(JSON, nullable=True)
    display_order = Column(Integer, nullable=False)

    issue = relationship("Issue", back_populates="stories")


class FeaturedVideo(Base):
    __tablename__ = "featured_videos"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    title = Column(String, nullable=False)
    video_url = Column(String, nullable=False)
    thumbnail_url = Column(String, nullable=False)
    description = Column(String, nullable=True)

    issue = relationship("Issue", back_populates="featured_videos")


class CandidateStory(Base):
    __tablename__ = "candidate_stories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    source = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    image_url = Column(String, nullable=True)
    date = Column(String, nullable=False)
    tavily_score = Column(Float, nullable=True)
    importance_score = Column(Float, nullable=True)
    search_query = Column(String, nullable=False)
    collected_at = Column(DateTime, default=func.now())
    processed = Column(Boolean, default=False)


class CandidateVideo(Base):
    __tablename__ = "candidate_videos"

    id = Column(Integer, primary_key=True, index=True)
    youtube_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    thumbnail_url = Column(String, nullable=False)
    description = Column(String, nullable=True)
    published_at = Column(String, nullable=False)
    view_count = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    like_count = Column(Integer, nullable=True)
    comment_count = Column(Integer, nullable=True)
    engagement_rate = Column(Float, nullable=True)
    view_velocity = Column(Float, nullable=True)
    transcript_excerpt = Column(Text, nullable=True)
    content_type = Column(String, nullable=True)
    importance_score = Column(Float, nullable=True)
    search_query = Column(String, nullable=False)
    collected_at = Column(DateTime, default=func.now())
    processed = Column(Boolean, default=False)


class ChannelReputation(Base):
    __tablename__ = "channel_reputations"

    id = Column(Integer, primary_key=True, index=True)
    channel_name = Column(String, unique=True, nullable=False)
    times_seen = Column(Integer, default=0)
    times_selected = Column(Integer, default=0)
    avg_importance_score = Column(Float, default=0.0)
    quality_tier = Column(String, default="unknown")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class DevPost(Base):
    """HN + GitHub rows for the /api/devs/posts feed."""

    __tablename__ = "dev_posts"

    # Common
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, index=True)  # "hn" | "github"
    url = Column(String, unique=True, nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    collected_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    title = Column(String, nullable=False)

    # Ranking / publish state
    importance_score = Column(Float, nullable=True)
    rank_score = Column(Float, nullable=True)
    rank_features = Column(JSON, nullable=True)
    topics = Column(JSON, nullable=True)  # list[str]
    is_active = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, nullable=True)

    # HN-only
    hn_url = Column(String, nullable=True)
    points = Column(Integer, nullable=True)
    comments = Column(Integer, nullable=True)
    bullets = Column(JSON, nullable=True)  # list[str]
    top_comment_excerpt = Column(Text, nullable=True)

    # GitHub-only
    repo = Column(String, nullable=True)
    version = Column(String, nullable=True)
    release_bullets = Column(JSON, nullable=True)  # list[str]
    release_notes_excerpt = Column(Text, nullable=True)
    why_it_matters = Column(Text, nullable=True)
    has_breaking_changes = Column(Boolean, nullable=True)
    stars = Column(Integer, nullable=True)
    stars_velocity_7d = Column(Integer, nullable=True)


class CandidateXTweet(Base):
    """Raw tweets pulled pre-synthesis for the X pipeline."""

    __tablename__ = "candidate_x_tweets"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, nullable=False)
    author_handle = Column(String, nullable=False, index=True)
    author_name = Column(String, nullable=True)
    author_avatar_url = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    likes = Column(Integer, nullable=True)
    reposts = Column(Integer, nullable=True)
    replies = Column(Integer, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    collected_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    quality_score = Column(Float, nullable=True)
    topic_cluster = Column(String, nullable=True)
    used_in_digest_id = Column(
        Integer, ForeignKey("x_topic_digests.id"), nullable=True
    )


class XTopicDigestRow(Base):
    """Synthesized X output — one row per published topic digest."""

    __tablename__ = "x_topic_digests"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, nullable=False)
    # list[{text, sources: [{url, author_handle, author_name}]}]
    bullets = Column(JSON, nullable=False)
    rank_score = Column(Float, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class RepoStarSnapshot(Base):
    """Periodic star counts per repo, for GitHub velocity calculation."""

    __tablename__ = "repo_star_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    repo = Column(String, nullable=False, index=True)
    stars = Column(Integer, nullable=False)
    observed_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class DiscoveredHandle(Base):
    """X handles surfaced by the weekly discovery pass."""

    __tablename__ = "discovered_handles"

    id = Column(Integer, primary_key=True, index=True)
    handle = Column(String, unique=True, nullable=False)
    first_seen_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    seed_engagement_count = Column(Integer, default=0, nullable=False)
    seed_handles = Column(JSON, nullable=True)  # list[str]
    status = Column(
        String, default="pending", nullable=False
    )  # "pending" | "added" | "ignored"
