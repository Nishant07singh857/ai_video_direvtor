"""
Effect System data models for the AI Video Director.
Extensible effect schema supporting blur, sharpen, glow, speed ramp, and stabilisation.
NOTE: This platform edits raw video — it does NOT generate video content.
"""

import uuid
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List
from enum import Enum as PyEnum

from sqlalchemy import ForeignKey, String, Enum as SAEnum, JSON, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EffectType(str, PyEnum):
    BLUR = "blur"
    SHARPEN = "sharpen"
    GLOW = "glow"
    SPEED_RAMP = "speed_ramp"
    STABILIZE = "stabilize"


class Effect(Base):
    """A video effect applied to a clip on the timeline."""
    __tablename__ = "effects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timelines.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Logical clip identifier within the timeline JSON
    track_item_id: Mapped[str] = mapped_column(String(255), nullable=False)

    effect_type: Mapped[EffectType] = mapped_column(
        SAEnum(EffectType, name="effect_type"), nullable=False,
    )

    # Freeform parameters — schema depends on effect_type.
    # E.g. BLUR: {"radius": 5, "sigma": 1.2}
    #      SPEED_RAMP: {"speed_curve": [[0,1],[0.5,0.25],[1,1]]}
    parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict,
    )

    # Keyframes for animating the effect over time.
    # List of {"time": float, "values": {param: value}} dicts.
    keyframes: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON, nullable=True,
    )

    # Whether this effect implementation supports GPU acceleration
    cpu_gpu_capable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )

    # Optional: ordering when multiple effects stack on the same clip
    order: Mapped[int] = mapped_column(default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    timeline: Mapped["Timeline"] = relationship("Timeline")


# Indexes
Index("ix_effects_timeline_track", Effect.timeline_id, Effect.track_item_id)
Index("ix_effects_type", Effect.effect_type)
