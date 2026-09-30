from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class StyleCloneBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: bool = False

class StyleCloneCreate(StyleCloneBase):
    reference_asset_id: Optional[UUID] = None

class StyleCloneExtractRequest(BaseModel):
    reference_asset_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: bool = False

class StyleCloneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: Optional[bool] = None

class StyleCloneResponse(StyleCloneBase):
    id: UUID
    reference_asset_id: Optional[UUID] = None
    extracted_lut_path: Optional[str] = None
    color_parameters: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StyleCloneListResponse(BaseModel):
    styles: List[StyleCloneResponse]
    total: int
    page: int
    page_size: int
