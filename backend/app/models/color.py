import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import Float, String, ForeignKey, DateTime, func, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, ConfigDict, Field

from app.core.database import Base

class ColorAdjustment(Base):
    __tablename__ = "color_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Applied to either a VideoShot (source media) or a StoryShot (timeline instance)
    video_shot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video_shots.id", ondelete="CASCADE"), nullable=True, index=True
    )
    story_shot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("story_shots.id", ondelete="CASCADE"), nullable=True, index=True
    )

    contrast: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    brightness: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    saturation: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tint: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    lut_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "(video_shot_id IS NOT NULL AND story_shot_id IS NULL) OR "
            "(video_shot_id IS NULL AND story_shot_id IS NOT NULL)",
            name="check_color_adjustment_target"
        ),
    )

    # Relationships can be added here if needed
    # video_shot = relationship("VideoShot")
    # story_shot = relationship("StoryShot")


# Pydantic Schemas

class ColorAdjustmentBase(BaseModel):
    contrast: float = Field(1.0, description="Contrast multiplier (1.0 is neutral)")
    brightness: float = Field(1.0, description="Brightness multiplier (1.0 is neutral)")
    saturation: float = Field(1.0, description="Saturation multiplier (1.0 is neutral)")
    temperature: float = Field(0.0, description="Color temperature adjustment")
    tint: float = Field(0.0, description="Tint adjustment (green-magenta axis)")
    lut_path: Optional[str] = Field(None, description="Path to a custom 3D LUT file (.cube)")

class ColorAdjustmentCreate(ColorAdjustmentBase):
    video_shot_id: Optional[uuid.UUID] = None
    story_shot_id: Optional[uuid.UUID] = None

class ColorAdjustmentUpdate(BaseModel):
    contrast: Optional[float] = None
    brightness: Optional[float] = None
    saturation: Optional[float] = None
    temperature: Optional[float] = None
    tint: Optional[float] = None
    lut_path: Optional[str] = None

class ColorAdjustmentResponse(ColorAdjustmentBase):
    id: uuid.UUID
    video_shot_id: Optional[uuid.UUID]
    story_shot_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
