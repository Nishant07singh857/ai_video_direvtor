import uuid
from datetime import datetime
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ErrorSeverity(str, enum.Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ModelStatus(str, enum.Enum):
    TRAINING = "TRAINING"
    EVALUATING = "EVALUATING"
    SHADOW = "SHADOW"
    PRODUCTION = "PRODUCTION"
    RETIRED = "RETIRED"
    FAILED = "FAILED"


class AIErrorEvent(Base):
    """
    Stores structured error events and learning signals from the continuous learning loop.
    """
    __tablename__ = "ai_error_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    
    # Context IDs
    ai_run_id = Column(String(255), nullable=True)
    operation_id = Column(String(255), nullable=True)
    timeline_id = Column(String(255), nullable=True)
    timeline_version_id = Column(String(255), nullable=True)
    
    # Error Classification
    error_type = Column(String(255), nullable=False) # e.g., SHOT_DURATION_OVER_ESTIMATION
    error_category = Column(String(100), nullable=False) # EDITORIAL, TECHNICAL, AI, UX
    severity = Column(Enum(ErrorSeverity), default=ErrorSeverity.INFO)
    
    # Payload
    input_context = Column(JSON, nullable=True)
    ai_action = Column(JSON, nullable=True)
    expected_result = Column(JSON, nullable=True)
    actual_result = Column(JSON, nullable=True)
    source_context = Column(JSON, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True) # metadata is reserved in SQLAlchemy
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    project = relationship("Project")
    user = relationship("User")


class ModelRegistry(Base):
    """
    Tracks AI models, their versions, and statuses for the learning governance pipeline.
    """
    __tablename__ = "model_registry"

    model_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_type = Column(String(100), nullable=False) # e.g., RANKING, PREFERENCE, CRITIC
    version = Column(String(50), nullable=False)
    dataset_version = Column(String(100), nullable=True)
    training_run_id = Column(String(255), nullable=True)
    
    metrics = Column(JSON, nullable=True)
    status = Column(Enum(ModelStatus), default=ModelStatus.TRAINING)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    rollback_version = Column(String(50), nullable=True)


class PipelineStatus(str, enum.Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    LEARNED = "LEARNED"
    IGNORED = "IGNORED"


class ErrorToLearningPipeline(Base):
    """
    Tracks the full lifecycle of a user correction transforming into AI learning.
    """
    __tablename__ = "error_to_learning_pipeline"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    error_event_id = Column(UUID(as_uuid=True), ForeignKey("ai_error_events.id", ondelete="CASCADE"), index=True, nullable=False)
    
    # Core learning data
    original_decision = Column(JSON, nullable=False)
    user_correction = Column(JSON, nullable=False)
    root_cause_analysis = Column(JSON, nullable=True)
    
    status = Column(Enum(PipelineStatus), default=PipelineStatus.PENDING)
    applied_to_model_id = Column(UUID(as_uuid=True), ForeignKey("model_registry.model_id", ondelete="SET NULL"), index=True, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    error_event = relationship("AIErrorEvent")
    applied_to_model = relationship("ModelRegistry")

