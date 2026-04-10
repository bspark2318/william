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
    importance_score = Column(Float, nullable=True)
    search_query = Column(String, nullable=False)
    collected_at = Column(DateTime, default=func.now())
    processed = Column(Boolean, default=False)
