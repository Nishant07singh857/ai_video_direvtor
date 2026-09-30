from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class ProjectSnapshot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    snapshot_data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    description: Optional[str] = None

class TimelineVersion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timeline_id: str
    version_number: int
    timeline_data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    author_id: Optional[str] = None
    commit_message: Optional[str] = None
