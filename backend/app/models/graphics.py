"""
Motion Graphics data models for the AI Video Director.
Defines Text Layers, Shape Layers, and Keyframe structures for title overlays.
NOTE: This platform edits raw video — it does NOT generate video content.
"""

import uuid
from datetime import datetime, UTC
from enum import Enum as PyEnum

from sqlalchemy import ForeignKey, Float, Text, String, Integer, JSON, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class GraphicsLayerType(str, PyEnum):
    TEXT = "text"
    SHAPE = "shape"
    SUBTITLE = "subtitle"
    LOWER_THIRD = "lower_third"


class GraphicsLayer(Base):
    """A text or shape overlay on the timeline."""
    __tablename__ = "graphics_layers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timeline_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("timelines.id"), index=True, nullable=False)
    layer_type: Mapped[GraphicsLayerType] = mapped_column(SAEnum(GraphicsLayerType, name="graphics_layer_type"), nullable=False)

    # Timing
    start_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)

    # Text properties
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    font_family: Mapped[str] = mapped_column(String(128), nullable=False, default="Arial")
    font_size: Mapped[int] = mapped_column(Integer, nullable=False, default=48)
    font_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#FFFFFF")
    background_color: Mapped[Optional[str]] = mapped_column(String(9), nullable=True)

    # Transform
    position_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)  # 0-1 normalized
    position_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.9)  # 0-1 normalized
    opacity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Keyframes stored as JSON array
    keyframes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
