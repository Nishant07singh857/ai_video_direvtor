import uuid
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import database
from app.models import (
    Project,
    StoryCandidate,
    StoryShot,
    StoryShotRole,
    Timeline,
    TranscriptSegment,
    VideoShot,
)


@dataclass
class PlannedSequence:
    """Planned shot sequence for a story."""
    story_candidate_id: uuid.UUID
    story_shots: List[Dict[str, Any]]
    total_duration: float
    shot_count: int


class SequencePlannerService:
    """Plans shot sequences for story candidates.
    
    Assigns narrative roles, orders shots, and creates the final sequence.
    Uses available analysis data to make informed decisions.
    """
    
    def __init__(self):
        ...
    
    async def plan_sequence(
        self,
        project_id: uuid.UUID,
        story_candidate_id: uuid.UUID,
    ) -> PlannedSequence:
        """Plan the shot sequence for a story candidate."""
        async with database.async_session_maker() as db:
            # Verify story candidate
            story_result = await db.execute(
                select(StoryCandidate).where(
                    StoryCandidate.id == story_candidate_id,
                    StoryCandidate.project_id == project_id,
                )
            )
            story = story_result.scalar_one_or_none()
            if not story:
                raise ValueError(f"Story candidate {story_candidate_id} not found in project {project_id}")
            
            # Get all shots for this project
            shots_result = await db.execute(
                select(VideoShot)
                .join(VideoShot.media_asset)
                .where(VideoShot.media_asset.has(project_id=project_id))
                .order_by(VideoShot.start_time)
            )
            all_shots = shots_result.scalars().all()
            
            if not all_shots:
                raise ValueError("No shots available for sequence planning")
            
            # Get transcript segments for narrative alignment
            transcripts_result = await db.execute(
                select(TranscriptSegment)
                .join(TranscriptSegment.media_asset)
                .where(TranscriptSegment.media_asset.has(project_id=project_id))
                .order_by(TranscriptSegment.start_time)
            )
            transcripts = transcripts_result.scalars().all()
            
            # Clear existing story shots for this candidate
            await db.execute(
                StoryShot.__table__.delete().where(StoryShot.story_candidate_id == story_candidate_id)
            )
            
            # Plan sequence based on story structure
            structure = story.narrative_arc.get("structure", "chronological") if story.narrative_arc else "chronological"
            
            if structure == "chronological":
                planned = self._plan_chronological(story, all_shots, transcripts)
            elif structure == "highlight_reel":
                planned = self._plan_highlight_reel(story, all_shots, transcripts)
            elif structure == "emotional_narrative":
                planned = self._plan_emotional_narrative(story, all_shots, transcripts)
            elif structure == "documentary":
                planned = await self._plan_documentary(story, all_shots, transcripts, db)
            elif structure == "educational":
                planned = self._plan_educational(story, all_shots, transcripts)
            else:
                planned = self._plan_chronological(story, all_shots, transcripts)
            
            # Persist story shots
            sequence_order = 0
            for shot_plan in planned["story_shots"]:
                story_shot = StoryShot(
                    story_candidate_id=story_candidate_id,
                    video_shot_id=shot_plan["video_shot_id"],
                    sequence_order=sequence_order,
                    start_time=shot_plan["start_time"],
                    end_time=shot_plan["end_time"],
                    role=StoryShotRole(shot_plan["role"]),
                    reasoning=shot_plan.get("reasoning"),
                    confidence=shot_plan.get("confidence", 0.7),
                )
                db.add(story_shot)
                sequence_order += 1
            
            await db.commit()
            
            return PlannedSequence(
                story_candidate_id=story_candidate_id,
                story_shots=planned["story_shots"],
                total_duration=planned["total_duration"],
                shot_count=len(planned["story_shots"]),
            )
    
    def _plan_chronological(
        self,
        story: StoryCandidate,
        shots: List[VideoShot],
        transcripts: List[TranscriptSegment],
    ) -> Dict[str, Any]:
        """Plan chronological sequence - use all shots in time order."""
        
        # Map transcripts to shots for narrative context
        shot_transcripts = defaultdict(list)
        for ts in transcripts:
            for shot in shots:
                if ts.start_time >= shot.start_time and ts.end_time <= shot.end_time:
                    shot_transcripts[shot.id].append(ts)
        
        story_shots = []
        total_duration = 0.0
        
        for i, shot in enumerate(shots):
            # Assign role based on position
            if i == 0:
                role = StoryShotRole.HOOK
            elif i == len(shots) - 1:
                role = StoryShotRole.RESOLUTION
            elif i < len(shots) // 3:
                role = StoryShotRole.DEVELOPMENT
            elif i > 2 * len(shots) // 3:
                role = StoryShotRole.CLIMAX
            else:
                role = StoryShotRole.DEVELOPMENT
            
            # Check if shot has transcript content
            has_dialog = shot.id in shot_transcripts and len(shot_transcripts[shot.id]) > 0
            
            story_shots.append({
                "video_shot_id": shot.id,
                "start_time": shot.start_time,
                "end_time": shot.end_time,
                "role": role.value,
                "reasoning": f"Chronological position {i+1}/{len(shots)}" + (" with dialogue" if has_dialog else ""),
                "confidence": 0.8,
            })
            
            total_duration += shot.duration or 0
        
        return {"story_shots": story_shots, "total_duration": total_duration}
    
    def _plan_highlight_reel(
        self,
        story: StoryCandidate,
        shots: List[VideoShot],
        transcripts: List[TranscriptSegment],
    ) -> Dict[str, Any]:
        """Plan highlight reel - select best shots."""
        
        # Score shots
        scored = []
        for shot in shots:
            score = (shot.duration or 1) * (shot.confidence or 0.5)
            # Bonus for shots with dialogue
            has_dialog = any(
                ts.start_time >= shot.start_time and ts.end_time <= shot.end_time
                for ts in transcripts
            )
            if has_dialog:
                score *= 1.5
            scored.append((shot, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Take top shots
        top_shots = [s for s, _ in scored[:max(3, len(shots) // 2)]]
        
        # Sort selected shots by original time order
        top_shots.sort(key=lambda s: s.start_time)
        
        story_shots = []
        total_duration = 0.0
        
        for i, shot in enumerate(top_shots):
            if i == 0:
                role = StoryShotRole.HOOK
            elif i == len(top_shots) - 1:
                role = StoryShotRole.RESOLUTION
            else:
                role = StoryShotRole.CLIMAX if i < len(top_shots) * 0.5 else StoryShotRole.DEVELOPMENT
            
            story_shots.append({
                "video_shot_id": shot.id,
                "start_time": shot.start_time,
                "end_time": shot.end_time,
                "role": role.value,
                "reasoning": f"Highlight selection rank {i+1} (quality score: {scored[i][1]:.2f})",
                "confidence": 0.85,
            })
            
            total_duration += shot.duration or 0
        
        return {"story_shots": story_shots, "total_duration": total_duration}
    
    def _plan_emotional_narrative(
        self,
        story: StoryCandidate,
        shots: List[VideoShot],
        transcripts: List[TranscriptSegment],
    ) -> Dict[str, Any]:
        """Plan emotional three-act structure."""
        
        # Find shots with strong transcript content
        emotional_shots = []
        for shot in shots:
            shot_transcripts = [
                ts for ts in transcripts
                if ts.start_time >= shot.start_time and ts.end_time <= shot.end_time
            ]
            if shot_transcripts:
                # Score by transcript confidence and length
                text_length = sum(len(ts.text) for ts in shot_transcripts)
                avg_conf = sum(ts.confidence or 0 for ts in shot_transcripts) / len(shot_transcripts)
                score = text_length * avg_conf
                emotional_shots.append((shot, score, shot_transcripts))
        
        emotional_shots.sort(key=lambda x: x[1], reverse=True)
        
        # If not enough emotional shots, supplement with regular shots
        if len(emotional_shots) < 3:
            other_shots = [s for s in shots if s not in [e[0] for e in emotional_shots]]
            emotional_shots.extend([(s, 0, []) for s in other_shots])
        
        story_shots = []
        total_duration = 0.0
        
        # Three-act structure
        acts = [
            ("opening", StoryShotRole.HOOK, 0.3),
            ("development", StoryShotRole.DEVELOPMENT, 0.4),
            ("climax", StoryShotRole.CLIMAX, 0.2),
            ("resolution", StoryShotRole.RESOLUTION, 0.1),
        ]
        
        act_idx = 0
        shots_per_act = max(1, len(emotional_shots) // len(acts))
        
        for i, (shot, score, ts_list) in enumerate(emotional_shots):
            # Move to next act when we've allocated enough shots
            if i >= (act_idx + 1) * shots_per_act and act_idx < len(acts) - 1:
                act_idx += 1
            
            role = acts[act_idx][1]
            
            has_dialog = len(ts_list) > 0
            
            story_shots.append({
                "video_shot_id": shot.id,
                "start_time": shot.start_time,
                "end_time": shot.end_time,
                "role": role.value,
                "reasoning": f"Emotional {acts[act_idx][0]}: {'with dialogue' if has_dialog else 'visual'}"
                           f" (act {act_idx+1}/{len(acts)})",
                "confidence": 0.75 if has_dialog else 0.6,
            })
            
            total_duration += shot.duration or 0
        
        return {"story_shots": story_shots, "total_duration": total_duration}
    
    async def _plan_documentary(
        self,
        story: StoryCandidate,
        shots: List[VideoShot],
        transcripts: List[TranscriptSegment],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Plan documentary - structured by scenes."""
        
        # Get scenes for this project
        from app.models import VideoScene
        scenes_result = await db.execute(
            select(VideoScene)
            .join(VideoScene.media_asset)
            .where(VideoScene.media_asset.has(project_id=story.project_id))
            .order_by(VideoScene.scene_index)
        )
        scenes = scenes_result.scalars().all()
        
        story_shots = []
        total_duration = 0.0
        
        for scene_idx, scene in enumerate(scenes):
            scene_shots = [
                s for s in shots
                if s.start_time >= scene.start_time and s.end_time <= scene.end_time
            ]
            
            if not scene_shots:
                continue
            
            for shot_idx, shot in enumerate(scene_shots):
                if scene_idx == 0 and shot_idx == 0:
                    role = StoryShotRole.HOOK
                elif scene_idx == len(scenes) - 1 and shot_idx == len(scene_shots) - 1:
                    role = StoryShotRole.RESOLUTION
                else:
                    role = StoryShotRole.DEVELOPMENT
                
                story_shots.append({
                    "video_shot_id": shot.id,
                    "start_time": shot.start_time,
                    "end_time": shot.end_time,
                    "role": role.value,
                    "reasoning": f"Documentary scene {scene_idx+1}: {scene.label or f'Scene {scene.scene_index}'}",
                    "confidence": 0.75,
                })
                
                total_duration += shot.duration or 0
        
        return {"story_shots": story_shots, "total_duration": total_duration}
    
    def _plan_educational(
        self,
        story: StoryCandidate,
        shots: List[VideoShot],
        transcripts: List[TranscriptSegment],
    ) -> Dict[str, Any]:
        """Plan educational - structured by topics."""
        
        # Extract topics from narrative arc
        topics = story.narrative_arc.get("themes", []) if story.narrative_arc else []
        if not topics:
            topics = ["overview", "details", "summary"]
        
        # Distribute shots across topics
        shots_per_topic = max(1, len(shots) // len(topics))
        
        story_shots = []
        total_duration = 0.0
        
        for topic_idx, topic in enumerate(topics):
            start = topic_idx * shots_per_topic
            end = min((topic_idx + 1) * shots_per_topic, len(shots))
            topic_shots = shots[start:end]
            
            for i, shot in enumerate(topic_shots):
                if topic_idx == 0 and i == 0:
                    role = StoryShotRole.HOOK
                elif topic_idx == len(topics) - 1 and i == len(topic_shots) - 1:
                    role = StoryShotRole.RESOLUTION
                else:
                    role = StoryShotRole.DEVELOPMENT
                
                story_shots.append({
                    "video_shot_id": shot.id,
                    "start_time": shot.start_time,
                    "end_time": shot.end_time,
                    "role": role.value,
                    "reasoning": f"Educational topic {topic_idx+1}: {topic} (shot {i+1}/{len(topic_shots)})",
                    "confidence": 0.7,
                })
                
                total_duration += shot.duration or 0
        
        return {"story_shots": story_shots, "total_duration": total_duration}


# Import defaultdict
from collections import defaultdict


# Singleton
_sequence_planner_service: Optional["SequencePlannerService"] = None


def get_sequence_planner_service(): return SequencePlannerService()

