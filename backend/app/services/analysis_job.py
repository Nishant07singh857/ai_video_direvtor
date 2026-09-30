import uuid
from datetime import datetime, UTC
from typing import Optional, Callable, Awaitable

from sqlalchemy import select
from app.models import AnalysisJob, AnalysisStatus

from app.core import database


class AnalysisJobService:
    """Service for managing analysis job lifecycle.
    
    This service handles the PENDING -> RUNNING -> COMPLETED/FAILED state machine
    for analysis jobs. It is designed to be compatible with future Redis/Celery
    integration while working locally without a message queue.
    """
    
    def __init__(self):
        self._task_handlers: dict[str, Callable[[uuid.UUID], Awaitable[bool]]] = {}

    def register_handler(
        self,
        analysis_type: str,
        handler: Callable[[uuid.UUID], Awaitable[bool]],
    ) -> None:
        """Register or replace the handler for an analysis type."""
        self._task_handlers[analysis_type] = handler
    
    
    async def create_job(
        self,
        media_asset_id: uuid.UUID,
        analysis_type: str,
    ) -> AnalysisJob:
        """Create a new analysis job in PENDING state."""
        async with database.async_session_maker() as db:
            job = AnalysisJob(
                media_asset_id=media_asset_id,
                analysis_type=analysis_type,
                status=AnalysisStatus.PENDING,
                progress=0,
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
            return job
    
    async def get_job(self, job_id: uuid.UUID) -> Optional[AnalysisJob]:
        """Get a job by ID."""
        async with database.async_session_maker() as db:
            result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
            return result.scalar_one_or_none()
    
    async def get_jobs_for_media(
        self,
        media_asset_id: uuid.UUID,
    ) -> list[AnalysisJob]:
        """Get all analysis jobs for a media asset."""
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(AnalysisJob)
                .where(AnalysisJob.media_asset_id == media_asset_id)
                .order_by(AnalysisJob.created_at.desc())
            )
            return result.scalars().all()
    
    async def start_job(self, job_id: uuid.UUID) -> bool:
        """Mark a job as RUNNING."""
        async with database.async_session_maker() as db:
            result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return False
            
            if job.status != AnalysisStatus.PENDING:
                return False
            
            job.status = AnalysisStatus.RUNNING
            job.started_at = datetime.now(UTC)
            job.progress = 0
            await db.commit()
            return True
    
    async def update_progress(self, job_id: uuid.UUID, progress: int) -> bool:
        """Update job progress (0-100)."""
        async with database.async_session_maker() as db:
            result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job or job.status != AnalysisStatus.RUNNING:
                return False
            
            job.progress = max(0, min(100, progress))
            await db.commit()
            return True
    
    async def complete_job(self, job_id: uuid.UUID) -> bool:
        """Mark a job as COMPLETED."""
        async with database.async_session_maker() as db:
            result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return False
            
            job.status = AnalysisStatus.COMPLETED
            job.progress = 100
            job.completed_at = datetime.now(UTC)
            await db.commit()
            return True
    
    async def fail_job(self, job_id: uuid.UUID, error_message: str) -> bool:
        """Mark a job as FAILED with error message."""
        async with database.async_session_maker() as db:
            result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return False
            
            job.status = AnalysisStatus.FAILED
            job.error_message = error_message
            job.completed_at = datetime.now(UTC)
            await db.commit()
            return True
    
    async def run_job(self, job_id: uuid.UUID) -> bool:
        """Execute a job using its registered handler.
        
        This is the main entry point for processing a job. It handles the
        PENDING -> RUNNING -> COMPLETED/FAILED state transitions.
        """
        # Get job and verify it's pending
        async with database.async_session_maker() as db:
            result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return False
            
            if job.status != AnalysisStatus.PENDING:
                return False
            
            analysis_type = job.analysis_type.value if hasattr(job.analysis_type, "value") else str(job.analysis_type)
            media_asset_id = job.media_asset_id
        
        # Check if we have a handler for this analysis type
        if analysis_type not in self._task_handlers:
            await self.fail_job(job_id, f"No handler registered for analysis type: {analysis_type}")
            return False
        
        # Start the job
        if not await self.start_job(job_id):
            return False
        
        try:
            # Execute the handler
            handler = self._task_handlers[analysis_type]
            success = await handler(media_asset_id)
            
            if success:
                await self.complete_job(job_id)
            else:
                await self.fail_job(job_id, "Handler returned False")
            
            return success
            
        except Exception as e:
            await self.fail_job(job_id, str(e))
            return False
    
    async def retry_job(self, job_id: uuid.UUID) -> bool:
        """Retry a failed job by resetting it to PENDING."""
        async with database.async_session_maker() as db:
            result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return False
            
            if job.status != AnalysisStatus.FAILED:
                return False
            
            job.status = AnalysisStatus.PENDING
            job.progress = 0
            job.error_message = None
            job.started_at = None
            job.completed_at = None
            await db.commit()
            return True


# Global instance
_analysis_job_service: Optional[AnalysisJobService] = None


def get_analysis_job_service() -> AnalysisJobService:
    global _analysis_job_service
    if _analysis_job_service is None:
        _analysis_job_service = AnalysisJobService()
    return _analysis_job_service

