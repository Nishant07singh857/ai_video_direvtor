"""
Image Editing data models for the AI Video Director.
Supports placing still images on the timeline with Ken Burns (pan/zoom) effects.
NOTE: This platform edits raw video — it does NOT generate video content.
"""

import uuid
from datetime import datetime, UTC
from typing import Optional, Dict, Any

from sqlalchemy import Float, String, ForeignKey, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ImageOnTimeline(Base):
    """A still image placed on a timeline with optional Ken Burns animation."""
    __tablename__ = "image_on_timeline"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timelines.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Reference to the source image asset
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Logical clip identifier within the timeline JSON
    track_item_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Placement on the timeline (seconds)
    start_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)

    # --- Ken Burns effect parameters ---
    # Crop regions are normalised 0-1 (x, y, w, h) stored as JSON dicts
    start_crop: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, comment='{"x":0,"y":0,"w":1,"h":1}'
    )
    end_crop: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, comment='{"x":0.1,"y":0.1,"w":0.8,"h":0.8}'
    )

    # Pan offsets (normalised -1 to 1, centre = 0)
    pan_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pan_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Zoom multipliers (1.0 = no zoom)
    zoom_start: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    zoom_end: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    timeline: Mapped["Timeline"] = relationship("Timeline")
    media_asset: Mapped["MediaAsset"] = relationship("MediaAsset")


# Indexes
Index("ix_image_on_timeline_timeline_track", ImageOnTimeline.timeline_id, ImageOnTimeline.track_item_id)
