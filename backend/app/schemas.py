from pydantic import BaseModel, model_validator


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
    importance_score: float | None = None
    search_query: str
    processed: bool

    model_config = {"from_attributes": True}
