import uuid
from datetime import datetime, UTC
from enum import Enum as PyEnum

from typing import Optional, Dict, Any
from sqlalchemy import ForeignKey, String, Enum, DateTime, JSON, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EditOperationType(str, PyEnum):
    TRIM = "trim"
    SPLIT = "split"
    DELETE = "delete"
    MOVE = "move"
    ADD = "add"


class EditOperation(Base):
    __tablename__ = "edit_operations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timelines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Target item (e.g., track item id in the timeline JSON)
    target_item_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Operation details
    operation_type: Mapped[EditOperationType] = mapped_column(Enum(EditOperationType), nullable=False)
    
    # Parameters for the operation (e.g., {"trim_start": 1.5, "trim_end": 5.0} for TRIM, 
    # {"split_time": 3.0} for SPLIT, {"new_start_time": 10.0, "track": 1} for MOVE)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    
    # To maintain sequence of edits
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Undo/redo state tracking
    is_undone: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    timeline: Mapped["Timeline"] = relationship("Timeline")


# Indexes
Index("ix_edit_operations_project", EditOperation.project_id)
Index("ix_edit_operations_timeline", EditOperation.timeline_id)
Index("ix_edit_operations_sequence", EditOperation.timeline_id, EditOperation.sequence_order)
