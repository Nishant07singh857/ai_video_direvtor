"""Style Cloning model for Phase 52 - Video Style Cloning."""

import uuid
from datetime import datetime, UTC
from typing import Optional, Dict, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


class StyleClone(Base):
    __tablename__ = "style_clones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    reference_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True)
    extracted_lut_path: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, comment="Path to generated LUT file"
    )
    color_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, comment="Extracted color values (brightness, contrast, etc.)"
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
    reference_asset: Mapped[Optional["MediaAsset"]] = relationship(
        "MediaAsset", foreign_keys=[reference_asset_id]
    )

# Indexes
Index("ix_style_clones_is_public", StyleClone.is_public)
Index("ix_style_clones_reference_asset", StyleClone.reference_asset_id)
