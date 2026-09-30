"""
Preview rendering service.
Handles fast, low-resolution preview renders.
"""

import uuid
import os
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from sqlalchemy import select, update

from app.core import database
from app.models import Project, Timeline, TimelineStatus, RenderJob, RenderPreset, RenderJobType, RenderJobStatus, MediaAsset
from video_engine.rendering.ffmpeg_renderer import create_ffmpeg_renderer
from video_engine.rendering.timeline_to_ffmpeg import TimelineCompiler, ResolvedClip
from video_engine.rendering.preview import get_preview_settings
from app.services.storage import get_storage_service
from app.core.timeline import normalize_timeline, validate_timeline
from app.core.config import settings


@dataclass
class PreviewResult:
    """Result of a preview render."""
    success: bool
    render_job: Optional[RenderJob] = None
    output_path: Optional[str] = None
    error: Optional[str] = None


class PreviewService:
    """Service for generating preview renders."""

    def __init__(self):
        self._compiler = TimelineCompiler()
        self._renderer = create_ffmpeg_renderer(
            settings.FFMPEG_PATH or "ffmpeg",
            settings.FFPROBE_PATH or "ffprobe",
        )
        self._storage = get_storage_service()

    async def create_preview_job(
        self,
        project_id: uuid.UUID,
        timeline_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PreviewResult:
        """Create and queue a preview render job."""
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
                return PreviewResult(
                    success=False,
                    error="Project not found or access denied",
                )

            # Get timeline
            timeline_result = await db.execute(
                select(Timeline).where(
                    Timeline.id == timeline_id,
                    Timeline.project_id == project_id,
                )
            )
            timeline = timeline_result.scalar_one_or_none()
            if not timeline:
                return PreviewResult(
                    success=False,
                    error="Timeline not found",
                )

            # Get preview preset
            preset_result = await db.execute(
                select(RenderPreset).where(
                    RenderPreset.name == "Preview (Fast)",
                )
            )
            preset = preset_result.scalar_one_or_none()
            if not preset:
                return PreviewResult(
                    success=False,
                    error="Preview preset not found",
                )

            # Create render job
            render_job = RenderJob(
                project_id=project_id,
                timeline_id=timeline_id,
                job_type=RenderJobType.PREVIEW,
                preset_id=preset.id,
                status=RenderJobStatus.QUEUED,
                progress=0,
            )
            db.add(render_job)
            await db.commit()
            await db.refresh(render_job)

            return PreviewResult(
                success=True,
                render_job=render_job,
            )

    async def execute_preview_render(
        self,
        render_job_id: uuid.UUID,
        progress_callback: Optional[callable] = None,
    ) -> PreviewResult:
        """Execute the preview render synchronously (for local dev)."""
        async with database.async_session_maker() as db:
            # Get render job
            job_result = await db.execute(
                select(RenderJob).where(RenderJob.id == render_job_id)
            )
            render_job = job_result.scalar_one_or_none()
            if not render_job:
                return PreviewResult(success=False, error="Render job not found")

            # Claim atomically. A duplicate Celery delivery must not execute the same job.
            claim = await db.execute(
                update(RenderJob)
                .where(RenderJob.id == render_job_id, RenderJob.status == RenderJobStatus.QUEUED)
                .values(status=RenderJobStatus.RUNNING, started_at=datetime.now(UTC), progress=0,
                        error_message=None)
            )
            await db.commit()
            if claim.rowcount != 1:
                await db.refresh(render_job)
                return PreviewResult(success=False, render_job=render_job,
                                     error=f"Render job is not queued (status: {render_job.status.value})")
            await db.refresh(render_job)

            output_storage_key: Optional[str] = None
            try:
                # Get timeline
                timeline_result = await db.execute(
                    select(Timeline).where(Timeline.id == render_job.timeline_id)
                )
                timeline = timeline_result.scalar_one_or_none()
                if not timeline:
                    raise ValueError("Timeline not found")

                canonical_timeline = normalize_timeline(timeline.timeline_json)
                timeline_errors = validate_timeline(canonical_timeline)
                if timeline_errors:
                    raise ValueError("Timeline validation failed: " + "; ".join(timeline_errors))
                timeline.timeline_json = canonical_timeline
                # Resolve clips
                resolved_clips = await self._resolve_clips(canonical_timeline, render_job.project_id, db)

                if not resolved_clips:
                    raise ValueError("No valid clips in timeline")

                # Prepare output path
                output_storage_key = f"projects/{render_job.project_id}/renders/{render_job.id}/preview.mp4"
                output_path = self._storage.get_path(output_storage_key)

                # Get preview settings
                settings = get_preview_settings().to_dict()

                # Compile FFmpeg command
                compile_result = self._compiler.compile(
                    timeline_json=canonical_timeline,
                    resolved_clips=resolved_clips,
                    output_settings=settings,
                )

                # Store FFmpeg command
                render_job.ffmpeg_cmd = " ".join([
                    "ffmpeg", "-y",
                    *[opt for clip_opts in compile_result.ffmpeg_inputs.input_options for opt in clip_opts],
                    *[f"-i {inp}" for inp in compile_result.ffmpeg_inputs.inputs],
                    f"-filter_complex {compile_result.ffmpeg_inputs.filter_complex}",
                    *compile_result.ffmpeg_inputs.output_mapping,
                    *compile_result.ffmpeg_inputs.output_options,
                    output_path,
                ])
                await db.commit()

                # Progress wrapper
                async def progress_wrapper(prog):
                    progress = max(0, min(99, int(prog.progress_percent)))
                    state = await db.execute(
                        select(RenderJob.status).where(RenderJob.id == render_job.id)
                    )
                    current_status = state.scalar_one_or_none()
                    if current_status == RenderJobStatus.CANCELLED:
                        self._renderer.cancel()
                        return
                    if current_status != RenderJobStatus.RUNNING:
                        return
                    await db.execute(update(RenderJob).where(
                        RenderJob.id == render_job.id, RenderJob.status == RenderJobStatus.RUNNING
                    ).values(progress=progress))
                    await db.commit()
                    render_job.progress = progress
                    if progress_callback:
                        callback_result = progress_callback(prog)
                        if hasattr(callback_result, "__await__"):
                            await callback_result

                # Execute render
                result = await self._renderer.render(
                    inputs=compile_result.ffmpeg_inputs.inputs,
                    input_options=compile_result.ffmpeg_inputs.input_options,
                    filter_complex=compile_result.ffmpeg_inputs.filter_complex,
                    output_mapping=compile_result.ffmpeg_inputs.output_mapping,
                    output_options=compile_result.ffmpeg_inputs.output_options,
                    output_path=output_path,
                    total_duration=compile_result.total_duration,
                    progress_callback=progress_wrapper,
                )

                if result.success:
                    # Update render job
                    transition = await db.execute(update(RenderJob).where(
                        RenderJob.id == render_job.id, RenderJob.status == RenderJobStatus.RUNNING
                    ).values(status=RenderJobStatus.COMPLETED, progress=100,
                             completed_at=datetime.now(UTC), output_storage_key=output_storage_key,
                             output_size=result.file_size, duration=result.duration,
                             width=result.width, height=result.height,
                             fps=int(result.fps) if result.fps else None,
                             video_codec=result.video_codec, bitrate=result.bitrate))
                    if transition.rowcount != 1:
                        await self._cleanup_output(output_storage_key)
                        await db.rollback()
                        await db.refresh(render_job)
                        return PreviewResult(success=False, render_job=render_job,
                                             error=f"Render ended with job status {render_job.status.value}")
                    await db.refresh(render_job)

                    # Update timeline status
                    timeline.status = TimelineStatus.RENDERED
                    timeline.render_path = output_storage_key

                    await db.commit()

                    return PreviewResult(
                        success=True,
                        render_job=render_job,
                        output_path=output_path,
                    )
                else:
                    transition = await db.execute(update(RenderJob).where(
                        RenderJob.id == render_job.id, RenderJob.status == RenderJobStatus.RUNNING
                    ).values(status=RenderJobStatus.FAILED, error_message=result.error_message,
                             completed_at=datetime.now(UTC)))
                    await self._cleanup_output(output_storage_key)
                    await db.commit()
                    await db.refresh(render_job)

                    return PreviewResult(
                        success=False,
                        render_job=render_job,
                        error=result.error_message,
                    )

            except Exception as e:
                transition = await db.execute(update(RenderJob).where(
                    RenderJob.id == render_job.id, RenderJob.status == RenderJobStatus.RUNNING
                ).values(status=RenderJobStatus.FAILED, error_message=str(e),
                         completed_at=datetime.now(UTC)))
                await self._cleanup_output(output_storage_key)
                await db.commit()
                await db.refresh(render_job)

                return PreviewResult(
                    success=False,
                    render_job=render_job,
                    error=str(e),
                )

    async def _cleanup_output(self, storage_key: Optional[str]) -> None:
        """Remove partial output whenever a render does not complete."""
        if not storage_key:
            return
        try:
            await asyncio.to_thread(self._storage.delete, storage_key)
        except Exception:
            # The job status is authoritative; cleanup is best effort.
            pass

    async def _resolve_clips(self, timeline_json: Dict[str, Any], project_id: uuid.UUID, db) -> List[Any]:
        """Resolve timeline clips to source file paths."""
        assets_result = await db.execute(select(MediaAsset).where(MediaAsset.project_id == project_id))
        assets = {str(asset.id): asset for asset in assets_result.scalars().all()}
        resolved = []

        tracks = timeline_json.get("tracks", [])
        for track_index, track in enumerate(tracks):
            track_type = track.get("type", "video")
            try:
                layer_index = int(track.get("track_index", track_index) or track_index)
            except (TypeError, ValueError):
                raise ValueError(f"Track {track.get('id', track_index)} has invalid track_index")
            if layer_index < 0:
                raise ValueError(f"Track {track.get('id', track_index)} has invalid track_index")
            clips = track.get("clips", [])

            for clip_order, clip in enumerate(clips):
                if not isinstance(clip, dict):
                    raise ValueError(f"Invalid clip in track {track.get('id', track_index)}")
                source = clip.get("source", {})
                if not isinstance(source, dict):
                    raise ValueError(f"Clip {clip.get('id', clip_order)} has invalid source")
                asset_id = source.get("media_asset_id")
                storage_key = source.get("storage_key")
                asset = assets.get(str(asset_id)) if asset_id else None
                if asset is None or not storage_key or asset.storage_key != storage_key:
                    raise ValueError(f"Clip {clip.get('id', clip_order)} does not reference project media")
                source_path = self._storage.get_path(asset.storage_key)
                if not os.path.isfile(source_path):
                    raise ValueError(f"Media file is missing for clip {clip.get('id', clip_order)}")
                try:
                    source_start = float(clip.get("source_start", 0))
                    source_end = float(clip.get("source_end", 0))
                    timeline_start = float(clip.get("timeline_start", 0))
                    timeline_end = float(clip.get("timeline_end", 0))
                except (TypeError, ValueError):
                    raise ValueError(f"Clip {clip.get('id', clip_order)} has invalid timing")
                import math
                if not all(math.isfinite(v) for v in (source_start, source_end, timeline_start, timeline_end)):
                    raise ValueError(f"Clip {clip.get('id', clip_order)} has non-finite timing")
                if source_start < 0 or source_end <= source_start or timeline_start < 0 or timeline_end <= timeline_start:
                    raise ValueError(f"Clip {clip.get('id', clip_order)} has invalid timing")
                source_duration = source_end - source_start
                timeline_duration = timeline_end - timeline_start
                for field, declared, actual in (
                    ("source_duration", clip.get("source_duration", source.get("duration")), source_duration),
                    ("timeline_duration", clip.get("timeline_duration", clip.get("duration")), timeline_duration),
                ):
                    if declared is not None:
                        try:
                            declared = float(declared)
                        except (TypeError, ValueError):
                            raise ValueError(f"Clip {clip.get('id', clip_order)} has invalid {field}")
                        if not math.isfinite(declared) or declared <= 0 or not math.isclose(declared, actual, abs_tol=1e-4):
                            raise ValueError(f"Clip {clip.get('id', clip_order)} has inconsistent {field}")
                if asset.duration is not None and source_end > float(asset.duration) + 1e-6:
                    raise ValueError(f"Clip {clip.get('id', clip_order)} exceeds source duration")

                try:
                    sequence_order = int(clip.get("sequence_order", clip_order) or clip_order)
                except (TypeError, ValueError):
                    raise ValueError(f"Clip {clip.get('id', clip_order)} has invalid sequence_order")
                if sequence_order < 0 or not isinstance(clip.get("properties", {}), dict):
                    raise ValueError(f"Clip {clip.get('id', clip_order)} has invalid ordering or properties")
                resolved.append(ResolvedClip(
                    clip_id=str(clip.get("id", str(uuid.uuid4()))),
                    track_type=track_type,
                    source_path=source_path,
                    source_start=source_start,
                    source_end=source_end,
                    source_duration=source_duration,
                    timeline_start=timeline_start,
                    timeline_end=timeline_end,
                    timeline_duration=timeline_duration,
                    sequence_order=sequence_order,
                    properties=clip.get("properties", {}),
                    track_index=layer_index,
                ))

        resolved.sort(key=lambda c: (c.track_type, c.track_index, c.timeline_start, c.sequence_order))
        return resolved


def get_preview_service(): return PreviewService()

