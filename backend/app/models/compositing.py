import uuid
from datetime import datetime, UTC
from typing import Optional
from enum import Enum as PyEnum

from sqlalchemy import Float, String, ForeignKey, DateTime, func, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, ConfigDict, Field

from app.core.database import Base


class BlendMode(str, PyEnum):
    NORMAL = "Normal"
    MULTIPLY = "Multiply"
    SCREEN = "Screen"
    OVERLAY = "Overlay"


class ClipCompositing(Base):
    __tablename__ = "clip_compositing"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timelines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The ID of the clip/track item in the timeline JSON
    track_item_id: Mapped[str] = mapped_column(String(255), nullable=False)

    position_x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    scale_x: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    scale_y: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    rotation: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    opacity: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    
    blend_mode: Mapped[BlendMode] = mapped_column(
        Enum(BlendMode), default=BlendMode.NORMAL, nullable=False
    )
    
    chroma_key_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    timeline: Mapped["Timeline"] = relationship("Timeline")


# Pydantic Schemas

class ClipCompositingBase(BaseModel):
    position_x: float = Field(0.0, description="X position offset")
    position_y: float = Field(0.0, description="Y position offset")
    scale_x: float = Field(1.0, description="X scale multiplier")
    scale_y: float = Field(1.0, description="Y scale multiplier")
    rotation: float = Field(0.0, description="Rotation in degrees")
    opacity: float = Field(1.0, ge=0.0, le=1.0, description="Opacity (0.0 to 1.0)")
    blend_mode: BlendMode = Field(BlendMode.NORMAL, description="Blend mode")
    chroma_key_color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$", description="Hex color for chroma key, e.g. #00FF00")

class ClipCompositingCreate(ClipCompositingBase):
    timeline_id: uuid.UUID
    track_item_id: str

class ClipCompositingUpdate(BaseModel):
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    scale_x: Optional[float] = None
    scale_y: Optional[float] = None
    rotation: Optional[float] = None
    opacity: Optional[float] = Field(None, ge=0.0, le=1.0)
    blend_mode: Optional[BlendMode] = None
    chroma_key_color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")

class ClipCompositingResponse(ClipCompositingBase):
    id: uuid.UUID
    timeline_id: uuid.UUID
    track_item_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
