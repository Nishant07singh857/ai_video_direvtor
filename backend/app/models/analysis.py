import uuid
from datetime import datetime, UTC
from typing import Optional
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func, Integer, Float, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy import JSON as Vector


class AnalysisStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisType(str, PyEnum):
    SHOT_DETECTION = "shot_detection"
    KEYFRAME_EXTRACTION = "keyframe_extraction"
    SCENE_DETECTION = "scene_detection"
    AUDIO_ANALYSIS = "audio_analysis"
    SPEECH_TRANSCRIPTION = "speech_transcription"
    VISUAL_ANALYSIS = "visual_analysis"


class CinematicType(str, PyEnum):
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    ESTABLISHING = "establishing"
    OVER_THE_SHOULDER = "over_the_shoulder"
    B_ROLL = "b_roll"
    INSERT = "insert"


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_type: Mapped[AnalysisType] = mapped_column(Enum(AnalysisType), nullable=False)
    status: Mapped[AnalysisStatus] = mapped_column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
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
    media_asset: Mapped["MediaAsset"] = relationship("MediaAsset")


class VideoShot(Base):
    __tablename__ = "video_shots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    shot_index: Mapped[int] = mapped_column(Integer, nullable=False)
    detection_method: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    embedding = mapped_column(Vector, nullable=True)
    cinematic_type: Mapped[Optional[CinematicType]] = mapped_column(Enum(CinematicType), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    media_asset: Mapped["MediaAsset"] = relationship("MediaAsset", back_populates="shots")
    keyframes: Mapped[list["Keyframe"]] = relationship("Keyframe", back_populates="shot", cascade="all, delete-orphan")


class VideoScene(Base):
    __tablename__ = "video_scenes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    scene_index: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    detection_method: Mapped[str] = mapped_column(String(100), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    media_asset: Mapped["MediaAsset"] = relationship("MediaAsset", back_populates="scenes")


class Keyframe(Base):
    __tablename__ = "keyframes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video_shots.id", ondelete="CASCADE"), nullable=True, index=True
    )
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    frame_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    media_asset: Mapped["MediaAsset"] = relationship("MediaAsset", back_populates="keyframes")
    shot: Mapped[Optional["VideoShot"]] = relationship("VideoShot", back_populates="keyframes")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    speaker_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    media_asset: Mapped["MediaAsset"] = relationship("MediaAsset", back_populates="transcript_segments")


class AudioAnalysis(Base):
    __tablename__ = "audio_analysis"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    has_audio: Mapped[bool] = mapped_column(default=False, nullable=False)
    audio_streams: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sample_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    channels: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bitrate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Audio features (extensible JSON)
    features: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    media_asset: Mapped["MediaAsset"] = relationship("MediaAsset", back_populates="audio_analysis")


# Add indexes
Index("ix_analysis_jobs_media_asset_type", AnalysisJob.media_asset_id, AnalysisJob.analysis_type)
Index("ix_analysis_jobs_status", AnalysisJob.status)
Index("ix_video_shots_media_asset", VideoShot.media_asset_id)
Index("ix_video_shots_start_time", VideoShot.start_time)
Index("ix_video_scenes_media_asset", VideoScene.media_asset_id)
Index("ix_keyframes_media_asset", Keyframe.media_asset_id)
Index("ix_keyframes_shot", Keyframe.shot_id)
Index("ix_transcript_segments_media_asset", TranscriptSegment.media_asset_id)
Index("ix_transcript_segments_time", TranscriptSegment.start_time, TranscriptSegment.end_time)
Index("ix_audio_analysis_media_asset", AudioAnalysis.media_asset_id)