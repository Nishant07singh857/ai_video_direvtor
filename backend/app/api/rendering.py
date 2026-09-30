"""
Rendering API endpoints.
Handles preview/export job creation, status, download, and management.
"""

import os
from uuid import UUID
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Body, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.render_job_service import get_render_job_service
from app.services.preview_service import get_preview_service
from app.services.export_service import get_export_service
from app.services.storage import get_storage_service
from app.models import User, RenderPreset, RenderJob, Project, RenderJobType, Timeline, RenderJobStatus
router = APIRouter()


async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    """Get project and verify ownership."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


async def get_timeline(
    timeline_id: UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
) -> Timeline:
    """Get timeline and verify it belongs to the project."""
    result = await db.execute(
        select(Timeline).where(
            Timeline.id == timeline_id,
            Timeline.project_id == project.id,
        )
    )
    timeline = result.scalar_one_or_none()
    if not timeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeline not found",
        )
    return timeline


async def get_render_job(
    render_job_id: UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
) -> RenderJob:
    """Get render job and verify it belongs to the project."""
    result = await db.execute(
        select(RenderJob).where(
            RenderJob.id == render_job_id,
            RenderJob.project_id == project.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Render job not found",
        )
    return job


# Preview Render Endpoint
@router.post(
    "/projects/{project_id}/timelines/{timeline_id}/preview",
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_preview_render(
    project_id: UUID,
    timeline_id: UUID,
    project: Project = Depends(get_project),
    timeline: Timeline = Depends(get_timeline),
    current_user: User = Depends(get_current_user),
):
    """Start a preview render for a timeline."""
    preview_service = get_preview_service()

    result = await preview_service.create_preview_job(
        project_id=project_id,
        timeline_id=timeline_id,
        user_id=current_user.id,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error,
        )

    # Queue only when explicitly enabled.  Importing Celery is not proof that
    # a broker is reachable; avoiding an implicit broker connection keeps local
    # development and tests deterministic.
    try:
        if not settings.CELERY_ENABLED:
            raise RuntimeError("Celery queue disabled")
        from app.workers.render_tasks import render_preview_job
        render_preview_job.delay(str(timeline_id), str(result.render_job.id))
    except Exception as exc:
        if not settings.RENDER_SYNC_FALLBACK:
            raise HTTPException(status_code=503, detail="Render queue unavailable") from exc
        # Development fallback only. Production must have a worker/queue.
        import asyncio
        asyncio.create_task(preview_service.execute_preview_render(result.render_job.id))

    return {
        "render_job_id": str(result.render_job.id),
        "status": "queued",
    }


# Export Render Endpoint
@router.post(
    "/projects/{project_id}/timelines/{timeline_id}/export",
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_export_render(
    project_id: UUID,
    timeline_id: UUID,
    preset_id: Optional[UUID] = Query(None),
    body: Optional[Dict[str, Any]] = Body(None),
    project: Project = Depends(get_project),
    timeline: Timeline = Depends(get_timeline),
    current_user: User = Depends(get_current_user),
):
    """Start an export render for a timeline."""
    if body and body.get("preset_id"):
        try:
            preset_id = UUID(str(body["preset_id"]))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Invalid preset_id") from exc
    export_service = get_export_service()

    result = await export_service.create_export_job(
        project_id=project_id,
        timeline_id=timeline_id,
        user_id=current_user.id,
        preset_id=preset_id,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error,
        )

    # Try to queue with Celery, fall back to synchronous for local dev
    try:
        if not settings.CELERY_ENABLED:
            raise RuntimeError("Celery queue disabled")
        from app.workers.render_tasks import render_export_job
        render_export_job.delay(
            str(timeline_id),
            str(result.render_job.id),
            str(result.render_job.preset_id),
        )
    except Exception as exc:
        if not settings.RENDER_SYNC_FALLBACK:
            raise HTTPException(status_code=503, detail="Render queue unavailable") from exc
        # Development fallback only. Production must have a worker/queue.
        import asyncio
        asyncio.create_task(export_service.execute_export_render(result.render_job.id))

    return {
        "render_job_id": str(result.render_job.id),
        "status": "queued",
    }


# List Render Jobs
@router.get("/projects/{project_id}/renders")
async def list_render_jobs(
    project_id: UUID,
    job_type: Optional[RenderJobType] = None,
    status: Optional[RenderJobStatus] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    project: Project = Depends(get_project),
):
    """List all render jobs for a project."""
    render_job_service = get_render_job_service()

    jobs = await render_job_service.list_jobs(
        project_id=project_id,
        job_type=job_type,
        status=status,
        limit=limit,
        offset=offset,
    )

    job_infos = []
    for job in jobs:
        info = await render_job_service.get_job_info(job)
        job_infos.append({
            "id": str(info.id),
            "timeline_id": str(info.timeline_id) if info.timeline_id else None,
            "job_type": info.job_type.value,
            "status": info.status.value,
            "progress": info.progress,
            "output_storage_key": info.output_storage_key,
            "output_size": info.output_size,
            "duration": info.duration,
            "width": info.width,
            "height": info.height,
            "fps": info.fps,
            "video_codec": info.video_codec,
            "bitrate": info.bitrate,
            "error_message": info.error_message,
            "created_at": info.created_at.isoformat() if info.created_at else None,
            "started_at": info.started_at.isoformat() if info.started_at else None,
            "completed_at": info.completed_at.isoformat() if info.completed_at else None,
            "preset_name": info.preset_name,
            "preset_platform": info.preset_platform,
        })

    return {
        "project_id": str(project_id),
        "renders": job_infos,
        "total": len(job_infos),
    }


# Get Render Job Detail
@router.get("/projects/{project_id}/renders/{render_job_id}")
async def get_render_job_detail(
    project_id: UUID,
    render_job_id: UUID,
    project: Project = Depends(get_project),
    render_job: RenderJob = Depends(get_render_job),
):
    """Get detailed information about a render job."""
    render_job_service = get_render_job_service()
    info = await render_job_service.get_job_info(render_job)

    return {
        "id": str(info.id),
        "project_id": str(info.project_id),
        "timeline_id": str(info.timeline_id) if info.timeline_id else None,
        "job_type": info.job_type.value,
        "status": info.status.value,
        "progress": info.progress,
        "output_storage_key": info.output_storage_key,
        "output_size": info.output_size,
        "duration": info.duration,
        "width": info.width,
        "height": info.height,
        "fps": info.fps,
        "video_codec": info.video_codec,
        "bitrate": info.bitrate,
        "error_message": info.error_message,
        "ffmpeg_cmd": render_job.ffmpeg_cmd,
        "created_at": info.created_at.isoformat() if info.created_at else None,
        "started_at": info.started_at.isoformat() if info.started_at else None,
        "completed_at": info.completed_at.isoformat() if info.completed_at else None,
        "preset_name": info.preset_name,
        "preset_platform": info.preset_platform,
    }


# Download Rendered File
@router.get("/projects/{project_id}/renders/{render_job_id}/download")
async def download_render(
    project_id: UUID,
    render_job_id: UUID,
    project: Project = Depends(get_project),
    render_job: RenderJob = Depends(get_render_job),
):
    """Download a rendered video file."""
    if render_job.status != RenderJobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Render job not completed. Status: {render_job.status.value}",
        )

    if not render_job.output_storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Render output not found",
        )

    storage = get_storage_service()
    file_path = storage.get_path(render_job.output_storage_key)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Render file not found on disk",
        )

    # Determine filename
    filename = f"render_{render_job.job_type.value}.mp4"
    if render_job.timeline_id:
        filename = f"timeline_{render_job.timeline_id}_{render_job.job_type.value}.mp4"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="video/mp4",
    )


# Cancel Render Job
@router.delete("/projects/{project_id}/renders/{render_job_id}")
async def cancel_render_job(
    project_id: UUID,
    render_job_id: UUID,
    project: Project = Depends(get_project),
    render_job: RenderJob = Depends(get_render_job),
):
    """Cancel a queued or running render job."""
    render_job_service = get_render_job_service()

    if render_job.status in (RenderJobStatus.COMPLETED, RenderJobStatus.FAILED, RenderJobStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {render_job.status.value}",
        )

    success = await render_job_service.cancel_job(render_job_id, project_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to cancel job",
        )

    return {
        "render_job_id": str(render_job_id),
        "status": "cancelled",
    }


# Retry Render Job
@router.post("/projects/{project_id}/renders/{render_job_id}/retry")
async def retry_render_job(
    project_id: UUID,
    render_job_id: UUID,
    project: Project = Depends(get_project),
    render_job: RenderJob = Depends(get_render_job),
):
    """Retry a failed or cancelled render job."""
    render_job_service = get_render_job_service()

    if render_job.status not in (RenderJobStatus.FAILED, RenderJobStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only retry failed or cancelled jobs. Current status: {render_job.status.value}",
        )

    new_job = await render_job_service.retry_job(render_job_id, project_id)

    if not new_job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create retry job",
        )

    # Queue the new job
    try:
        if not settings.CELERY_ENABLED:
            raise RuntimeError("Celery queue disabled")
        from app.workers.render_tasks import render_preview_job, render_export_job
        if new_job.job_type == RenderJobType.PREVIEW:
            render_preview_job.delay(str(new_job.timeline_id), str(new_job.id))
        else:
            if new_job.preset_id:
                render_export_job.delay(str(new_job.timeline_id), str(new_job.id), str(new_job.preset_id))
    except Exception:
        # Run synchronously for local dev
        if new_job.job_type == RenderJobType.PREVIEW:
            preview_service = get_preview_service()
            import asyncio
            asyncio.create_task(preview_service.execute_preview_render(new_job.id))
        else:
            export_service = get_export_service()
            import asyncio
            asyncio.create_task(export_service.execute_export_render(new_job.id))

    return {
        "render_job_id": str(new_job.id),
        "status": "queued",
    }


# Delete Render Job
@router.delete("/projects/{project_id}/renders/{render_job_id}/delete")
async def delete_render_job(
    project_id: UUID,
    render_job_id: UUID,
    project: Project = Depends(get_project),
    render_job: RenderJob = Depends(get_render_job),
):
    """Delete a render job and its output file."""
    render_job_service = get_render_job_service()

    success = await render_job_service.delete_job(render_job_id, project_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete job",
        )

    return {
        "render_job_id": str(render_job_id),
        "status": "deleted",
    }


# List Render Presets
@router.get("/render-presets")
async def list_render_presets(
    current_user: User = Depends(get_current_user),
):
    """List all available render presets."""
    render_job_service = get_render_job_service()

    presets = await render_job_service.list_presets()

    return {
        "presets": [
            {
                "id": str(p.id),
                "name": p.name,
                "platform": p.platform.value,
                "width": p.width,
                "height": p.height,
                "fps": p.fps,
                "video_codec": p.video_codec,
                "video_bitrate": p.video_bitrate,
                "crf": p.crf,
                "preset": p.preset,
                "audio_codec": p.audio_codec,
                "audio_bitrate": p.audio_bitrate,
                "pixel_format": p.pixel_format,
                "container": p.container,
                "is_default": p.is_default,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in presets
        ]
    }


# Get Render Preset
@router.get("/render-presets/{preset_id}")
async def get_render_preset(
    preset_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Get a specific render preset."""
    render_job_service = get_render_job_service()

    preset = await render_job_service.get_preset(preset_id)

    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preset not found",
        )

    return {
        "id": str(preset.id),
        "name": preset.name,
        "platform": preset.platform.value,
        "width": preset.width,
        "height": preset.height,
        "fps": preset.fps,
        "video_codec": preset.video_codec,
        "video_bitrate": preset.video_bitrate,
        "crf": preset.crf,
        "preset": preset.preset,
        "audio_codec": preset.audio_codec,
        "audio_bitrate": preset.audio_bitrate,
        "pixel_format": preset.pixel_format,
        "container": preset.container,
        "is_default": preset.is_default,
        "created_at": preset.created_at.isoformat() if preset.created_at else None,
    }
