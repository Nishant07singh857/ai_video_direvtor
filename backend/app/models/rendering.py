import uuid
from datetime import datetime, UTC
from typing import Optional
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func, Integer, Index, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RenderJobType(str, PyEnum):
    PREVIEW = "preview"
    EXPORT = "export"


class RenderJobStatus(str, PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RenderPresetPlatform(str, PyEnum):
    GENERIC = "generic"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    SHORTS = "shorts"
    REELS = "reels"
    CUSTOM = "custom"


class RenderJob(Base):
    __tablename__ = "render_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timeline_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timelines.id", ondelete="SET NULL"), nullable=True, index=True
    )
    job_type: Mapped[RenderJobType] = mapped_column(
        Enum(RenderJobType), nullable=False
    )
    preset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("render_presets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[RenderJobStatus] = mapped_column(
        Enum(RenderJobStatus), default=RenderJobStatus.QUEUED, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    output_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ffmpeg_cmd: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # seconds
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bitrate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    timeline: Mapped[Optional["Timeline"]] = relationship("Timeline")
    preset: Mapped[Optional["RenderPreset"]] = relationship("RenderPreset", back_populates="render_jobs")


class RenderPreset(Base):
    __tablename__ = "render_presets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    platform: Mapped[RenderPresetPlatform] = mapped_column(
        Enum(RenderPresetPlatform), default=RenderPresetPlatform.GENERIC, nullable=False
    )
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    fps: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    video_codec: Mapped[str] = mapped_column(String(30), default="libx264", nullable=False)
    video_bitrate: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g., "8M"
    crf: Mapped[int] = mapped_column(Integer, default=23, nullable=False)
    preset: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    audio_codec: Mapped[str] = mapped_column(String(20), default="aac", nullable=False)
    audio_bitrate: Mapped[str] = mapped_column(String(10), default="128k", nullable=False)
    pixel_format: Mapped[str] = mapped_column(String(20), default="yuv420p", nullable=False)
    container: Mapped[str] = mapped_column(String(20), default="mp4", nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    render_jobs: Mapped[list["RenderJob"]] = relationship("RenderJob", back_populates="preset")


class ProxyStatus(str, PyEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ProxyMedia(Base):
    __tablename__ = "proxy_media"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    resolution: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "720p", "360p"
    status: Mapped[ProxyStatus] = mapped_column(
        Enum(ProxyStatus), default=ProxyStatus.QUEUED, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class RenderCache(Base):
    __tablename__ = "render_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timeline_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timelines.id", ondelete="CASCADE"), nullable=True, index=True
    )
    cache_key: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_valid: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


# Add indexes
Index("ix_render_jobs_project", RenderJob.project_id)
Index("ix_render_jobs_timeline", RenderJob.timeline_id)
Index("ix_render_jobs_status", RenderJob.status)
Index("ix_render_jobs_job_type", RenderJob.job_type)
Index("ix_render_jobs_preset", RenderJob.preset_id)
Index("ix_render_presets_platform", RenderPreset.platform)
Index("ix_render_presets_default", RenderPreset.is_default)
Index("ix_proxy_media_asset", ProxyMedia.media_asset_id)
Index("ix_proxy_media_status", ProxyMedia.status)
Index("ix_render_cache_project", RenderCache.project_id)
Index("ix_render_cache_timeline", RenderCache.timeline_id)
