import uuid
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum as PyEnum

from sqlalchemy import select
from app.models import (
    AnalysisJob,
    AudioAnalysis,
    MediaAsset,
    Project,
    StoryCandidate,
    StoryStatus,
    Timeline,
    TranscriptSegment,
    VideoScene,
    VideoShot,
)

from app.core import database
from app.services.knowledge_graph import get_knowledge_graph_service


class StoryStructureType(str, PyEnum):
    CHRONOLOGICAL = "chronological"
    HIGHLIGHT_REEL = "highlight_reel"
    EMOTIONAL_NARRATIVE = "emotional_narrative"
    DOCUMENTARY = "documentary"
    EDUCATIONAL = "educational"


@dataclass
class StoryCandidateDraft:
    """Draft story candidate before persistence."""
    title: str
    description: str
    narrative_arc: Dict[str, Any]
    structure_type: StoryStructureType
    themes: List[str]
    tone: str
    estimated_duration: float
    confidence: float
    source_media_asset_ids: List[uuid.UUID]
    source_shot_ids: List[uuid.UUID]
    source_analysis_job_ids: List[uuid.UUID]


class StoryGeneratorService:
    """Generates multiple story candidates from analyzed media assets.
    
    Creates diverse story approaches based on available footage and analysis.
    Does not invent semantic content not present in Phase 3 analysis.
    """
    
    def __init__(self):
        self._knowledge_graph = get_knowledge_graph_service()
    
    async def generate_stories(
        self,
        project_id: uuid.UUID,
        max_candidates: int = 5,
    ) -> List[StoryCandidate]:
        """Generate multiple story candidates for a project."""
        async with database.async_session_maker() as db:
            # Verify project and get media with analysis
            project_result = await db.execute(select(Project).where(Project.id == project_id))
            project = project_result.scalar_one_or_none()
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Get media assets with complete analysis
            media_result = await db.execute(
                select(MediaAsset).where(MediaAsset.project_id == project_id)
            )
            media_assets = media_result.scalars().all()
            
            if not media_assets:
                raise ValueError("No media assets found for project")
            
            # Collect all analysis data
            all_shots = []
            all_scenes = []
            all_transcripts = []
            all_audio = []
            analysis_job_ids = []
            total_duration = 0.0
            
            for media in media_assets:
                # Shots
                shots_result = await db.execute(
                    select(VideoShot).where(VideoShot.media_asset_id == media.id).order_by(VideoShot.shot_index)
                )
                shots = shots_result.scalars().all()
                all_shots.extend(shots)
                
                # Scenes
                scenes_result = await db.execute(
                    select(VideoScene).where(VideoScene.media_asset_id == media.id).order_by(VideoScene.scene_index)
                )
                scenes = scenes_result.scalars().all()
                all_scenes.extend(scenes)
                
                # Transcripts
                transcript_result = await db.execute(
                    select(TranscriptSegment).where(TranscriptSegment.media_asset_id == media.id).order_by(TranscriptSegment.start_time)
                )
                transcripts = transcript_result.scalars().all()
                all_transcripts.extend(transcripts)
                
                # Audio
                audio_result = await db.execute(
                    select(AudioAnalysis).where(AudioAnalysis.media_asset_id == media.id)
                )
                audio = audio_result.scalar_one_or_none()
                if audio:
                    all_audio.append(audio)
                
                # Analysis jobs
                jobs_result = await db.execute(
                    select(AnalysisJob).where(AnalysisJob.media_asset_id == media.id)
                )
                jobs = jobs_result.scalars().all()
                analysis_job_ids.extend([str(j.id) for j in jobs])  # Convert UUIDs to strings for JSON
                
                if media.duration:
                    total_duration += media.duration
            
            if not all_shots:
                raise ValueError("No analyzed shots available for story generation")
            
            # Build knowledge graph if not exists
            await self._knowledge_graph.build_graph(project_id)
            
            # Generate candidates using different structural approaches
            candidates = []
            
            # 1. Chronological story (follows temporal order)
            if max_candidates >= 1:
                candidates.append(self._generate_chronological(
                    project_id, all_shots, all_scenes, all_transcripts, 
                    total_duration, analysis_job_ids
                ))
            
            # 2. Highlight reel (best shots only)
            if max_candidates >= 2:
                candidates.append(self._generate_highlight_reel(
                    project_id, all_shots, total_duration, analysis_job_ids
                ))
            
            # 3. Emotional narrative (build from transcript themes)
            if max_candidates >= 3 and all_transcripts:
                candidates.append(self._generate_emotional_narrative(
                    project_id, all_shots, all_transcripts, total_duration, analysis_job_ids
                ))
            
            # 4. Documentary style (scene-based structure)
            if max_candidates >= 4 and all_scenes:
                candidates.append(self._generate_documentary(
                    project_id, all_shots, all_scenes, total_duration, analysis_job_ids
                ))
            
            # 5. Educational (structured by topics/themes from transcripts)
            if max_candidates >= 5 and all_transcripts:
                candidates.append(self._generate_educational(
                    project_id, all_shots, all_transcripts, total_duration, analysis_job_ids
                ))
            
            # Persist all candidates
            persisted = []
            for i, draft in enumerate(candidates[:max_candidates]):
                candidate = StoryCandidate(
                    project_id=project_id,
                    title=draft.title,
                    description=draft.description,
                    narrative_arc=draft.narrative_arc,
                    estimated_duration=draft.estimated_duration,
                    confidence=draft.confidence,
                    status=StoryStatus.GENERATED,
                    source_analysis_job_ids=draft.source_analysis_job_ids,
                )
                db.add(candidate)
                await db.flush()
                persisted.append(candidate)
            
            await db.commit()
            return persisted
    
    def _generate_chronological(
        self,
        project_id: uuid.UUID,
        shots: List[VideoShot],
        scenes: List[VideoScene],
        transcripts: List[TranscriptSegment],
        total_duration: float,
        analysis_job_ids: List[uuid.UUID],
    ) -> StoryCandidateDraft:
        """Generate a chronological story following the natural time order."""
        
        # Group shots by scenes for structure
        acts = []
        if scenes:
            for i, scene in enumerate(scenes):
                scene_shots = [s for s in shots if s.start_time >= scene.start_time and s.end_time <= scene.end_time]
                acts.append({
                    "act_number": i + 1,
                    "title": scene.label or f"Scene {scene.scene_index + 1}",
                    "duration": scene.end_time - scene.start_time,
                    "shot_count": len(scene_shots),
                    "description": scene.description,
                })
        else:
            # Single act for all shots
            acts.append({
                "act_number": 1,
                "title": "Full Sequence",
                "duration": total_duration,
                "shot_count": len(shots),
            })
        
        narrative_arc = {
            "structure": StoryStructureType.CHRONOLOGICAL.value,
            "acts": acts,
            "themes": ["chronology", "natural flow"],
            "tone": "natural",
            "total_shots": len(shots),
        }
        
        return StoryCandidateDraft(
            title="Chronological Story",
            description="A natural chronological narrative following the original footage sequence.",
            narrative_arc=narrative_arc,
            structure_type=StoryStructureType.CHRONOLOGICAL,
            themes=["chronology", "natural flow"],
            tone="natural",
            estimated_duration=total_duration,
            confidence=0.8,
            source_media_asset_ids=list(set(s.media_asset_id for s in shots)),
            source_shot_ids=[s.id for s in shots],
            source_analysis_job_ids=analysis_job_ids,
        )
    
    def _generate_highlight_reel(
        self,
        project_id: uuid.UUID,
        shots: List[VideoShot],
        total_duration: float,
        analysis_job_ids: List[uuid.UUID],
    ) -> StoryCandidateDraft:
        """Generate a highlight reel from the best shots."""
        
        # Sort shots by duration and confidence (proxy for quality)
        scored_shots = []
        for s in shots:
            score = (s.duration if s.duration else 0) * (s.confidence or 0.5)
            scored_shots.append((s, score))
        
        scored_shots.sort(key=lambda x: x[1], reverse=True)
        
        # Take top 50% or at most 10 shots
        top_shots = [s for s, _ in scored_shots[:max(3, len(shots) // 2)]]
        highlight_duration = sum(s.duration or 0 for s in top_shots)
        
        narrative_arc = {
            "structure": StoryStructureType.HIGHLIGHT_REEL.value,
            "acts": [{
                "act_number": 1,
                "title": "Highlights",
                "duration": highlight_duration,
                "shot_count": len(top_shots),
                "description": "Best moments from the footage",
            }],
            "themes": ["highlights", "best moments", "energy"],
            "tone": "energetic",
            "total_shots": len(top_shots),
        }
        
        return StoryCandidateDraft(
            title="Highlight Reel",
            description="An energetic compilation of the most engaging moments.",
            narrative_arc=narrative_arc,
            structure_type=StoryStructureType.HIGHLIGHT_REEL,
            themes=["highlights", "energy", "impact"],
            tone="energetic",
            estimated_duration=highlight_duration,
            confidence=0.7,
            source_media_asset_ids=list(set(s.media_asset_id for s in top_shots)),
            source_shot_ids=[s.id for s in top_shots],
            source_analysis_job_ids=analysis_job_ids,
        )
    
    def _generate_emotional_narrative(
        self,
        project_id: uuid.UUID,
        shots: List[VideoShot],
        transcripts: List[TranscriptSegment],
        total_duration: float,
        analysis_job_ids: List[uuid.UUID],
    ) -> StoryCandidateDraft:
        """Generate an emotional narrative based on speech content."""
        
        # Extract themes from transcript text
        themes = self._extract_themes_from_transcripts(transcripts)
        
        # Group shots near transcript segments
        narrated_shots = []
        for shot in shots:
            for ts in transcripts:
                if ts.start_time >= shot.start_time and ts.end_time <= shot.end_time:
                    narrated_shots.append(shot)
                    break
        
        if not narrated_shots:
            narrated_shots = shots[:len(shots) // 2]
        
        narrated_duration = sum(s.duration or 0 for s in narrated_shots)
        
        acts = [{
            "act_number": 1,
            "title": "Opening",
            "duration": narrated_duration * 0.3,
            "shot_count": max(1, len(narrated_shots) // 3),
        }, {
            "act_number": 2,
            "title": "Development",
            "duration": narrated_duration * 0.4,
            "shot_count": max(1, len(narrated_shots) // 3),
        }, {
            "act_number": 3,
            "title": "Resolution",
            "duration": narrated_duration * 0.3,
            "shot_count": max(1, len(narrated_shots) // 3),
        }]
        
        narrative_arc = {
            "structure": StoryStructureType.EMOTIONAL_NARRATIVE.value,
            "acts": acts,
            "themes": themes,
            "tone": "emotional",
            "total_shots": len(narrated_shots),
        }
        
        return StoryCandidateDraft(
            title="Emotional Narrative",
            description="A character-driven story built around spoken content and emotional beats.",
            narrative_arc=narrative_arc,
            structure_type=StoryStructureType.EMOTIONAL_NARRATIVE,
            themes=themes,
            tone="emotional",
            estimated_duration=narrated_duration,
            confidence=0.6,
            source_media_asset_ids=list(set(s.media_asset_id for s in narrated_shots)),
            source_shot_ids=[s.id for s in narrated_shots],
            source_analysis_job_ids=analysis_job_ids,
        )
    
    def _generate_documentary(
        self,
        project_id: uuid.UUID,
        shots: List[VideoShot],
        scenes: List[VideoScene],
        total_duration: float,
        analysis_job_ids: List[uuid.UUID],
    ) -> StoryCandidateDraft:
        """Generate a documentary-style story with scene-based structure."""
        
        acts = []
        for i, scene in enumerate(scenes):
            scene_shots = [s for s in shots if s.start_time >= scene.start_time and s.end_time <= scene.end_time]
            acts.append({
                "act_number": i + 1,
                "title": f"Chapter {i + 1}: {scene.label or f'Scene {scene.scene_index}'}",
                "duration": scene.end_time - scene.start_time,
                "shot_count": len(scene_shots),
                "description": scene.description,
            })
        
        narrative_arc = {
            "structure": StoryStructureType.DOCUMENTARY.value,
            "acts": acts,
            "themes": ["documentary", "structured", "informative"],
            "tone": "informative",
            "total_shots": len(shots),
        }
        
        return StoryCandidateDraft(
            title="Documentary Structure",
            description="An organized documentary-style narrative with clear chapter breaks.",
            narrative_arc=narrative_arc,
            structure_type=StoryStructureType.DOCUMENTARY,
            themes=["documentary", "structure", "information"],
            tone="informative",
            estimated_duration=total_duration,
            confidence=0.75,
            source_media_asset_ids=list(set(s.media_asset_id for s in shots)),
            source_shot_ids=[s.id for s in shots],
            source_analysis_job_ids=analysis_job_ids,
        )
    
    def _generate_educational(
        self,
        project_id: uuid.UUID,
        shots: List[VideoShot],
        transcripts: List[TranscriptSegment],
        total_duration: float,
        analysis_job_ids: List[uuid.UUID],
    ) -> StoryCandidateDraft:
        """Generate an educational/explainer style story."""
        
        # Extract key topics from transcripts
        topics = self._extract_topics_from_transcripts(transcripts)
        
        # Distribute shots across topics
        acts = []
        shots_per_topic = max(1, len(shots) // max(1, len(topics)))
        
        for i, topic in enumerate(topics):
            start_idx = i * shots_per_topic
            end_idx = min((i + 1) * shots_per_topic, len(shots))
            topic_shots = shots[start_idx:end_idx]
            topic_duration = sum(s.duration or 0 for s in topic_shots)
            
            acts.append({
                "act_number": i + 1,
                "title": f"Topic: {topic}",
                "duration": topic_duration,
                "shot_count": len(topic_shots),
                "description": f"Coverage of {topic}",
            })
        
        narrative_arc = {
            "structure": StoryStructureType.EDUCATIONAL.value,
            "acts": acts,
            "themes": topics,
            "tone": "educational",
            "total_shots": len(shots),
        }
        
        return StoryCandidateDraft(
            title="Educational Explainer",
            description="A structured educational narrative organized by key topics.",
            narrative_arc=narrative_arc,
            structure_type=StoryStructureType.EDUCATIONAL,
            themes=topics,
            tone="educational",
            estimated_duration=total_duration,
            confidence=0.65,
            source_media_asset_ids=list(set(s.media_asset_id for s in shots)),
            source_shot_ids=[s.id for s in shots],
            source_analysis_job_ids=analysis_job_ids,
        )
    
    def _extract_themes_from_transcripts(self, transcripts: List[TranscriptSegment]) -> List[str]:
        """Extract thematic keywords from transcript text."""
        # Simple keyword extraction - in production could use NLP
        text = " ".join(t.text.lower() for t in transcripts)
        themes = []
        
        # Common thematic keywords
        keyword_map = {
            "journey": ["journey", "travel", "adventure", "trip", "path"],
            "growth": ["grow", "learn", "develop", "improve", "change", "become"],
            "challenge": ["hard", "difficult", "challenge", "struggle", "overcome", "fight"],
            "success": ["win", "success", "achieve", "accomplish", "victory", "triumph"],
            "connection": ["together", "team", "friend", "family", "love", "community"],
            "discovery": ["discover", "find", "explore", "reveal", "uncover", "new"],
        }
        
        for theme, keywords in keyword_map.items():
            if any(kw in text for kw in keywords):
                themes.append(theme)
        
        return themes if themes else ["story", "narrative"]
    
    def _extract_topics_from_transcripts(self, transcripts: List[TranscriptSegment]) -> List[str]:
        """Extract educational topics from transcript text."""
        # Simple noun phrase extraction placeholder
        text = " ".join(t.text.lower() for t in transcripts)
        topics = []
        
        # Domain-specific topic keywords
        topic_keywords = {
            "technology": ["tech", "software", "code", "program", "computer", "ai", "digital"],
            "science": ["science", "research", "experiment", "data", "study", "analysis"],
            "business": ["business", "market", "customer", "product", "strategy", "revenue"],
            "design": ["design", "create", "build", "make", "prototype", "interface"],
            "education": ["teach", "learn", "student", "course", "lesson", "training"],
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                topics.append(topic)
        
        return topics if topics else ["general", "overview"]


# Singleton
_story_generator_service: Optional["StoryGeneratorService"] = None

def get_story_generator_service(): return StoryGeneratorService()

