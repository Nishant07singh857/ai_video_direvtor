import uuid
from datetime import datetime, UTC
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import ForeignKey, String, Enum, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MediaStatus(str, PyEnum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class MediaType(str, PyEnum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False, default=MediaType.VIDEO)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Video metadata (nullable for non-video)
    duration: Mapped[Optional[float]] = mapped_column(nullable=True)
    width: Mapped[Optional[int]] = mapped_column(nullable=True)
    height: Mapped[Optional[int]] = mapped_column(nullable=True)
    fps: Mapped[Optional[float]] = mapped_column(nullable=True)
    video_codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    audio_codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bitrate: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    status: Mapped[MediaStatus] = mapped_column(Enum(MediaStatus), default=MediaStatus.UPLOADING, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="media_assets")
    shots: Mapped[List["VideoShot"]] = relationship(
        "VideoShot", back_populates="media_asset", cascade="all, delete-orphan"
    )
    scenes: Mapped[List["VideoScene"]] = relationship(
        "VideoScene", back_populates="media_asset", cascade="all, delete-orphan"
    )
    keyframes: Mapped[List["Keyframe"]] = relationship(
        "Keyframe", back_populates="media_asset", cascade="all, delete-orphan"
    )
    transcript_segments: Mapped[List["TranscriptSegment"]] = relationship(
        "TranscriptSegment", back_populates="media_asset", cascade="all, delete-orphan"
    )
    audio_analysis: Mapped[Optional["AudioAnalysis"]] = relationship(
        "AudioAnalysis", back_populates="media_asset", cascade="all, delete-orphan"
    )
    analysis_jobs: Mapped[List["AnalysisJob"]] = relationship(
        "AnalysisJob", back_populates="media_asset", cascade="all, delete-orphan"
    )
    bins: Mapped[List["MediaBin"]] = relationship(
        "MediaBin", secondary="media_bin_assets", back_populates="assets"
    )
    markers: Mapped[List["MediaMarker"]] = relationship(
        "MediaMarker", back_populates="asset", cascade="all, delete-orphan"
    )
    tags: Mapped[List["MediaTag"]] = relationship(
        "MediaTag", secondary="media_asset_tags", back_populates="assets"
    )