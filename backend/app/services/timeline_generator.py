import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import select
from app.models import StoryCandidate, Timeline, Project, StoryShot, VideoShot, MediaAsset, TimelineStatus

from app.core import database
from app.core.timeline import normalize_timeline
from video_engine.timeline.builder import TimelineBuilder

class TimelineGeneratorService:
    """Generates renderer-ready timeline JSON from story sequences."""
    
    def __init__(self):
        self.builder = TimelineBuilder()
    
    async def generate_timeline(
        self,
        project_id: uuid.UUID,
        story_candidate_id: uuid.UUID,
    ) -> Timeline:
        """Generate a timeline from a story candidate's planned sequence."""
        async with database.async_session_maker() as db:
            story_result = await db.execute(
                select(StoryCandidate).where(
                    StoryCandidate.id == story_candidate_id,
                    StoryCandidate.project_id == project_id,
                )
            )
            story = story_result.scalar_one_or_none()
            if not story:
                raise ValueError(f"Story candidate {story_candidate_id} not found")
            
            shots_result = await db.execute(
                select(StoryShot)
                .where(StoryShot.story_candidate_id == story_candidate_id)
                .order_by(StoryShot.sequence_order)
            )
            story_shots = shots_result.scalars().all()
            
            if not story_shots:
                raise ValueError("No story shots found for this candidate. Run sequence planning first.")
            
            video_shot_ids = [ss.video_shot_id for ss in story_shots]
            video_shots_result = await db.execute(
                select(VideoShot).where(VideoShot.id.in_(video_shot_ids))
            )
            video_shots = {str(vs.id): vs for vs in video_shots_result.scalars().all()}
            
            media_asset_ids = set(vs.media_asset_id for vs in video_shots.values())
            media_assets_result = await db.execute(
                select(MediaAsset).where(MediaAsset.id.in_(media_asset_ids))
            )
            media_assets = {str(ma.id): ma for ma in media_assets_result.scalars().all()}
            
            timeline_json = self.builder.build_timeline_json(
                project_id=str(story.project_id),
                story_id=str(story.id),
                story_title=story.title,
                story_description=story.description,
                narrative_arc=story.narrative_arc,
                estimated_duration=story.estimated_duration,
                confidence=story.confidence,
                story_shots=story_shots,
                video_shots=video_shots,
                media_assets=media_assets
            )
            timeline_json = normalize_timeline(timeline_json)
            
            validation = self.builder.validate_timeline(timeline_json, video_shots)
            if not validation.is_valid:
                raise ValueError(f"Timeline validation failed: {'; '.join(validation.errors)}")
            
            version_result = await db.execute(
                select(Timeline.version_number)
                .where(Timeline.project_id == project_id)
                .order_by(Timeline.version_number.desc())
            )
            max_version = version_result.scalar() or 0
            next_version = max_version + 1
            
            total_duration = timeline_json.get("total_duration", timeline_json.get("duration", 0.0))
            
            timeline = Timeline(
                project_id=project_id,
                story_candidate_id=story_candidate_id,
                version_number=next_version,
                timeline_json=timeline_json,
                total_duration=total_duration,
                status=TimelineStatus.DRAFT,
            )
            db.add(timeline)
            await db.commit()
            await db.refresh(timeline)
            
            return timeline
    
    def _apply_sanity_checks(self, timeline_json: Dict[str, Any]) -> None:
        for track in timeline_json.get("tracks", []):
            for clip in track.get("clips", []):
                start = clip.get("start_time")
                end = clip.get("end_time")
                dur = clip.get("video_duration")
                
                if start is not None and end is not None:
                    if start > end:
                        clip["start_time"], clip["end_time"] = end, start
                        start, end = clip["start_time"], clip["end_time"]
                    
                    if dur is not None:
                        if clip["start_time"] > dur:
                            clip["start_time"] = dur
                        if clip["end_time"] > dur:
                            clip["end_time"] = dur

    async def generate_timeline_from_swarm(
        self,
        project_id: uuid.UUID,
        enriched_state: Dict[str, Any],
    ) -> Timeline:
        self._apply_sanity_checks(enriched_state)
        
        async with database.async_session_maker() as db:
            version_result = await db.execute(
                select(Timeline.version_number)
                .where(Timeline.project_id == project_id)
                .order_by(Timeline.version_number.desc())
            )
            max_version = version_result.scalar() or 0
            next_version = max_version + 1
            
            canonical_timeline = normalize_timeline(enriched_state)
            total_duration = canonical_timeline.get("total_duration", enriched_state.get("duration", 0.0))
            
            timeline = Timeline(
                project_id=project_id,
                version_number=next_version,
                timeline_json=canonical_timeline,
                total_duration=total_duration,
                status=TimelineStatus.DRAFT,
            )
            db.add(timeline)
            await db.commit()
            await db.refresh(timeline)
            
            return timeline

    async def get_timeline(
        self,
        project_id: uuid.UUID,
        timeline_id: uuid.UUID,
    ) -> Optional[Timeline]:
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(Timeline).where(
                    Timeline.id == timeline_id,
                    Timeline.project_id == project_id,
                )
            )
            return result.scalar_one_or_none()
    
    async def list_timelines(
        self,
        project_id: uuid.UUID,
    ) -> List[Timeline]:
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(Timeline)
                .where(Timeline.project_id == project_id)
                .order_by(Timeline.version_number.desc())
            )
            return result.scalars().all()
    
    async def regenerate_timeline(
        self,
        project_id: uuid.UUID,
        timeline_id: uuid.UUID,
    ) -> Timeline:
        async with database.async_session_maker() as db:
            timeline = await self.get_timeline(project_id, timeline_id)
            if not timeline:
                raise ValueError(f"Timeline {timeline_id} not found")
            
            if not timeline.story_candidate_id:
                raise ValueError("Cannot regenerate timeline without story candidate")
            
            return await self.generate_timeline(project_id, timeline.story_candidate_id)

_timeline_generator_service: Optional["TimelineGeneratorService"] = None

def get_timeline_generator_service(): return TimelineGeneratorService()
