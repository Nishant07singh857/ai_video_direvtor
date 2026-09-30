import uuid
from datetime import datetime, UTC
from typing import Optional, Dict, Any

from sqlalchemy import ForeignKey, Float, String, DateTime, func, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserPreference(Base):
    """
    Stores individual user's video editing preferences.
    Learns over time via AI Error Learning and usage patterns.
    """
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    
    preferred_pacing: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # 1.0 = normal, >1 faster, <1 slower
    preferred_style: Mapped[str] = mapped_column(String(100), default="cinematic", nullable=False)
    
    # Stores dynamic preferences like favorite transitions, color grading presets, etc.
    advanced_preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")


class EditorDecisionPattern(Base):
    """
    Tracks editing decisions made by a specific user across different contexts.
    Used to build an AI memory graph of "how this user edits".
    """
    __tablename__ = "editor_decision_patterns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    context_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "action_scene", "dialogue"
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "cut_on_beat", "color_temp_change"
    
    pattern_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    project: Mapped[Optional["Project"]] = relationship("Project")
