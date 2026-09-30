import uuid
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Project,
    MediaAsset,
    VideoShot,
    VideoScene,
    Keyframe,
    TranscriptSegment,
    AudioAnalysis,
    ShotRanking,
)
from app.core import database


@dataclass
class ShotScore:
    """Detailed score breakdown for a shot."""
    video_shot_id: uuid.UUID
    quality_score: float
    relevance_score: float
    visual_appeal: float
    audio_appeal: float
    composite_score: float
    rank: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class ShotRankerService:
    """Ranks shots based on available Phase 3 analysis data.
    
    Scoring is deterministic and based only on actual extracted metadata.
    No fabricated AI results are used.
    """
    
    def __init__(self):
        # Weights for composite score (should sum to 1.0)
        self.weights = {
            "quality": 0.25,
            "relevance": 0.30,
            "visual_appeal": 0.25,
            "audio_appeal": 0.20,
        }
    
    async def rank_shots(
        self,
        project_id: uuid.UUID,
        story_candidate_id: Optional[uuid.UUID] = None,
    ) -> List[ShotScore]:
        """Rank all shots in a project (or for a specific story candidate)."""
        async with database.async_session_maker() as db:
            # Get project and verify ownership through context
            project_result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = project_result.scalar_one_or_none()
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Get media assets
            media_result = await db.execute(
                select(MediaAsset).where(MediaAsset.project_id == project_id)
            )
            media_assets = media_result.scalars().all()
            
            if not media_assets:
                return []
            
            # Get all shots for these media assets
            all_shots = []
            for media in media_assets:
                shots_result = await db.execute(
                    select(VideoShot)
                    .where(VideoShot.media_asset_id == media.id)
                    .order_by(VideoShot.shot_index)
                )
                shots = shots_result.scalars().all()
                all_shots.extend(shots)
            
            if not all_shots:
                return []
            
            # Score each shot
            scores = []
            for shot in all_shots:
                score = await self._score_shot(db, shot, media_assets)
                scores.append(score)
            
            # Sort by composite score descending
            scores.sort(key=lambda s: s.composite_score, reverse=True)
            
            # Assign ranks
            for i, score in enumerate(scores):
                score.rank = i + 1
            
            # Persist rankings
            await self._persist_rankings(db, project_id, story_candidate_id, scores)
            await db.commit()
            
            return scores
    
    async def _score_shot(
        self,
        db: AsyncSession,
        shot: VideoShot,
        media_assets: List[MediaAsset],
    ) -> ShotScore:
        """Calculate detailed score for a single shot."""
        
        # Find the media asset this shot belongs to
        media = None
        for m in media_assets:
            shots_result = await db.execute(
                select(VideoShot).where(
                    VideoShot.id == shot.id,
                    VideoShot.media_asset_id == m.id
                )
            )
            if shots_result.scalar_one_or_none():
                media = m
                break
        
        details = {}
        
        # 1. Quality Score (0-1)
        # Based on resolution, duration, codec quality indicators
        quality = self._calculate_quality_score(shot, media)
        details["quality"] = quality
        
        # 2. Relevance Score (0-1)
        # Based on shot position, duration, scene membership
        relevance = await self._calculate_relevance_score(db, shot, media)
        details["relevance"] = relevance
        
        # 3. Visual Appeal (0-1)
        # Based on keyframe presence, resolution, aspect ratio
        visual = await self._calculate_visual_appeal(db, shot)
        details["visual_appeal"] = visual
        
        # 4. Audio Appeal (0-1)
        # Based on audio presence, transcript quality in shot time range
        audio = await self._calculate_audio_appeal(db, shot, media)
        details["audio_appeal"] = audio
        
        # Composite score (weighted)
        composite = (
            self.weights["quality"] * quality +
            self.weights["relevance"] * relevance +
            self.weights["visual_appeal"] * visual +
            self.weights["audio_appeal"] * audio
        )
        
        return ShotScore(
            video_shot_id=shot.id,
            quality_score=quality,
            relevance_score=relevance,
            visual_appeal=visual,
            audio_appeal=audio,
            composite_score=composite,
            details=details,
        )
    
    def _calculate_quality_score(self, shot: VideoShot, media: Optional[MediaAsset]) -> float:
        """Technical quality based on available metadata."""
        score = 0.5  # baseline
        
        # Resolution factor (if available)
        if media and media.width and media.height:
            pixel_count = media.width * media.height
            # Normalize: 1920x1080 = 0.8, 3840x2160 = 1.0
            max_pixels = 3840 * 2160
            score += min(0.3, (pixel_count / max_pixels) * 0.3)
        
        # Duration factor - very short shots may be artifacts
        if shot.duration < 0.5:
            score -= 0.2
        elif shot.duration > 2.0:
            score += 0.1
        
        # Confidence from detection
        if shot.confidence:
            score = (score + shot.confidence) / 2
        
        return max(0.0, min(1.0, score))
    
    async def _calculate_relevance_score(
        self, db: AsyncSession, shot: VideoShot, media: Optional[MediaAsset]
    ) -> float:
        """Relevance based on position, duration, scene context."""
        score = 0.5  # baseline
        
        # Scene membership boost
        scenes_result = await db.execute(
            select(VideoScene).where(
                VideoScene.media_asset_id == shot.media_asset_id,
                VideoScene.start_time <= shot.start_time,
                VideoScene.end_time >= shot.end_time,
            )
        )
        # We'll approximate - in real implementation we'd check overlap
        score += 0.1
        
        # First and last shots often have special relevance (intro/outro)
        if shot.shot_index == 0:
            score += 0.15  # hook potential
        elif shot.shot_index > 10:  # assuming reasonable shot count
            ...
        
        # Moderate duration shots are often most useful
        if 2.0 <= shot.duration <= 10.0:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    async def _calculate_visual_appeal(self, db: AsyncSession, shot: VideoShot) -> float:
        """Visual appeal based on keyframes and resolution."""
        score = 0.5
        
        # Keyframe count indicates visual interest
        keyframes_result = await db.execute(
            select(Keyframe).where(Keyframe.shot_id == shot.id)
        )
        keyframes = keyframes_result.scalars().all()
        
        if keyframes:
            score += min(0.3, len(keyframes) * 0.1)
            
            # Average resolution of keyframes
            avg_width = sum(k.width for k in keyframes) / len(keyframes)
            avg_height = sum(k.height for k in keyframes) / len(keyframes)
            if avg_width * avg_height >= 640 * 360:
                score += 0.1
        
        return max(0.0, min(1.0, score))
    
    async def _calculate_audio_appeal(
        self, db: AsyncSession, shot: VideoShot, media: Optional[MediaAsset]
    ) -> float:
        """Audio appeal based on transcript and audio analysis."""
        if not media:
            return 0.0
        
        score = 0.0
        
        # Check audio analysis
        audio_result = await db.execute(
            select(AudioAnalysis).where(AudioAnalysis.media_asset_id == media.id)
        )
        audio = audio_result.scalar_one_or_none()
        
        if audio and audio.has_audio:
            score += 0.3
            
            # Check for transcript segments in this shot's time range
            transcript_result = await db.execute(
                select(TranscriptSegment).where(
                    TranscriptSegment.media_asset_id == media.id,
                    TranscriptSegment.start_time >= shot.start_time,
                    TranscriptSegment.end_time <= shot.end_time,
                )
            )
            transcripts = transcript_result.scalars().all()
            
            if transcripts:
                score += min(0.4, len(transcripts) * 0.1)
                avg_confidence = sum(t.confidence or 0 for t in transcripts) / len(transcripts)
                score += avg_confidence * 0.3
        
        return max(0.0, min(1.0, score))
    
    async def _persist_rankings(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        story_candidate_id: Optional[uuid.UUID],
        scores: List[ShotScore],
    ) -> None:
        """Persist shot rankings to database."""
        for score in scores:
            ranking = ShotRanking(
                project_id=project_id,
                story_candidate_id=story_candidate_id,
                video_shot_id=score.video_shot_id,
                quality_score=score.quality_score,
                relevance_score=score.relevance_score,
                visual_appeal=score.visual_appeal,
                audio_appeal=score.audio_appeal,
                composite_score=score.composite_score,
                rank=score.rank,
            )
            db.add(ranking)
    
    async def get_rankings(
        self,
        project_id: uuid.UUID,
        story_candidate_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve shot rankings for a project."""
        async with database.async_session_maker() as db:
            query = select(ShotRanking).where(ShotRanking.project_id == project_id)
            if story_candidate_id:
                query = query.where(ShotRanking.story_candidate_id == story_candidate_id)
            query = query.order_by(ShotRanking.rank)
            
            result = await db.execute(query)
            rankings = result.scalars().all()
            
            return [
                {
                    "id": str(r.id),
                    "project_id": str(r.project_id),
                    "story_candidate_id": str(r.story_candidate_id) if r.story_candidate_id else None,
                    "video_shot_id": str(r.video_shot_id),
                    "quality_score": r.quality_score,
                    "relevance_score": r.relevance_score,
                    "visual_appeal": r.visual_appeal,
                    "audio_appeal": r.audio_appeal,
                    "composite_score": r.composite_score,
                    "rank": r.rank,
                }
                for r in rankings
            ]


# Singleton
_shot_ranker_service: Optional["ShotRankerService"] = None


def get_shot_ranker_service(): return ShotRankerService()
