import hashlib
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import BackgroundTasks, APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import MediaAsset, MediaStatus, MediaType, Project, User
from app.schemas import MediaAssetResponse, MediaAssetListResponse
from app.services.storage import get_storage_service

router = APIRouter()


async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    """Get project and verify ownership."""
    query = select(Project).where(
        Project.id == project_id, Project.user_id == current_user.id
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


# Supported media MIME types.  The extension is used only to select the
# media class; the stored bytes are still validated by FFprobe/decoders in
# the processing pipeline.
SUPPORTED_MEDIA_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
    "video/x-flv",
    "video/mpeg",
    "video/3gpp",
    "video/3gpp2",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/ogg",
    "audio/webm",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

EXTENSION_MEDIA_TYPES = {
    ".mp4": MediaType.VIDEO, ".mov": MediaType.VIDEO, ".avi": MediaType.VIDEO,
    ".mkv": MediaType.VIDEO, ".webm": MediaType.VIDEO, ".flv": MediaType.VIDEO,
    ".mpeg": MediaType.VIDEO, ".mpg": MediaType.VIDEO, ".3gp": MediaType.VIDEO,
    ".3g2": MediaType.VIDEO, ".mp3": MediaType.AUDIO, ".wav": MediaType.AUDIO,
    ".m4a": MediaType.AUDIO, ".ogg": MediaType.AUDIO, ".flac": MediaType.AUDIO,
    ".aac": MediaType.AUDIO, ".jpg": MediaType.IMAGE, ".jpeg": MediaType.IMAGE,
    ".png": MediaType.IMAGE, ".webp": MediaType.IMAGE, ".gif": MediaType.IMAGE,
}


def validate_media_file(filename: str, content_type: str) -> tuple[MediaType, str]:
    """Validate media file and return media type and MIME type."""
    ext = Path(filename).suffix.lower()
    media_type = EXTENSION_MEDIA_TYPES.get(ext)
    if media_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media extension: {ext}",
        )

    # Browsers sometimes send application/octet-stream.  Accept that only
    # when the extension is known; reject a contradictory, known MIME type.
    if content_type and content_type != "application/octet-stream" and content_type not in SUPPORTED_MEDIA_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported MIME type: {content_type}")
    if content_type and content_type not in {"application/octet-stream", ""}:
        declared_type = content_type.split("/", 1)[0]
        if declared_type != media_type.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File extension and MIME type disagree")
    fallback_mime = {
        MediaType.VIDEO: "video/mp4",
        MediaType.AUDIO: "audio/mpeg",
        MediaType.IMAGE: "image/jpeg",
    }[media_type]
    return media_type, content_type or fallback_mime


async def calculate_checksum(file_obj, chunk_size: int = 8192) -> str:
    """Calculate SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    while chunk := await file_obj.read(chunk_size):
        hasher.update(chunk)
    await file_obj.seek(0)
    return hasher.hexdigest()


@router.post(
    "/projects/{project_id}/media",
    response_model=MediaAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a media file to a project."""
    # Verify project ownership
    project = await get_project(project_id, db, current_user)
    
    # Validate file
    media_type, mime_type = validate_media_file(file.filename or "", file.content_type or "")
    
    # Optimized Zero-Copy Streaming Upload (Fixes RAM spikes)
    import aiofiles
    
    file_size = 0
    hasher = hashlib.sha256()
    
    # Generate unique storage key
    ext = Path(file.filename or "").suffix.lower()
    storage_key = f"projects/{project_id}/{uuid.uuid4()}{ext}"
    storage = get_storage_service()
    final_file_path = storage.get_path(storage_key)
    import os
    os.makedirs(os.path.dirname(final_file_path), exist_ok=True)

    # Write to a private temporary sibling and publish atomically only after
    # the complete byte stream and checksum have been accepted.  A cancelled
    # upload can therefore never become renderable media.
    temporary_file_path = f"{final_file_path}.uploading"
    try:
        async with aiofiles.open(temporary_file_path, "wb") as out_file:
            while chunk := await file.read(64 * 1024):  # 64 KB buffer limits RAM usage
                file_size += len(chunk)
                if file_size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE} bytes",
                    )
                hasher.update(chunk)
                await out_file.write(chunk)
        os.replace(temporary_file_path, final_file_path)
    except Exception:
        try:
            os.remove(temporary_file_path)
        except FileNotFoundError:
            pass
        raise
            
    checksum = hasher.hexdigest()
    
    # Create MediaAsset record
    media_asset = MediaAsset(
        project_id=project_id,
        original_filename=file.filename,
        storage_key=storage_key,
        media_type=media_type,
        mime_type=mime_type,
        file_size=file_size,
        checksum=checksum,
        status=MediaStatus.UPLOADED,
    )
    db.add(media_asset)
    await db.commit()
    await db.refresh(media_asset)
    
    # Metadata/analysis is intentionally a background step.  The API returns
    # immediately, while the media row transitions to FAILED with a useful
    # error instead of reporting READY for an unverified file.
    async def process_media() -> None:
        from app.core import database
        from app.services.media_analysis import get_media_analysis_service

        try:
            async with database.async_session_maker() as session:
                media = await session.get(MediaAsset, media_asset.id)
                if media:
                    media.status = MediaStatus.PROCESSING
                    await session.commit()
            if media_type == MediaType.VIDEO:
                analysis_result = await get_media_analysis_service().analyze_media(media_asset.id)
                failed_jobs = [
                    analysis_type
                    for analysis_type, job_result in analysis_result.get("jobs", {}).items()
                    if not job_result.get("success")
                ]
                if failed_jobs:
                    raise RuntimeError(
                        "Media analysis failed for: " + ", ".join(sorted(failed_jobs))
                    )
            else:
                from video_engine.ingestion.processor import MediaProcessor
                metadata = await MediaProcessor().extract_metadata(storage.get_path(storage_key))
                async with database.async_session_maker() as session:
                    media = await session.get(MediaAsset, media_asset.id)
                    if media:
                        media.duration = metadata.duration
                        media.width = metadata.width
                        media.height = metadata.height
                        media.fps = metadata.fps
                        media.video_codec = metadata.video_codec
                        media.audio_codec = metadata.audio_codec
                        media.bitrate = metadata.bitrate
                        media.status = MediaStatus.READY
                        await session.commit()
            async with database.async_session_maker() as session:
                media = await session.get(MediaAsset, media_asset.id)
                if media and media.status != MediaStatus.FAILED:
                    media.status = MediaStatus.READY
                    await session.commit()
        except Exception as exc:
            async with database.async_session_maker() as session:
                media = await session.get(MediaAsset, media_asset.id)
                if media:
                    media.status = MediaStatus.FAILED
                    media.error_message = str(exc)[:2000]
                    await session.commit()

    background_tasks.add_task(process_media)
    
    return media_asset


@router.get(
    "/projects/{project_id}/media",
    response_model=MediaAssetListResponse,
)
async def list_media(
    project_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List media assets for a project."""
    # Verify project ownership
    project = await get_project(project_id, db, current_user)
    
    query = select(MediaAsset).where(MediaAsset.project_id == project_id).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    media_assets = result.scalars().all()
    
    count_query = select(func.count(MediaAsset.id)).where(MediaAsset.project_id == project_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return {
        "media_assets": media_assets,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/media/{media_id}",
    response_model=MediaAssetResponse,
)
async def get_media(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific media asset."""
    query = select(MediaAsset).where(MediaAsset.id == media_id)
    result = await db.execute(query)
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media asset not found",
        )
        
    # Verify ownership through project
    await get_project(media.project_id, db, current_user)
    
    return media

@router.get("/media/{media_id}/stream")
async def stream_media(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi.responses import FileResponse
    from app.services.storage import get_storage_service
    
    query = select(MediaAsset).where(MediaAsset.id == media_id)
    result = await db.execute(query)
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
        
    # Authentication is handled by the bearer dependency.  Deliberately do
    # not accept access tokens in the URL: query strings leak into browser
    # history, proxy logs, and referrer headers.
    await get_project(media.project_id, db, current_user)
    
    storage = get_storage_service()
    path = storage.get_path(media.storage_key)
    import os
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(path, media_type=media.mime_type or "video/mp4", headers={"Accept-Ranges": "bytes"})

@router.delete(
    "/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_media(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a media asset."""
    # Get media and verify ownership
    media = await get_media(media_id, db, current_user)
    
    # Delete from storage
    storage = get_storage_service()
    storage.delete(media.storage_key)
    
    # Delete from database
    await db.delete(media)
    await db.commit()
    
    return None
