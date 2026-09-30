"""
Celery tasks for rendering operations.
These tasks run in background workers to perform preview and export renders.
"""

import uuid
import os
import asyncio
from datetime import datetime, UTC
from celery import shared_task
from sqlalchemy import select

from app.core import database
from app.services.render_job_service import get_render_job_service
from app.services.preview_service import get_preview_service
from app.services.export_service import get_export_service
from app.services.storage import get_storage_service
from app.models import RenderJob, RenderJobStatus


@shared_task(bind=True, name="app.workers.render_tasks.render_preview_job")
def render_preview_job(self, timeline_id: str, render_job_id: str) -> dict:
    """
    Celery task to render a preview.

    Args:
        timeline_id: UUID of the timeline to render
        render_job_id: UUID of the render job record

    Returns:
        Dict with result status
    """
    return asyncio.run(_render_preview_job_async(
        uuid.UUID(timeline_id),
        uuid.UUID(render_job_id),
    ))


async def _render_preview_job_async(timeline_id: uuid.UUID, render_job_id: uuid.UUID) -> dict:
    """Async implementation of preview render."""
    render_job_service = get_render_job_service()
    preview_service = get_preview_service()

    try:
        # Execute preview render
        result = await preview_service.execute_preview_render(render_job_id)

        if result.success:
            return {
                "success": True,
                "render_job_id": str(render_job_id),
                "output_storage_key": result.render_job.output_storage_key,
            }
        else:
            return {
                "success": False,
                "render_job_id": str(render_job_id),
                "error": result.error,
            }

    except Exception as e:
        # Mark job as failed
        await render_job_service.update_job_status(
            render_job_id,
            RenderJobStatus.FAILED,
            error_message=str(e),
        )
        return {
            "success": False,
            "render_job_id": str(render_job_id),
            "error": str(e),
        }


@shared_task(bind=True, name="app.workers.render_tasks.render_export_job")
def render_export_job(self, timeline_id: str, render_job_id: str, preset_id: str) -> dict:
    """
    Celery task to render an export.

    Args:
        timeline_id: UUID of the timeline to render
        render_job_id: UUID of the render job record
        preset_id: UUID of the export preset

    Returns:
        Dict with result status
    """
    return asyncio.run(_render_export_job_async(
        uuid.UUID(timeline_id),
        uuid.UUID(render_job_id),
        uuid.UUID(preset_id),
    ))


async def _render_export_job_async(
    timeline_id: uuid.UUID,
    render_job_id: uuid.UUID,
    preset_id: uuid.UUID,
) -> dict:
    """Async implementation of export render."""
    render_job_service = get_render_job_service()
    export_service = get_export_service()

    try:
        # Execute export render
        result = await export_service.execute_export_render(render_job_id)

        if result.success:
            return {
                "success": True,
                "render_job_id": str(render_job_id),
                "output_storage_key": result.render_job.output_storage_key,
            }
        else:
            return {
                "success": False,
                "render_job_id": str(render_job_id),
                "error": result.error,
            }

    except Exception as e:
        # Mark job as failed
        await render_job_service.update_job_status(
            render_job_id,
            RenderJobStatus.FAILED,
            error_message=str(e),
        )
        return {
            "success": False,
            "render_job_id": str(render_job_id),
            "error": str(e),
        }


@shared_task(name="app.workers.render_tasks.cleanup_old_renders")
def cleanup_old_renders(days: int = 30) -> dict:
    """
    Periodic task to clean up old render files.

    Args:
        days: Delete renders older than this many days

    Returns:
        Dict with cleanup stats
    """
    return asyncio.run(_cleanup_old_renders_async(days))


async def _cleanup_old_renders_async(days: int) -> dict:
    """Async implementation of cleanup."""
    from sqlalchemy import select, and_
    from datetime import timedelta

    storage = get_storage_service()
    cutoff = datetime.now(UTC) - timedelta(days=days)

    async with database.async_session_maker() as db:
        # Find old completed/failed jobs
        result = await db.execute(
            select(RenderJob).where(
                and_(
                    RenderJob.status.in_([RenderJobStatus.COMPLETED, RenderJobStatus.FAILED]),
                    RenderJob.created_at < cutoff,
                )
            )
        )
        old_jobs = result.scalars().all()

        deleted_count = 0
        freed_bytes = 0

        for job in old_jobs:
            if job.output_storage_key:
                try:
                    file_path = storage.get_path(job.output_storage_key)
                    if await asyncio.to_thread(os.path.exists, file_path):
                        file_size = await asyncio.to_thread(os.path.getsize, file_path)
                        await asyncio.to_thread(os.remove, file_path)
                        deleted_count += 1
                        freed_bytes += file_size
                except Exception:
                    ...

            # Delete job record
            await db.delete(job)

        await db.commit()

        return {
            "deleted_jobs": deleted_count,
            "freed_bytes": freed_bytes,
        }


@shared_task(name="app.workers.render_tasks.retry_failed_renders")
def retry_failed_renders(max_retries: int = 0) -> dict:
    """
    Periodic task to retry failed renders.

    Args:
        max_retries: Retained for task compatibility; automatic retries are disabled.

    Returns:
        Dict with retry stats
    """
    return asyncio.run(_retry_failed_renders_async(max_retries))


async def _retry_failed_renders_async(max_retries: int) -> dict:
    """Async implementation of retry."""

    # Rendering retries are an explicit user action.  There is no retry counter
    # on RenderJob, so an automatic periodic retry would otherwise be unbounded.
    return {"retried_jobs": 0, "reason": "automatic retries disabled; retry a job explicitly"}
