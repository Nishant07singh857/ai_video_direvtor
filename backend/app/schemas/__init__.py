from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: Optional[str] = None


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    platform: Optional[str] = Field(None, pattern="^(youtube|instagram|shorts)$")


class ProjectCreate(ProjectBase):
    ...


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    platform: Optional[str] = Field(None, pattern="^(youtube|instagram|shorts)$")
    status: Optional[str] = Field(None, pattern="^(draft|processing|completed|failed)$")


class ProjectResponse(ProjectBase):
    id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int
    page: int
    page_size: int


# Media schemas
class MediaAssetBase(BaseModel):
    original_filename: str
    media_type: str
    mime_type: str
    file_size: int
    checksum: str


class MediaAssetCreate(MediaAssetBase):
    storage_key: str


class MediaAssetUpdate(BaseModel):
    status: Optional[str] = None
    error_message: Optional[str] = None


class MediaAssetResponse(MediaAssetBase):
    id: UUID
    project_id: UUID
    status: str
    error_message: Optional[str] = None
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    bitrate: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MediaAssetListResponse(BaseModel):
    media_assets: list[MediaAssetResponse]
    total: int
    page: int
    page_size: int

# Style Cloning schemas