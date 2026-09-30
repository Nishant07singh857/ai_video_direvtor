import uuid
from datetime import datetime, UTC
from typing import Optional, List

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    media_assets: Mapped[List["MediaAsset"]] = relationship(
        "MediaAsset", back_populates="project", cascade="all, delete-orphan"
    )
    story_candidates: Mapped[List["StoryCandidate"]] = relationship(
        "StoryCandidate", back_populates="project", cascade="all, delete-orphan"
    )
    timelines: Mapped[List["Timeline"]] = relationship(
        "Timeline", back_populates="project", cascade="all, delete-orphan"
    )
    shot_rankings: Mapped[List["ShotRanking"]] = relationship(
        "ShotRanking", back_populates="project", cascade="all, delete-orphan"
    )
    knowledge_nodes: Mapped[List["KnowledgeNode"]] = relationship(
        "KnowledgeNode", back_populates="project", cascade="all, delete-orphan"
    )
    knowledge_edges: Mapped[List["KnowledgeEdge"]] = relationship(
        "KnowledgeEdge", back_populates="project", cascade="all, delete-orphan"
    )
