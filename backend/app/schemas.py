from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_serializer, model_validator  # noqa: F401


class StoryOut(BaseModel):
    id: int
    title: str
    summary: str
    bullet_points: list[str] | None = None
    source: str
    url: str
    image_url: str | None = None
    date: str
    tags: list[str] | None = None
    display_order: int

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def default_bullet_points(self):
        if self.bullet_points:
            return self
        return self.model_copy(
            update={"bullet_points": [self.summary] if self.summary.strip() else []}
        )


class FeaturedVideoOut(BaseModel):
    id: int
    title: str
    video_url: str
    thumbnail_url: str
    description: str | None = None

    model_config = {"from_attributes": True}


class IssueListItemOut(BaseModel):
    id: int
    week_of: str
    title: str
    edition: int

    model_config = {"from_attributes": True}


class IssueOut(BaseModel):
    id: int
    week_of: str
    title: str
    edition: int
    stories: list[StoryOut]
    featured_video: FeaturedVideoOut | None = None
    featured_videos: list[FeaturedVideoOut]

    model_config = {"from_attributes": True}


class CandidateStoryOut(BaseModel):
    id: int
    title: str
    summary: str
    source: str
    url: str
    image_url: str | None = None
    date: str
    tavily_score: float | None = None
    importance_score: float | None = None
    search_query: str
    processed: bool

    model_config = {"from_attributes": True}


class CandidateVideoOut(BaseModel):
    id: int
    youtube_id: str
    title: str
    channel: str
    thumbnail_url: str
    description: str | None = None
    published_at: str
    view_count: int | None = None
    duration_seconds: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    engagement_rate: float | None = None
    view_velocity: float | None = None
    content_type: str | None = None
    importance_score: float | None = None
    search_query: str
    processed: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# /api/devs/posts — discriminated-union response models
# ---------------------------------------------------------------------------


class HNPostOut(BaseModel):
    """Served shape for an HN post row."""

    source: Literal["hn"] = "hn"
    id: int
    rank_score: float | None = None
    display_order: int
    url: str
    published_at: datetime
    title: str
    hn_url: str
    points: int
    comments: int
    bullets: list[str] | None = None
    top_comment_excerpt: str | None = None
    topics: list[str] | None = None

    model_config = {"from_attributes": True}

    @field_serializer("published_at")
    def _serialize_published_at(self, value: datetime) -> str:
        return value.isoformat()


class GitHubPostOut(BaseModel):
    """Served shape for a GitHub release / trending row."""

    source: Literal["github"] = "github"
    id: int
    rank_score: float | None = None
    display_order: int
    url: str
    published_at: datetime
    repo: str
    title: str
    version: str | None = None
    release_bullets: list[str] | None = None
    release_notes_excerpt: str | None = None
    why_it_matters: str | None = None
    has_breaking_changes: bool | None = None
    stars: int | None = None
    stars_velocity_7d: int | None = None
    topics: list[str] | None = None

    model_config = {"from_attributes": True}

    @field_serializer("published_at")
    def _serialize_published_at(self, value: datetime) -> str:
        return value.isoformat()


DevPostOut = Annotated[
    Union[HNPostOut, GitHubPostOut],
    Field(discriminator="source"),
]
