"""Templates API endpoints for Phase 51 & 52."""


import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_owned_project
from app.models import MediaAsset, MediaType, Timeline, TimelineStatus, User
from app.models.template import VideoTemplate
from app.services.template_engine import get_template_engine
from app.services.video_cloner import get_video_style_cloner
from app.services.storage import get_storage_service
from app.core.timeline import normalize_timeline

router = APIRouter()


# â”€â”€ Request / Response schemas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class MediaItem(BaseModel):
    media_asset_id: uuid.UUID
    storage_key: str
    duration: float = Field(default=0.0, ge=0.0)
    theme: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class ApplyTemplateRequest(BaseModel):
    template_id: str
    user_media: List[MediaItem]


class CloneStyleRequest(BaseModel):
    reference_video_path: str
    user_media: List[MediaItem]


class ProjectCloneStyleRequest(BaseModel):
    reference_media_id: uuid.UUID
    raw_media_ids: List[uuid.UUID] = Field(min_length=1, max_length=100)


class ProjectApplyTemplateRequest(BaseModel):
    template_id: uuid.UUID
    raw_media_ids: List[uuid.UUID] = Field(min_length=1, max_length=100)


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    beatmap: Optional[List[float]] = None
    media_slots: Optional[List[Dict[str, Any]]] = None
    global_effects: Optional[Dict[str, Any]] = None
    is_public: bool
    created_at: str


# â”€â”€ Endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/apply", status_code=status.HTTP_200_OK)
async def apply_template(
    body: ApplyTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Apply a saved template to the provided user media."""
    try:
        template_id = uuid.UUID(body.template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template_id")

    engine = get_template_engine()
    media_dicts = [m.model_dump() for m in body.user_media]
    media_ids = [m.media_asset_id for m in body.user_media]
    owned = await db.execute(
        select(MediaAsset.id)
        .join(MediaAsset.project)
        .where(MediaAsset.id.in_(media_ids), MediaAsset.project.has(user_id=current_user.id))
    )
    owned_ids = {row[0] for row in owned.all()}
    if owned_ids != set(media_ids):
        raise HTTPException(status_code=403, detail="Media does not belong to the authenticated user")
    assets_result = await db.execute(select(MediaAsset).where(MediaAsset.id.in_(media_ids)))
    assets_by_id = {asset.id: asset for asset in assets_result.scalars().all()}
    if any(assets_by_id[media_id].storage_key != media.storage_key for media_id, media in zip(media_ids, body.user_media)):
        raise HTTPException(status_code=400, detail="Media storage keys do not match the database")

    try:
        timeline = await engine.apply_template(template_id, media_dicts)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {"status": "ok", "timeline": timeline}


@router.post("/projects/{project_id}/clone", status_code=status.HTTP_200_OK)
async def clone_project_style(
    project_id: uuid.UUID,
    body: ProjectCloneStyleRequest,
    project=Depends(get_owned_project),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Analyse one uploaded reference and apply its style to uploaded footage."""
    media_ids = [body.reference_media_id, *body.raw_media_ids]
    result = await db.execute(
        select(MediaAsset).where(
            MediaAsset.project_id == project_id,
            MediaAsset.id.in_(media_ids),
            MediaAsset.media_type == MediaType.VIDEO,
        )
    )
    media_by_id = {asset.id: asset for asset in result.scalars().all()}
    if len(media_by_id) != len(set(media_ids)):
        raise HTTPException(status_code=400, detail="Reference and raw media must be project videos")
    if body.reference_media_id in body.raw_media_ids:
        raise HTTPException(status_code=400, detail="Reference media cannot also be raw media")

    storage = get_storage_service()
    reference = media_by_id[body.reference_media_id]
    raw_media = [media_by_id[media_id] for media_id in body.raw_media_ids]
    reference_path = storage.get_path(reference.storage_key)
    user_media = [
        {
            "media_asset_id": str(asset.id),
            "storage_key": asset.storage_key,
            "duration": float(asset.duration or 0.0),
            "width": asset.width,
            "height": asset.height,
        }
        for asset in raw_media
    ]
    try:
        result = await get_video_style_cloner().clone_style(reference_path, user_media)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    timeline_json = normalize_timeline(result["timeline"])
    latest_result = await db.execute(
        select(func.max(Timeline.version_number)).where(Timeline.project_id == project_id)
    )
    version = int(latest_result.scalar() or 0) + 1
    timeline = Timeline(
        project_id=project_id,
        version_number=version,
        timeline_json=timeline_json,
        total_duration=float(timeline_json.get("total_duration", 0.0)),
        status=TimelineStatus.DRAFT,
    )
    db.add(timeline)
    await db.commit()
    await db.refresh(timeline)
    return {
        "status": "ok",
        "template_id": result.get("template_id"),
        "template": result.get("template"),
        "analysis": result.get("analysis"),
        "timeline_id": str(timeline.id),
        "timeline": timeline_json,
    }


@router.post("/clone", status_code=status.HTTP_200_OK)
async def clone_legacy_style(
    body: CloneStyleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Compatibility endpoint restricted to media owned by the caller.

    Clients must reference an uploaded media asset, never an arbitrary server
    path. New clients should use the project-scoped endpoint above.
    """
    media_ids = [item.media_asset_id for item in body.user_media]
    result = await db.execute(
        select(MediaAsset)
        .join(MediaAsset.project)
        .where(MediaAsset.id.in_(media_ids), MediaAsset.project.has(user_id=current_user.id))
    )
    assets = {asset.id: asset for asset in result.scalars().all()}
    if len(assets) != len(set(media_ids)):
        raise HTTPException(status_code=403, detail="Media does not belong to the authenticated user")
    storage = get_storage_service()
    allowed_reference_paths = {
        str(Path(storage.get_path(asset.storage_key)).resolve()) for asset in assets.values()
    }
    try:
        requested_reference = str(Path(body.reference_video_path).resolve())
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid reference media path") from exc
    if requested_reference not in allowed_reference_paths:
        raise HTTPException(status_code=400, detail="Reference must be one of the caller's uploaded media assets")
    media_dicts = []
    for item in body.user_media:
        asset = assets[item.media_asset_id]
        if asset.storage_key != item.storage_key:
            raise HTTPException(status_code=400, detail="Media storage keys do not match the database")
        media_dicts.append(
            {
                **item.model_dump(),
                "storage_key": asset.storage_key,
                "duration": float(asset.duration or item.duration or 0.0),
            }
        )
    try:
        result = await get_video_style_cloner().clone_style(requested_reference, media_dicts)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", **result}


@router.post("/projects/{project_id}/apply", status_code=status.HTTP_200_OK)
async def apply_project_template(
    project_id: uuid.UUID,
    body: ProjectApplyTemplateRequest,
    project=Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Apply a saved public template to raw videos in the current project."""

    template_result = await db.execute(
        select(VideoTemplate).where(
            VideoTemplate.id == body.template_id,
            VideoTemplate.is_public.is_(True),
        )
    )
    template = template_result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    media_result = await db.execute(
        select(MediaAsset).where(
            MediaAsset.project_id == project_id,
            MediaAsset.id.in_(body.raw_media_ids),
            MediaAsset.media_type == MediaType.VIDEO,
        )
    )
    assets = {asset.id: asset for asset in media_result.scalars().all()}
    if len(assets) != len(set(body.raw_media_ids)):
        raise HTTPException(status_code=400, detail="All raw media must be videos in this project")

    user_media = [
        {
            "media_asset_id": str(asset.id),
            "storage_key": asset.storage_key,
            "duration": float(asset.duration or 0.0),
            "width": asset.width,
            "height": asset.height,
        }
        for asset in (assets[media_id] for media_id in body.raw_media_ids)
    ]
    try:
        timeline_json = normalize_timeline(
            await get_template_engine().apply_template(body.template_id, user_media)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    metadata = dict(timeline_json.get("metadata") or {})
    metadata["director"] = {
        "mode": "saved_template",
        "template_id": str(template.id),
        "template_name": template.name,
    }
    timeline_json["metadata"] = metadata
    latest_result = await db.execute(
        select(func.max(Timeline.version_number)).where(Timeline.project_id == project_id)
    )
    timeline = Timeline(
        project_id=project_id,
        version_number=int(latest_result.scalar() or 0) + 1,
        timeline_json=timeline_json,
        total_duration=float(timeline_json.get("total_duration", 0.0)),
        status=TimelineStatus.DRAFT,
    )
    db.add(timeline)
    await db.commit()
    await db.refresh(timeline)
    return {
        "status": "ok",
        "template_id": str(template.id),
        "timeline_id": str(timeline.id),
        "timeline": timeline_json,
    }


@router.get("", status_code=status.HTTP_200_OK)
async def list_public_templates(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """List all public templates."""
    result = await db.execute(
        select(VideoTemplate).where(VideoTemplate.is_public.is_(True))
    )
    templates = result.scalars().all()

    items = [
        TemplateResponse(
            id=str(t.id),
            name=t.name,
            description=t.description,
            beatmap=t.beatmap,
            media_slots=t.media_slots,
            global_effects=t.global_effects,
            is_public=t.is_public,
            created_at=t.created_at.isoformat(),
        ).model_dump()
        for t in templates
    ]

    return {"templates": items, "total": len(items)}
