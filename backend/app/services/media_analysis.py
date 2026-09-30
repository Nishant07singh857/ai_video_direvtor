import uuid
from typing import Optional, List, Dict, Any

from app.core import database
from sqlalchemy import select

from app.models import (
    AnalysisStatus,
    AnalysisType,
    AudioAnalysis,
    Keyframe,
    MediaAsset,
    MediaStatus,
    VideoScene,
    VideoShot,
    TranscriptSegment,
)
from app.services.storage import get_storage_service
from video_engine.ingestion.processor import MediaProcessor
from video_engine.shots.detector import ShotBoundary, ShotDetector
from video_engine.shots.keyframe_extractor import KeyframeExtractor
from video_engine.audio.analyzer import AudioAnalyzer
from video_engine.audio.speech import SpeechRecognitionStatus, get_speech_analyzer
from app.services.scene_analyzer import get_scene_analyzer
from app.services.analysis_job import get_analysis_job_service


class MediaAnalysisService:
    """Orchestrates the complete media analysis pipeline.
    
    Coordinates: metadata extraction -> shot detection -> keyframes -> 
    scene analysis -> audio analysis -> speech transcription
    
    Each component is independently testable and replaceable.
    """
    
    def __init__(self):
        self._processor = MediaProcessor()
        self._storage = get_storage_service()
        self._shot_detector = ShotDetector()
        self._keyframe_extractor = KeyframeExtractor()
        self._audio_analyzer = AudioAnalyzer()
        self._scene_analyzer = get_scene_analyzer()
        self._speech_analyzer = get_speech_analyzer()
        self._job_service = get_analysis_job_service()
        
        # Register handlers for each analysis type
        self._register_handlers()
    
    def _register_handlers(self):
        """Register analysis job handlers."""
        self._job_service.register_handler(
            AnalysisType.SHOT_DETECTION.value,
            self._handle_shot_detection
        )
        self._job_service.register_handler(
            AnalysisType.KEYFRAME_EXTRACTION.value,
            self._handle_keyframe_extraction
        )
        self._job_service.register_handler(
            AnalysisType.SCENE_DETECTION.value,
            self._handle_scene_detection
        )
        self._job_service.register_handler(
            AnalysisType.AUDIO_ANALYSIS.value,
            self._handle_audio_analysis
        )
        self._job_service.register_handler(
            AnalysisType.SPEECH_TRANSCRIPTION.value,
            self._handle_speech_transcription
        )
    
    # ============================================================
    # Individual Analysis Handlers
    # ============================================================
    
    async def _handle_shot_detection(self, media_asset_id: uuid.UUID) -> bool:
        """Handler for shot detection analysis job."""
        async with database.async_session_maker() as db:
            # Get media asset
            result = await db.execute(select(MediaAsset).where(MediaAsset.id == media_asset_id))
            media = result.scalar_one_or_none()
            if not media:
                return False
            
            # Update media status
            media.status = MediaStatus.PROCESSING
            await db.commit()
            
            try:
                # Get file path
                from app.services.storage import get_storage_service
                storage = get_storage_service()
                file_path = storage.get_path(media.storage_key)

                metadata = await self._processor.extract_metadata(file_path)
                media.duration = metadata.duration
                media.width = metadata.width
                media.height = metadata.height
                media.fps = metadata.fps
                media.video_codec = metadata.video_codec
                media.audio_codec = metadata.audio_codec
                media.bitrate = metadata.bitrate
                await db.commit()
                
                # Detect shots
                detector = ShotDetector()
                boundaries = await detector.detect_shots(file_path)
                
                if not boundaries:
                    # Fallback: single shot for entire video
                    async with database.async_session_maker() as db2:
                        result2 = await db2.execute(select(MediaAsset).where(MediaAsset.id == media_asset_id))
                        media2 = result2.scalar_one_or_none()
                        if media2 and media2.duration:
                            boundaries = [ShotBoundary(
                                start_time=0.0,
                                end_time=media2.duration,
                                duration=media2.duration,
                                shot_index=0,
                                detection_method="single_shot_fallback",
                            )]
                
                # Save shots to database
                async with database.async_session_maker() as db3:
                    result3 = await db3.execute(select(MediaAsset).where(MediaAsset.id == media_asset_id))
                    media3 = result3.scalar_one_or_none()
                    if media3:
                        for boundary in boundaries:
                            shot = VideoShot(
                                media_asset_id=media_asset_id,
                                start_time=boundary.start_time,
                                end_time=boundary.end_time,
                                duration=boundary.duration,
                                shot_index=boundary.shot_index,
                                detection_method=boundary.detection_method,
                                confidence=boundary.confidence,
                            )
                            db3.add(shot)
                        await db3.commit()
                
                return True
                
            except Exception as e:
                async with database.async_session_maker() as db_err:
                    result_err = await db_err.execute(select(MediaAsset).where(MediaAsset.id == media_asset_id))
                    media_err = result_err.scalar_one_or_none()
                    if media_err:
                        media_err.status = MediaStatus.FAILED
                        media_err.error_message = f"Shot detection failed: {str(e)}"
                        await db_err.commit()
                return False
    
    async def _handle_keyframe_extraction(self, media_asset_id: uuid.UUID) -> bool:
        """Handler for keyframe extraction analysis job."""
        async with database.async_session_maker() as db:
            result = await db.execute(select(MediaAsset).where(MediaAsset.id == media_asset_id))
            media = result.scalar_one_or_none()
            if not media:
                return False
            
            # Get shots
            shots_result = await db.execute(
                select(VideoShot).where(VideoShot.media_asset_id == media_asset_id)
                .order_by(VideoShot.shot_index)
            )
            shots = shots_result.scalars().all()
            
            if not shots:
                return False
            
            try:
                from app.services.storage import get_storage_service
                storage = get_storage_service()
                file_path = storage.get_path(media.storage_key)
                
                # Extract keyframes for each shot
                extractor = self._keyframe_extractor
                output_dir = storage.get_path(
                    f"projects/{media.project_id}/analysis/{media.id}/keyframes"
                )
                
                for shot in shots:
                    keyframes = await extractor.extract_keyframes_for_shot(
                        video_path=storage.get_path(media.storage_key),
                        shot_start=shot.start_time,
                        shot_end=shot.end_time,
                        shot_index=shot.shot_index,
                        output_dir=output_dir,
                    )
                    
                    # Save keyframes
                    async with database.async_session_maker() as db2:
                        for kf in keyframes:
                            keyframe = Keyframe(
                                media_asset_id=media_asset_id,
                                shot_id=shot.id,
                                timestamp=kf.timestamp,
                                frame_index=kf.frame_index,
                                storage_key=(
                                    f"projects/{media.project_id}/analysis/{media.id}/keyframes/"
                                    f"{kf.storage_key}"
                                ),
                                width=kf.width,
                                height=kf.height,
                            )
                            db2.add(keyframe)
                        await db2.commit()
                
                return True
                
            except Exception as e:
                ...
                return False
    
    async def _handle_scene_detection(self, media_asset_id: uuid.UUID) -> bool:
        """Handler for scene detection analysis job."""
        async with database.async_session_maker() as db:
            result = await db.execute(select(MediaAsset).where(MediaAsset.id == media_asset_id))
            media = result.scalar_one_or_none()
            if not media:
                return False
            
            # Get shots
            shots_result = await db.execute(
                select(VideoShot).where(VideoShot.media_asset_id == media_asset_id)
                .order_by(VideoShot.shot_index)
            )
            shots = shots_result.scalars().all()
            
            if not shots:
                return False
            
            try:
                # Analyze scenes
                shot_boundaries = [
                    {
                        "start_time": s.start_time,
                        "end_time": s.end_time,
                        "duration": s.duration,
                        "shot_index": s.shot_index,
                    }
                    for s in shots
                ]
                
                analyzer = get_scene_analyzer()
                scenes = await analyzer.analyze(
                    video_path=None,  # Not needed for temporal analyzer
                    shot_boundaries=shot_boundaries,
                )
                
                # Save scenes
                for scene in scenes:
                    scene_obj = VideoScene(
                        media_asset_id=media_asset_id,
                        start_time=scene["start_time"],
                        end_time=scene["end_time"],
                        scene_index=scene["scene_index"],
                        label=scene.get("label"),
                        description=scene.get("description"),
                        confidence=scene.get("confidence"),
                        detection_method=scene.get("detection_method", "temporal_grouping"),
                    )
                    db.add(scene_obj)
                
                await db.commit()
                return True
                
            except Exception as e:
                ...
                return False
    
    async def _handle_audio_analysis(self, media_asset_id: uuid.UUID) -> bool:
        """Handler for audio analysis job."""
        async with database.async_session_maker() as db:
            result = await db.execute(select(MediaAsset).where(MediaAsset.id == media_asset_id))
            media = result.scalar_one_or_none()
            if not media:
                return False
            
            try:
                from app.services.storage import get_storage_service
                storage = get_storage_service()
                file_path = storage.get_path(media.storage_key)
                
                analyzer = self._audio_analyzer
                audio_info = await analyzer.analyze(file_path)
                
                # Save audio analysis
                audio_analysis = AudioAnalysis(
                    media_asset_id=media_asset_id,
                    has_audio=audio_info.has_audio,
                    audio_streams=audio_info.audio_streams,
                    sample_rate=audio_info.sample_rate,
                    channels=audio_info.channels,
                    codec=audio_info.codec,
                    bitrate=audio_info.bitrate,
                    duration=audio_info.duration,
                    features={},
                )
                db.add(audio_analysis)
                await db.commit()
                return True
                
            except Exception as e:
                ...
                return False
    
    async def _handle_speech_transcription(self, media_asset_id: uuid.UUID) -> bool:
        """Handler for speech transcription job."""
        async with database.async_session_maker() as db:
            result = await db.execute(select(MediaAsset).where(MediaAsset.id == media_asset_id))
            media = result.scalar_one_or_none()
            if not media:
                return False
            
            # Check if media has audio
            audio_result = await db.execute(
                select(AudioAnalysis).where(AudioAnalysis.media_asset_id == media_asset_id)
            )
            audio = audio_result.scalar_one_or_none()
            
            if not audio or not audio.has_audio:
                # No audio to transcribe
                return True
            
            try:
                from app.services.storage import get_storage_service
                storage = get_storage_service()
                file_path = storage.get_path(media.storage_key)
                
                analyzer = get_speech_analyzer()
                
                if not analyzer.is_available:
                    # Speech analysis not available - mark as unavailable
                    return True
                
                result = await analyzer.transcribe(file_path)
                
                if result.status == SpeechRecognitionStatus.COMPLETED:
                    for segment in result.segments:
                        transcript = TranscriptSegment(
                            media_asset_id=media_asset_id,
                            start_time=segment["start_time"],
                            end_time=segment["end_time"],
                            text=segment["text"],
                            confidence=segment.get("confidence"),
                            speaker_id=segment.get("speaker_id"),
                        )
                        db.add(transcript)
                    await db.commit()
                
                return result.status == SpeechRecognitionStatus.COMPLETED
                
            except Exception as e:
                ...
                return False
    
    # ============================================================
    # High-level Analysis Orchestration
    # ============================================================
    
    async def analyze_media(
        self,
        media_asset_id: uuid.UUID,
        analysis_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run full analysis pipeline for a media asset.
        
        Args:
            media_asset_id: Media asset to analyze
            analysis_types: Specific analysis types to run (None = all)
            
        Returns:
            Dictionary with analysis results summary
        """
        if analysis_types is None:
            analysis_types = [
                AnalysisType.SHOT_DETECTION.value,
                AnalysisType.KEYFRAME_EXTRACTION.value,
                AnalysisType.SCENE_DETECTION.value,
                AnalysisType.AUDIO_ANALYSIS.value,
                AnalysisType.SPEECH_TRANSCRIPTION.value,
            ]
        
        # Create analysis jobs
        jobs = []
        for analysis_type in analysis_types:
            job = await self._job_service.create_job(media_asset_id, analysis_type)
            jobs.append(job)
        
        # Execute jobs sequentially (could be parallelized)
        results = {}
        for job in jobs:
            success = await self._job_service.run_job(job.id)
            result_key = job.analysis_type.value if hasattr(job.analysis_type, "value") else str(job.analysis_type)
            results[result_key] = {
                "job_id": str(job.id),
                "success": success,
            }

        all_success = all(item["success"] for item in results.values())
        async with database.async_session_maker() as db:
            media = await db.get(MediaAsset, media_asset_id)
            if media:
                media.status = MediaStatus.READY if all_success else MediaStatus.FAILED
                if not all_success:
                    failed = [name for name, item in results.items() if not item["success"]]
                    media.error_message = "Analysis failed for: " + ", ".join(failed)
                else:
                    media.error_message = None
                await db.commit()
        
        return {
            "media_asset_id": str(media_asset_id),
            "jobs": results,
        }
    
    async def get_analysis_status(
        self,
        media_asset_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Get analysis status for a media asset."""
        jobs = await self._job_service.get_jobs_for_media(media_asset_id)
        
        return {
            "media_asset_id": str(media_asset_id),
            "jobs": [
                {
                    "id": str(job.id),
                    "analysis_type": job.analysis_type.value if hasattr(job.analysis_type, "value") else str(job.analysis_type),
                    "status": job.status.value,
                    "progress": job.progress,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "error_message": job.error_message,
                }
                for job in jobs
            ],
        }
    
    async def get_analysis_results(
        self,
        media_asset_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Get all analysis results for a media asset."""
        async with database.async_session_maker() as db:
            # Get shots
            shots_result = await db.execute(
                select(VideoShot).where(VideoShot.media_asset_id == media_asset_id)
                .order_by(VideoShot.shot_index)
            )
            shots = shots_result.scalars().all()
            
            # Get scenes
            scenes_result = await db.execute(
                select(VideoScene).where(VideoScene.media_asset_id == media_asset_id)
                .order_by(VideoScene.scene_index)
            )
            scenes = scenes_result.scalars().all()
            
            # Get keyframes
            keyframes_result = await db.execute(
                select(Keyframe).where(Keyframe.media_asset_id == media_asset_id)
                .order_by(Keyframe.timestamp)
            )
            keyframes = keyframes_result.scalars().all()
            
            # Get transcript
            transcript_result = await db.execute(
                select(TranscriptSegment).where(TranscriptSegment.media_asset_id == media_asset_id)
                .order_by(TranscriptSegment.start_time)
            )
            transcript = transcript_result.scalars().all()
            
            # Get audio analysis
            audio_result = await db.execute(
                select(AudioAnalysis).where(AudioAnalysis.media_asset_id == media_asset_id)
            )
            audio = audio_result.scalar_one_or_none()
            
            # Get jobs
            jobs = await self._job_service.get_jobs_for_media(media_asset_id)
            
            return {
                "media_asset_id": str(media_asset_id),
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
                "keyframes": [
                    {
                        "id": str(k.id),
                        "timestamp": k.timestamp,
                        "frame_index": k.frame_index,
                        "storage_key": k.storage_key,
                        "width": k.width,
                        "height": k.height,
                        "shot_id": str(k.shot_id) if k.shot_id else None,
                    }
                    for k in keyframes
                ],
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
                "audio": {
                    "has_audio": audio.has_audio if audio else False,
                    "audio_streams": audio.audio_streams if audio else 0,
                    "sample_rate": audio.sample_rate if audio else None,
                    "channels": audio.channels if audio else None,
                    "codec": audio.codec if audio else None,
                    "bitrate": audio.bitrate if audio else None,
                    "duration": audio.duration if audio else None,
                } if audio else None,
                "jobs": [
                    {
                        "id": str(j.id),
                        "analysis_type": j.analysis_type.value if hasattr(j.analysis_type, "value") else str(j.analysis_type),
                        "status": j.status.value,
                        "progress": j.progress,
                        "error_message": j.error_message,
                    }
                    for j in jobs
                ],
            }


# Singleton instance
_media_analysis_service: Optional["MediaAnalysisService"] = None


_media_analysis_service: Optional[MediaAnalysisService] = None


def get_media_analysis_service() -> MediaAnalysisService:
    global _media_analysis_service
    if _media_analysis_service is None:
        _media_analysis_service = MediaAnalysisService()
    return _media_analysis_service

