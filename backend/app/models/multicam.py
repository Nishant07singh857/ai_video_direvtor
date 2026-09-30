import uuid
from datetime import datetime, UTC
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SyncMethod(str, PyEnum):
    AUDIO = "audio"
    TIMECODE = "timecode"
    IN_POINT = "in_point"
    OUT_POINT = "out_point"
    MARKER = "marker"


class MulticamAngle(Base):
    __tablename__ = "multicam_angles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sequence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("multicam_sequences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    camera_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    offset_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    sequence: Mapped["MulticamSequence"] = relationship(
        "MulticamSequence", 
        back_populates="angles", 
        foreign_keys=[sequence_id]
    )
    media_asset: Mapped["MediaAsset"] = relationship("MediaAsset")


class MulticamSequence(Base):
    __tablename__ = "multicam_sequences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sync_method: Mapped[SyncMethod] = mapped_column(Enum(SyncMethod), nullable=False)
    
    active_angle_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("multicam_angles.id", name="fk_multicam_active_angle", ondelete="SET NULL", use_alter=True), nullable=True, index=True
    )
    audio_source_angle_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("multicam_angles.id", name="fk_multicam_audio_angle", ondelete="SET NULL", use_alter=True), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    project: Mapped["Project"] = relationship("Project")
    angles: Mapped[List["MulticamAngle"]] = relationship(
        "MulticamAngle", 
        back_populates="sequence", 
        foreign_keys="[MulticamAngle.sequence_id]",
        cascade="all, delete-orphan"
    )
    active_angle: Mapped[Optional["MulticamAngle"]] = relationship(
        "MulticamAngle",
        foreign_keys=[active_angle_id],
        post_update=True
    )
    audio_source_angle: Mapped[Optional["MulticamAngle"]] = relationship(
        "MulticamAngle",
        foreign_keys=[audio_source_angle_id],
        post_update=True
    )
