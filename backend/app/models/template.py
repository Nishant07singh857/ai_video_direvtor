"""Video template model for Phase 51 - Template Engine."""

import uuid
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


class VideoTemplate(Base):
    __tablename__ = "video_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True)
    beatmap: Mapped[Optional[List[float]]] = mapped_column(
        JSON, nullable=True, comment="Array of float timestamps for beat sync"
    )
    media_slots: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Array of {slot_index, duration, target_theme, aspect_ratio}",
    )
    global_effects: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, comment="{color_lut, transitions}"
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    audio_asset: Mapped[Optional["MediaAsset"]] = relationship(
        "MediaAsset", foreign_keys=[audio_asset_id]
    )


# Indexes
Index("ix_video_templates_is_public", VideoTemplate.is_public)
Index("ix_video_templates_audio_asset", VideoTemplate.audio_asset_id)
