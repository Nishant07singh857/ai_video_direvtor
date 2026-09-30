import uuid
from datetime import datetime, UTC
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import ForeignKey, String, Enum, Text, DateTime, func, JSON, Float, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StoryStatus(str, PyEnum):
    GENERATED = "generated"
    RANKED = "ranked"
    SELECTED = "selected"
    DISCARDED = "discarded"


class StoryShotRole(str, PyEnum):
    HOOK = "hook"
    DEVELOPMENT = "development"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    B_ROLL = "b_roll"


class TimelineStatus(str, PyEnum):
    DRAFT = "draft"
    RENDERED = "rendered"
    EXPORTED = "exported"


class KnowledgeNodeType(str, PyEnum):
    SHOT = "shot"
    SCENE = "scene"
    ENTITY = "entity"
    THEME = "theme"
    PERSON = "person"
    LOCATION = "location"
    AUDIO_EVENT = "audio_event"


class KnowledgeEdgeType(str, PyEnum):
    TEMPORAL = "temporal"
    VISUAL_SIMILARITY = "visual_similarity"
    SAME_PERSON = "same_person"
    SAME_LOCATION = "same_location"
    CAUSAL = "causal"
    THEMATIC = "thematic"


class StoryCandidate(Base):
    __tablename__ = "story_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    narrative_arc: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    estimated_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[StoryStatus] = mapped_column(
        Enum(StoryStatus), default=StoryStatus.GENERATED, nullable=False)
    source_analysis_job_ids: Mapped[Optional[List[uuid.UUID]]] = mapped_column(
        JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    shots: Mapped[List["StoryShot"]] = relationship(
        "StoryShot", back_populates="story_candidate", cascade="all, delete-orphan"
    )
    timeline: Mapped[Optional["Timeline"]] = relationship(
        "Timeline", back_populates="story_candidate", uselist=False
    )
    shot_rankings: Mapped[List["ShotRanking"]] = relationship(
        "ShotRanking", back_populates="story_candidate", cascade="all, delete-orphan"
    )


class StoryShot(Base):
    __tablename__ = "story_shots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    story_candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("story_candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_shot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video_shots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    role: Mapped[StoryShotRole] = mapped_column(Enum(StoryShotRole), nullable=False)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    story_candidate: Mapped["StoryCandidate"] = relationship("StoryCandidate", back_populates="shots")
    video_shot: Mapped["VideoShot"] = relationship("VideoShot")


class Timeline(Base):
    __tablename__ = "timelines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    story_candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("story_candidates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timeline_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    total_duration: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[TimelineStatus] = mapped_column(
        Enum(TimelineStatus), default=TimelineStatus.DRAFT, nullable=False)
    render_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    story_candidate: Mapped[Optional["StoryCandidate"]] = relationship(
        "StoryCandidate", back_populates="timeline"
    )


class ShotRanking(Base):
    __tablename__ = "shot_rankings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    story_candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("story_candidates.id", ondelete="CASCADE"), nullable=True, index=True
    )
    video_shot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video_shots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    visual_appeal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    audio_appeal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    composite_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    story_candidate: Mapped[Optional["StoryCandidate"]] = relationship("StoryCandidate", back_populates="shot_rankings")
    video_shot: Mapped["VideoShot"] = relationship("VideoShot")


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_type: Mapped[KnowledgeNodeType] = mapped_column(Enum(KnowledgeNodeType), nullable=False)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    properties: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    outgoing_edges: Mapped[List["KnowledgeEdge"]] = relationship(
        "KnowledgeEdge",
        foreign_keys="KnowledgeEdge.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[List["KnowledgeEdge"]] = relationship(
        "KnowledgeEdge",
        foreign_keys="KnowledgeEdge.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )


class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    edge_type: Mapped[KnowledgeEdgeType] = mapped_column(Enum(KnowledgeEdgeType), nullable=False)
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    properties: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    source_node: Mapped["KnowledgeNode"] = relationship(
        "KnowledgeNode", foreign_keys=[source_node_id], back_populates="outgoing_edges"
    )
    target_node: Mapped["KnowledgeNode"] = relationship(
        "KnowledgeNode", foreign_keys=[target_node_id], back_populates="incoming_edges"
    )


# Add indexes
Index("ix_story_candidates_project", StoryCandidate.project_id)
Index("ix_story_candidates_status", StoryCandidate.status)
Index("ix_story_shots_story_candidate", StoryShot.story_candidate_id)
Index("ix_story_shots_video_shot", StoryShot.video_shot_id)
Index("ix_story_shots_sequence", StoryShot.story_candidate_id, StoryShot.sequence_order)
Index("ix_timelines_project", Timeline.project_id)
Index("ix_timelines_story_candidate", Timeline.story_candidate_id)
Index("ix_timelines_version", Timeline.project_id, Timeline.version_number)
Index("ix_shot_rankings_project", ShotRanking.project_id)
Index("ix_shot_rankings_story_candidate", ShotRanking.story_candidate_id)
Index("ix_shot_rankings_video_shot", ShotRanking.video_shot_id)
Index("ix_shot_rankings_rank", ShotRanking.rank)
Index("ix_knowledge_nodes_project", KnowledgeNode.project_id)
Index("ix_knowledge_nodes_type", KnowledgeNode.node_type)
Index("ix_knowledge_nodes_source", KnowledgeNode.source_id)
Index("ix_knowledge_edges_project", KnowledgeEdge.project_id)
Index("ix_knowledge_edges_source", KnowledgeEdge.source_node_id)
Index("ix_knowledge_edges_target", KnowledgeEdge.target_node_id)
Index("ix_knowledge_edges_type", KnowledgeEdge.edge_type)