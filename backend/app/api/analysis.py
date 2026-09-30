from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User, AnalysisJob, MediaAsset, Project, VideoShot, VideoScene, Keyframe, TranscriptSegment, AudioAnalysis
from app.services.media_analysis import get_media_analysis_service
from app.services.analysis_job import get_analysis_job_service

router = APIRouter()


async def get_media_asset(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MediaAsset:
    """Get media asset and verify ownership."""
    result = await db.execute(
        select(MediaAsset)
        .join(Project)
        .where(
            MediaAsset.id == media_id,
            Project.user_id == current_user.id,
        )
    )
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media asset not found",
        )
    return media


# Analysis job endpoints
@router.post(
    "/media/{media_id}/analyze",
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_analysis(
    media_id: UUID,
    analysis_types: List[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start analysis for a media asset."""
    # Verify media ownership
    media = await get_media_asset(media_id, db, current_user)
    
    service = get_media_analysis_service()
    result = await service.analyze_media(media_id, analysis_types)
    
    return {
        "media_asset_id": str(media_id),
        "jobs_created": len(result.get("jobs", {})),
        "jobs": result.get("jobs", {}),
    }


@router.get(
    "/media/{media_id}/analysis",
)
async def get_analysis_status(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get analysis status for a media asset."""
    # Verify media ownership
    await get_media_asset(media_id, db, current_user)
    
    service = get_media_analysis_service()
    return await service.get_analysis_status(media_id)


@router.get(
    "/media/{media_id}/analysis/results",
)
async def get_analysis_results(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all analysis results for a media asset."""
    # Verify media ownership
    await get_media_asset(media_id, db, current_user)
    
    service = get_media_analysis_service()
    return await service.get_analysis_results(media_id)


# Shots endpoints
@router.get(
    "/media/{media_id}/shots",
)
async def get_shots(
    media_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all shots for a media asset."""
    # Verify media ownership
    await get_media_asset(media_id, db, current_user)
    
    result = await db.execute(
        select(VideoShot)
        .where(VideoShot.media_asset_id == media_id)
        .order_by(VideoShot.shot_index)
        .offset(skip)
        .limit(limit)
    )
    shots = result.scalars().all()
    
    return {
        "media_asset_id": str(media_id),
        "shots": [
            {
                "id": str(s.id),
                "start_time": s.start_time,
                "end_time": s.end_time,
                "duration": s.duration,
                "shot_index": s.shot_index,
                "detection_method": s.detection_method,
                "confidence": s.confidence,
            }
            for s in shots
        ],
    }


@router.get(
    "/media/{media_id}/shots/{shot_id}",
)
async def get_shot(
    media_id: UUID,
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific shot."""
    # Verify media ownership
    await get_media_asset(media_id, db, current_user)
    
    result = await db.execute(
        select(VideoShot).where(
            VideoShot.id == shot_id,
            VideoShot.media_asset_id == media_id,
        )
    )
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shot not found",
        )
    
    return {
        "id": str(shot.id),
        "start_time": shot.start_time,
        "end_time": shot.end_time,
        "duration": shot.duration,
        "shot_index": shot.shot_index,
        "detection_method": shot.detection_method,
        "confidence": shot.confidence,
    }


# Scenes endpoints
@router.get(
    "/media/{media_id}/scenes",
)
async def get_scenes(
    media_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all scenes for a media asset."""
    # Verify media ownership
    await get_media_asset(media_id, db, current_user)
    
    result = await db.execute(
        select(VideoScene)
        .where(VideoScene.media_asset_id == media_id)
        .order_by(VideoScene.scene_index)
        .offset(skip)
        .limit(limit)
    )
    scenes = result.scalars().all()
    
    return {
        "media_asset_id": str(media_id),
        "scenes": [
            {
                "id": str(s.id),
                "start_time": s.start_time,
                "end_time": s.end_time,
                "duration": s.end_time - s.start_time,
                "scene_index": s.scene_index,
                "label": s.label,
                "description": s.description,
                "confidence": s.confidence,
                "detection_method": s.detection_method,
            }
            for s in scenes
        ],
    }


@router.get(
    "/media/{media_id}/scenes/{scene_id}",
)
async def get_scene(
    media_id: UUID,
    scene_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific scene."""
    # Verify media ownership
    await get_media_asset(media_id, db, current_user)
    
    result = await db.execute(
        select(VideoScene).where(
            VideoScene.id == scene_id,
            VideoScene.media_asset_id == media_id,
        )
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scene not found",
        )
    
    return {
        "id": str(scene.id),
        "start_time": scene.start_time,
        "end_time": scene.end_time,
        "duration": scene.end_time - scene.start_time,
        "scene_index": scene.scene_index,
        "label": scene.label,
        "description": scene.description,
        "confidence": scene.confidence,
        "detection_method": scene.detection_method,
    }


# Keyframes endpoints
@router.get(
    "/media/{media_id}/keyframes",
)
async def get_keyframes(
    media_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all keyframes for a media asset."""
    # Verify media ownership
    await get_media_asset(media_id, db, current_user)
    
    result = await db.execute(
        select(Keyframe)
        .where(Keyframe.media_asset_id == media_id)
        .order_by(Keyframe.timestamp)
        .offset(skip)
        .limit(limit)
    )
    keyframes = result.scalars().all()
    
    return {
        "media_asset_id": str(media_id),
        "keyframes": [
            {
                "id": str(k.id),
                "timestamp": k.timestamp,
                "frame_index": k.frame_index,
                "storage_key": k.storage_key,
                "width": k.width,
                "height": k.height,
                "shot_index": k.shot_index,
            }
            for k in keyframes
        ],
    }


# Transcript endpoints
@router.get(
    "/media/{media_id}/transcript",
)
async def get_transcript(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get transcript for a media asset."""
    # Verify media ownership
    await get_media_asset(media_id, db, current_user)
    
    result = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.media_asset_id == media_id)
        .order_by(TranscriptSegment.start_time)
    )
    transcript = result.scalars().all()
    
    return {
        "media_asset_id": str(media_id),
        "transcript": [
            {
                "id": str(t.id),
                "start_time": t.start_time,
                "end_time": t.end_time,
                "text": t.text,
                "confidence": t.confidence,
                "speaker_id": t.speaker_id,
                "language": t.language,
            }
            for t in transcript
        ],
    }


# Audio analysis endpoint
@router.get(
    "/media/{media_id}/audio",
)
async def get_audio_analysis(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get audio analysis for a media asset."""
    # Verify media ownership
    await get_media_asset(media_id, db, current_user)
    
    result = await db.execute(
        select(AudioAnalysis).where(AudioAnalysis.media_asset_id == media_id)
    )
    audio = result.scalar_one_or_none()
    
    if not audio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio analysis not found. Run audio analysis first.",
        )
    
    return {
        "media_asset_id": str(media_id),
        "audio": {
            "has_audio": audio.has_audio,
            "audio_streams": audio.audio_streams,
            "sample_rate": audio.sample_rate,
            "channels": audio.channels,
            "codec": audio.codec,
            "bitrate": audio.bitrate,
            "duration": audio.duration,
        } if audio else None,
    }


# Analysis job endpoints
@router.get(
    "/media/{media_id}/jobs",
)
async def get_analysis_jobs(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all analysis jobs for a media asset."""
    # Verify media ownership
    await get_media_asset(media_id, db, current_user)
    
    service = get_analysis_job_service()
    jobs = await service.get_jobs_for_media(media_id)
    
    return {
        "media_asset_id": str(media_id),
        "jobs": [
            {
                "id": str(job.id),
                "analysis_type": job.analysis_type.value,
                "status": job.status.value,
                "progress": job.progress,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
            }
            for job in jobs
        ],
    }


@router.post(
    "/jobs/{job_id}/retry",
)
async def retry_analysis_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry a failed analysis job."""
    # Verify job ownership through media asset
    result = await db.execute(
        select(AnalysisJob)
        .join(MediaAsset)
        .join(Project)
        .where(
            AnalysisJob.id == job_id,
            Project.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis job not found",
        )
    
    if job.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retry failed jobs",
        )
    
    service = get_analysis_job_service()
    success = await service.retry_job(job_id)
    
    return {
        "job_id": str(job_id),
        "retry_success": success,
    }
