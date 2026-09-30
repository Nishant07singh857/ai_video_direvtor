import uuid
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum as PyEnum

from sqlalchemy import select

from app.core import database
from app.models import MediaAsset, Project, StoryCandidate, Timeline, VideoShot
from app.core.timeline import normalize_timeline
from app.services.knowledge_graph import get_knowledge_graph_service
from app.services.shot_ranker import get_shot_ranker_service
from app.services.story_generator import get_story_generator_service
from app.services.story_ranker import get_story_ranker_service
from app.services.sequence_planner import get_sequence_planner_service
from app.services.timeline_generator import get_timeline_generator_service
from app.services.analysis_job import get_analysis_job_service


class AIDirectorStage(str, PyEnum):
    """Stages of the AI Director pipeline."""
    VALIDATION = "validation"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    SHOT_RANKING = "shot_ranking"
    STORY_GENERATION = "story_generation"
    STORY_RANKING = "story_ranking"
    SEQUENCE_PLANNING = "sequence_planning"
    TIMELINE_GENERATION = "timeline_generation"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StageResult:
    """Result of a pipeline stage."""
    stage: AIDirectorStage
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class AIDirectorResult:
    """Complete result of the AI Director pipeline."""
    project_id: uuid.UUID
    success: bool
    stages: List[StageResult]
    story_candidates: Optional[List[Dict[str, Any]]] = None
    selected_story: Optional[Dict[str, Any]] = None
    timeline: Optional[Dict[str, Any]] = None
    knowledge_graph_stats: Optional[Dict[str, Any]] = None
    shot_rankings: Optional[List[Dict[str, Any]]] = None
    total_duration: float = 0.0
    error: Optional[str] = None


class AIDirectorService:
    """Orchestrates the complete AI Director pipeline.
    
    Stages:
    1. Validation - Check project has usable analyzed media
    2. Knowledge Graph - Build project knowledge graph from Phase 3 analysis
    3. Shot Ranking - Rank shots by quality/relevance
    4. Story Generation - Generate multiple story candidates
    5. Story Ranking - Rank story candidates
    6. Sequence Planning - Plan shot sequences for selected story
    7. Timeline Generation - Generate renderer-ready timeline
    """
    
    def __init__(self):
        self._knowledge_graph = get_knowledge_graph_service()
        self._shot_ranker = get_shot_ranker_service()
        self._story_generator = get_story_generator_service()
        self._story_ranker = get_story_ranker_service()
        self._sequence_planner = get_sequence_planner_service()
        self._timeline_generator = get_timeline_generator_service()
        self._job_service = get_analysis_job_service()
    
    async def run_full_pipeline(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        max_story_candidates: int = 5,
    ) -> AIDirectorResult:
        stages: list[StageResult] = []

        async def run_stage(stage_result: StageResult) -> StageResult:
            stages.append(stage_result)
            return stage_result

        validation = await run_stage(await self._stage_validation(project_id, user_id))
        if not validation.success:
            return AIDirectorResult(project_id, False, stages, error=validation.error)

        graph_stage = await run_stage(await self._stage_knowledge_graph(project_id))
        if not graph_stage.success:
            return AIDirectorResult(project_id, False, stages, error=graph_stage.error)

        shots_stage = await run_stage(await self._stage_shot_ranking(project_id))
        if not shots_stage.success:
            return AIDirectorResult(project_id, False, stages, error=shots_stage.error)

        stories_stage = await run_stage(
            await self._stage_story_generation(project_id, max_story_candidates)
        )
        if not stories_stage.success or not stories_stage.data:
            return AIDirectorResult(project_id, False, stages, error=stories_stage.error or "No stories generated")

        ranking_stage = await run_stage(await self._stage_story_ranking(project_id))
        if not ranking_stage.success:
            return AIDirectorResult(project_id, False, stages, error=ranking_stage.error)
        selected_id = (ranking_stage.data or {}).get("selected_story_id")
        if not selected_id:
            return AIDirectorResult(project_id, False, stages, error="No story candidate could be selected")

        try:
            story_id = uuid.UUID(str(selected_id))
        except ValueError:
            return AIDirectorResult(project_id, False, stages, error="Story ranking returned an invalid id")

        sequence_stage = await run_stage(await self._stage_sequence_planning(project_id, story_id))
        if not sequence_stage.success:
            return AIDirectorResult(project_id, False, stages, error=sequence_stage.error)
        timeline_stage = await run_stage(await self._stage_timeline_generation(project_id, story_id))
        if not timeline_stage.success:
            return AIDirectorResult(project_id, False, stages, error=timeline_stage.error)

        # Persist an explainable decision trace alongside the canonical EDL so
        # the dashboard can show why each cut exists instead of presenting a
        # black-box "AI complete" badge.
        timeline_id = (timeline_stage.data or {}).get("id")
        if timeline_id:
            async with database.async_session_maker() as db:
                timeline_row = await db.get(Timeline, uuid.UUID(str(timeline_id)))
                if timeline_row is not None:
                    canonical = normalize_timeline(timeline_row.timeline_json)
                    decisions = []
                    for track in canonical.get("tracks", []):
                        for clip in track.get("clips", []):
                            source = clip.get("source", {})
                            decisions.append(
                                {
                                    "clip_id": str(clip.get("id")),
                                    "media_asset_id": str(source.get("media_asset_id")) if source.get("media_asset_id") else "",
                                    "start": clip.get("timeline_start", 0.0),
                                    "end": clip.get("timeline_end", 0.0),
                                    "reason": clip.get("narrative_role") or "Selected from analyzed source footage",
                                }
                            )
                    metadata = dict(canonical.get("metadata") or {})
                    metadata["director"] = {
                        "mode": "deterministic_source_grounded",
                        "stages": [
                            {"stage": stage.stage.value, "status": "completed" if stage.success else "failed", "message": stage.message}
                            for stage in stages
                        ],
                        "decisions": decisions,
                    }
                    canonical["metadata"] = metadata
                    timeline_row.timeline_json = canonical
                    await db.commit()
                    timeline_stage.data["timeline_json"] = canonical

        completed = StageResult(
            stage=AIDirectorStage.COMPLETED,
            success=True,
            message="AI Director completed source-grounded timeline generation",
            data={"timeline_id": (timeline_stage.data or {}).get("id")},
        )
        stages.append(completed)
        story_candidates = stories_stage.data if isinstance(stories_stage.data, list) else []
        selected_story = next((s for s in story_candidates if s.get("id") == selected_id), None)
        return AIDirectorResult(
            project_id=project_id,
            success=True,
            stages=stages,
            story_candidates=story_candidates,
            selected_story=selected_story,
            timeline=(timeline_stage.data or {}).get("timeline_json"),
            knowledge_graph_stats=graph_stage.data,
            shot_rankings=shots_stage.data if isinstance(shots_stage.data, list) else [],
            total_duration=float((timeline_stage.data or {}).get("total_duration", 0.0) or 0.0),
        )

    async def _stage_validation(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> StageResult:
        """Stage 1: Validate project ownership and media readiness."""
        try:
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
                    return StageResult(
                        stage=AIDirectorStage.VALIDATION,
                        success=False,
                        message="Project not found or access denied",
                        error="Project not found or access denied",
                    )
                
                # Check for media assets with analysis
                media_result = await db.execute(
                    select(MediaAsset).where(MediaAsset.project_id == project_id)
                )
                media_assets = media_result.scalars().all()
                
                if not media_assets:
                    return StageResult(
                        stage=AIDirectorStage.VALIDATION,
                        success=False,
                        message="No media assets in project",
                        error="No media assets in project",
                    )
                
                # Check for at least some analyzed shots
                media_ids = [m.id for m in media_assets]
                if media_ids:
                    from sqlalchemy import func
                    total_shots_result = await db.execute(
                        select(func.count(VideoShot.id)).where(VideoShot.media_asset_id.in_(media_ids))
                    )
                    total_shots = total_shots_result.scalar() or 0
                else:
                    total_shots = 0
                
                if total_shots == 0:
                    return StageResult(
                        stage=AIDirectorStage.VALIDATION,
                        success=False,
                        message="No analyzed shots available. Run Phase 3 analysis first.",
                        error="No analyzed shots available. Run Phase 3 analysis first.",
                    )
                
                return StageResult(
                    stage=AIDirectorStage.VALIDATION,
                    success=True,
                    message=f"Project validated: {len(media_assets)} media assets, {total_shots} shots",
                    data={"media_count": len(media_assets), "shot_count": total_shots},
                )
        except Exception as e:
            return StageResult(
                stage=AIDirectorStage.VALIDATION,
                success=False,
                message=f"Validation failed: {str(e)}",
                error=str(e),
            )
    
    async def _stage_knowledge_graph(self, project_id: uuid.UUID) -> StageResult:
        """Stage 2: Build knowledge graph from Phase 3 analysis."""
        try:
            result = await self._knowledge_graph.build_graph(project_id)
            return StageResult(
                stage=AIDirectorStage.KNOWLEDGE_GRAPH,
                success=True,
                message=f"Knowledge graph built: {result.get('nodes', 0)} nodes, {result.get('edges', 0)} edges",
                data=result,
            )
        except Exception as e:
            return StageResult(
                stage=AIDirectorStage.KNOWLEDGE_GRAPH,
                success=False,
                message=f"Knowledge graph build failed: {str(e)}",
                error=str(e),
            )
    
    async def _stage_shot_ranking(self, project_id: uuid.UUID) -> StageResult:
        """Stage 3: Rank shots by quality and relevance."""
        try:
            rankings = await self._shot_ranker.rank_shots(project_id)
            return StageResult(
                stage=AIDirectorStage.SHOT_RANKING,
                success=True,
                message=f"Ranked {len(rankings)} shots",
                data=[{
                    "video_shot_id": str(r.video_shot_id),
                    "composite_score": r.composite_score,
                    "rank": r.rank,
                } for r in rankings],
            )
        except Exception as e:
            return StageResult(
                stage=AIDirectorStage.SHOT_RANKING,
                success=False,
                message=f"Shot ranking failed: {str(e)}",
                error=str(e),
            )
    
    async def _stage_story_generation(
        self, project_id: uuid.UUID, max_candidates: int
    ) -> StageResult:
        """Stage 4: Generate story candidates."""
        try:
            stories = await self._story_generator.generate_stories(project_id, max_candidates)
            return StageResult(
                stage=AIDirectorStage.STORY_GENERATION,
                success=True,
                message=f"Generated {len(stories)} story candidates",
                data=[{
                    "id": str(s.id),
                    "title": s.title,
                    "description": s.description,
                    "estimated_duration": s.estimated_duration,
                    "confidence": s.confidence,
                    "status": s.status.value,
                    "themes": s.narrative_arc.get("themes", []) if s.narrative_arc else [],
                } for s in stories],
            )
        except Exception as e:
            return StageResult(
                stage=AIDirectorStage.STORY_GENERATION,
                success=False,
                message=f"Story generation failed: {str(e)}",
                error=str(e),
            )
    
    async def _stage_story_ranking(self, project_id: uuid.UUID) -> StageResult:
        """Stage 5: Rank story candidates."""
        try:
            rankings = await self._story_ranker.rank_stories(project_id)
            best_story = await self._story_ranker.select_best_story(project_id)
            return StageResult(
                stage=AIDirectorStage.STORY_RANKING,
                success=True,
                message=f"Ranked {len(rankings)} stories, best: {best_story.title if best_story else 'none'}",
                data={
                    "rankings": [{
                        "story_candidate_id": str(r.story_candidate_id),
                        "composite_score": r.composite_score,
                        "rank": r.rank,
                    } for r in rankings],
                    "selected_story_id": str(best_story.id) if best_story else None,
                },
            )
        except Exception as e:
            return StageResult(
                stage=AIDirectorStage.STORY_RANKING,
                success=False,
                message=f"Story ranking failed: {str(e)}",
                error=str(e),
            )
    
    async def _stage_sequence_planning(
        self, project_id: uuid.UUID, story_id: uuid.UUID
    ) -> StageResult:
        """Stage 6: Plan shot sequence for selected story."""
        try:
            sequence = await self._sequence_planner.plan_sequence(project_id, story_id)
            return StageResult(
                stage=AIDirectorStage.SEQUENCE_PLANNING,
                success=True,
                message=f"Planned sequence: {sequence.shot_count} shots, {sequence.total_duration:.1f}s",
                data={
                    "story_candidate_id": str(sequence.story_candidate_id),
                    "shot_count": sequence.shot_count,
                    "total_duration": sequence.total_duration,
                },
            )
        except Exception as e:
            return StageResult(
                stage=AIDirectorStage.SEQUENCE_PLANNING,
                success=False,
                message=f"Sequence planning failed: {str(e)}",
                error=str(e),
            )
    
    async def _stage_timeline_generation(
        self, project_id: uuid.UUID, story_id: uuid.UUID
    ) -> StageResult:
        """Stage 7: Generate renderer-ready timeline."""
        try:
            timeline = await self._timeline_generator.generate_timeline(project_id, story_id)
            return StageResult(
                stage=AIDirectorStage.TIMELINE_GENERATION,
                success=True,
                message=f"Timeline generated: v{timeline.version_number}, {timeline.total_duration:.1f}s",
                data={
                    "id": str(timeline.id),
                    "version_number": timeline.version_number,
                    "total_duration": timeline.total_duration,
                    "status": timeline.status.value,
                    "timeline_json": timeline.timeline_json,
                },
            )
        except Exception as e:
            return StageResult(
                stage=AIDirectorStage.TIMELINE_GENERATION,
                success=False,
                message=f"Timeline generation failed: {str(e)}",
                error=str(e),
            )
    
    async def get_pipeline_status(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Get the current status of AI Director analysis for a project."""
        async with database.async_session_maker() as db:
            # Check each stage
            status = {
                "project_id": str(project_id),
                "stages": {},
            }
            
            # Knowledge graph
            kg = await self._knowledge_graph.get_graph(project_id)
            status["stages"]["knowledge_graph"] = {
                "completed": len(kg.get("nodes", [])) > 0,
                "nodes": len(kg.get("nodes", [])),
                "edges": len(kg.get("edges", [])),
            }
            
            # Shot rankings
            shot_rankings = await self._shot_ranker.get_rankings(project_id)
            status["stages"]["shot_ranking"] = {
                "completed": len(shot_rankings) > 0,
                "ranked_shots": len(shot_rankings),
            }
            
            # Stories
            stories_result = await db.execute(
                select(StoryCandidate).where(StoryCandidate.project_id == project_id)
            )
            stories = stories_result.scalars().all()
            status["stages"]["story_generation"] = {
                "completed": len(stories) > 0,
                "candidates": len(stories),
            }
            
            # Story rankings
            story_rankings = await self._story_ranker.get_rankings(project_id)
            status["stages"]["story_ranking"] = {
                "completed": len(story_rankings) > 0,
                "ranked": len(story_rankings),
            }
            
            # Timelines
            timelines = await self._timeline_generator.list_timelines(project_id)
            status["stages"]["timeline_generation"] = {
                "completed": len(timelines) > 0,
                "versions": len(timelines),
            }
            
            return status


# Singleton
_ai_director_service: Optional["AIDirectorService"] = None



def get_ai_director_service() -> AIDirectorService:
    global _ai_director_service
    if _ai_director_service is None:
        _ai_director_service = AIDirectorService()
    return _ai_director_service


