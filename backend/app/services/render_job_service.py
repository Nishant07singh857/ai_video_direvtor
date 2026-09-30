"""
Render Job Service.
Manages render job lifecycle, status updates, and coordination with Celery.
"""

import uuid
from datetime import datetime, UTC
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum as PyEnum

from sqlalchemy import select, desc, update
from sqlalchemy.orm import selectinload

from app.core import database
from app.models import RenderJob, RenderJobType, RenderJobStatus, RenderPreset, Project, Timeline
from app.services.storage import get_storage_service


class RenderJobAction(str, PyEnum):
    """Actions that can be performed on a render job."""
    START = "start"
    CANCEL = "cancel"
    RETRY = "retry"
    DELETE = "delete"


@dataclass
class RenderJobInfo:
    """Render job information for API responses."""
    id: uuid.UUID
    project_id: uuid.UUID
    timeline_id: Optional[uuid.UUID]
    job_type: RenderJobType
    status: RenderJobStatus
    progress: int
    output_storage_key: Optional[str]
    output_size: Optional[int]
    duration: Optional[float]
    width: Optional[int]
    height: Optional[int]
    fps: Optional[int]
    video_codec: Optional[str]
    bitrate: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    preset_name: Optional[str] = None
    preset_platform: Optional[str] = None


class RenderJobService:
    """Service for managing render jobs."""

    def __init__(self):
        self._storage = get_storage_service()

    async def create_job(
        self,
        project_id: uuid.UUID,
        timeline_id: uuid.UUID,
        job_type: RenderJobType,
        preset_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[RenderJob]:
        """Create a new render job."""
        async with database.async_session_maker() as db:
            # Verify project ownership
            project_result = await db.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.user_id == user_id,
                )
            )
            project = project_result.scalar_one_or_none()
            if not project:
                return None

            # Verify timeline belongs to project
            timeline_result = await db.execute(
                select(Timeline).where(
                    Timeline.id == timeline_id,
                    Timeline.project_id == project_id,
                )
            )
            timeline = timeline_result.scalar_one_or_none()
            if not timeline:
                return None

            # Verify preset exists
            preset_result = await db.execute(
                select(RenderPreset).where(RenderPreset.id == preset_id)
            )
            preset = preset_result.scalar_one_or_none()
            if not preset:
                return None

            render_job = RenderJob(
                project_id=project_id,
                timeline_id=timeline_id,
                job_type=job_type,
                preset_id=preset_id,
                status=RenderJobStatus.QUEUED,
                progress=0,
            )
            db.add(render_job)
            await db.commit()
            await db.refresh(render_job)

            return render_job

    async def get_job(self, job_id: uuid.UUID, project_id: uuid.UUID) -> Optional[RenderJob]:
        """Get a render job by ID, verifying project ownership."""
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(RenderJob).where(
                    RenderJob.id == job_id,
                    RenderJob.project_id == project_id,
                )
            )
            return result.scalar_one_or_none()

    async def get_job_by_id(self, job_id: uuid.UUID) -> Optional[RenderJob]:
        """Get a render job by ID only (for workers)."""
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(RenderJob).where(RenderJob.id == job_id)
            )
            return result.scalar_one_or_none()

    async def list_jobs(
        self,
        project_id: uuid.UUID,
        job_type: Optional[RenderJobType] = None,
        status: Optional[RenderJobStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[RenderJob]:
        """List render jobs for a project."""
        async with database.async_session_maker() as db:
            query = (
                select(RenderJob)
                .options(selectinload(RenderJob.preset))
                .where(RenderJob.project_id == project_id)
            )

            if job_type:
                query = query.where(RenderJob.job_type == job_type)
            if status:
                query = query.where(RenderJob.status == status)

            query = query.order_by(desc(RenderJob.created_at)).limit(limit).offset(offset)
            result = await db.execute(query)
            return result.scalars().all()

    async def update_job_status(
        self,
        job_id: uuid.UUID,
        status: RenderJobStatus,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
        output_storage_key: Optional[str] = None,
        output_size: Optional[int] = None,
        duration: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[int] = None,
        video_codec: Optional[str] = None,
        bitrate: Optional[int] = None,
    ) -> bool:
        """Update render job status and metadata."""
        async with database.async_session_maker() as db:
            values = {}
            if progress is not None:
                values[RenderJob.progress] = max(0, min(100, progress))
            if error_message is not None:
                values[RenderJob.error_message] = error_message
            for column, value in ((RenderJob.output_storage_key, output_storage_key),
                                  (RenderJob.output_size, output_size), (RenderJob.duration, duration),
                                  (RenderJob.width, width), (RenderJob.height, height),
                                  (RenderJob.fps, fps), (RenderJob.video_codec, video_codec),
                                  (RenderJob.bitrate, bitrate)):
                if value is not None:
                    values[column] = value
            if status == RenderJobStatus.RUNNING:
                values[RenderJob.status] = status
                values[RenderJob.started_at] = datetime.now(UTC)
                condition = RenderJob.status == RenderJobStatus.QUEUED
            elif status == RenderJobStatus.COMPLETED:
                values[RenderJob.status] = status
                values[RenderJob.completed_at] = datetime.now(UTC)
                condition = RenderJob.status == RenderJobStatus.RUNNING
            elif status == RenderJobStatus.FAILED:
                values[RenderJob.status] = status
                values[RenderJob.completed_at] = datetime.now(UTC)
                # A worker can fail before the renderer claims the job (for
                # example, during dependency/bootstrap work).  Permit that
                # queued -> failed transition, but never overwrite a final
                # state or a job claimed by another worker.
                condition = RenderJob.status.in_([RenderJobStatus.QUEUED, RenderJobStatus.RUNNING])
            elif status == RenderJobStatus.CANCELLED:
                values[RenderJob.status] = status
                values[RenderJob.completed_at] = datetime.now(UTC)
                condition = RenderJob.status.in_([RenderJobStatus.QUEUED, RenderJobStatus.RUNNING])
            else:
                values[RenderJob.status] = status
                condition = RenderJob.status.notin_([
                    RenderJobStatus.COMPLETED, RenderJobStatus.FAILED, RenderJobStatus.CANCELLED,
                ])
            result = await db.execute(
                update(RenderJob).where(RenderJob.id == job_id, condition).values(values)
            )
            await db.commit()
            return result.rowcount == 1

    async def claim_job(self, job_id: uuid.UUID) -> bool:
        """Atomically claim a queued job for one worker execution."""
        async with database.async_session_maker() as db:
            result = await db.execute(
                update(RenderJob)
                .where(RenderJob.id == job_id, RenderJob.status == RenderJobStatus.QUEUED)
                .values(status=RenderJobStatus.RUNNING, progress=0, started_at=datetime.now(UTC), error_message=None)
            )
            await db.commit()
            return result.rowcount == 1

    async def cancel_job(self, job_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        """Cancel a render job."""
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(RenderJob).where(
                    RenderJob.id == job_id,
                    RenderJob.project_id == project_id,
                )
            )
            job = result.scalar_one_or_none()
            if not job:
                return False

            if job.status not in (RenderJobStatus.QUEUED, RenderJobStatus.RUNNING):
                return False  # Cannot cancel finished jobs
            result = await db.execute(
                update(RenderJob)
                .where(RenderJob.id == job_id,
                       RenderJob.project_id == project_id,
                       RenderJob.status.in_([RenderJobStatus.QUEUED, RenderJobStatus.RUNNING]))
                .values(status=RenderJobStatus.CANCELLED, completed_at=datetime.now(UTC), progress=job.progress)
            )
            await db.commit()
            return result.rowcount == 1

    async def retry_job(self, job_id: uuid.UUID, project_id: uuid.UUID) -> Optional[RenderJob]:
        """Retry a failed render job by creating a new one with same parameters."""
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(RenderJob).where(
                    RenderJob.id == job_id,
                    RenderJob.project_id == project_id,
                )
            )
            job = result.scalar_one_or_none()
            if not job:
                return None

            if job.status not in (RenderJobStatus.FAILED, RenderJobStatus.CANCELLED):
                return None  # Can only retry failed/cancelled jobs

            # Create new job with same parameters
            new_job = RenderJob(
                project_id=job.project_id,
                timeline_id=job.timeline_id,
                job_type=job.job_type,
                preset_id=job.preset_id,
                status=RenderJobStatus.QUEUED,
                progress=0,
            )
            db.add(new_job)
            await db.commit()
            await db.refresh(new_job)
            return new_job

    async def delete_job(self, job_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        """Delete a render job and its output file."""
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(RenderJob).where(
                    RenderJob.id == job_id,
                    RenderJob.project_id == project_id,
                )
            )
            job = result.scalar_one_or_none()
            if not job:
                return False

            # Delete output file if exists
            if job.output_storage_key:
                try:
                    self._storage.delete(job.output_storage_key)
                except Exception:
                    ... # Ignore storage errors

            # Delete job record
            await db.delete(job)
            await db.commit()
            return True

    async def get_job_info(self, job: RenderJob) -> RenderJobInfo:
        """Convert RenderJob to RenderJobInfo with preset details."""
        preset_name = None
        preset_platform = None
        if job.preset_id:
            try:
                preset = job.preset
                if preset:
                    preset_name = preset.name
                    preset_platform = preset.platform.value if hasattr(preset.platform, "value") else str(preset.platform)
            except Exception:
                async with database.async_session_maker() as db:
                    preset_result = await db.execute(
                        select(RenderPreset).where(RenderPreset.id == job.preset_id)
                    )
                    preset = preset_result.scalar_one_or_none()
                    if preset:
                        preset_name = preset.name
                        preset_platform = preset.platform.value if hasattr(preset.platform, "value") else str(preset.platform)

        return RenderJobInfo(
            id=job.id,
            project_id=job.project_id,
            timeline_id=job.timeline_id,
            job_type=job.job_type,
            status=job.status,
            progress=job.progress,
            output_storage_key=job.output_storage_key,
            output_size=job.output_size,
            duration=job.duration,
            width=job.width,
            height=job.height,
            fps=job.fps,
            video_codec=job.video_codec,
            bitrate=job.bitrate,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            preset_name=preset_name,
            preset_platform=preset_platform,
        )

    async def list_presets(self) -> List[RenderPreset]:
        """List all render presets."""
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(RenderPreset).order_by(RenderPreset.platform, RenderPreset.name)
            )
            return result.scalars().all()

    async def get_preset(self, preset_id: uuid.UUID) -> Optional[RenderPreset]:
        """Get a render preset by ID."""
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(RenderPreset).where(RenderPreset.id == preset_id)
            )
            return result.scalar_one_or_none()


def get_render_job_service(): return RenderJobService()

