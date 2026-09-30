import uuid
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import database
from app.models import Project, StoryCandidate, StoryStatus, VideoShot


@dataclass
class StoryRankingResult:
    """Ranking result for a story candidate."""
    story_candidate_id: uuid.UUID
    coherence_score: float
    engagement_score: float
    completeness_score: float
    footage_coverage_score: float
    confidence_score: float
    composite_score: float
    rank: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class StoryRankerService:
    """Ranks story candidates based on objective criteria.
    
    Ranking is deterministic and based only on available analysis data.
    """
    
    def __init__(self):
        self.weights = {
            "coherence": 0.25,
            "engagement": 0.20,
            "completeness": 0.25,
            "footage_coverage": 0.15,
            "confidence": 0.15,
        }
    
    async def rank_stories(
        self,
        project_id: uuid.UUID,
    ) -> List[StoryRankingResult]:
        """Rank all story candidates for a project."""
        async with database.async_session_maker() as db:
            # Verify project
            project_result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = project_result.scalar_one_or_none()
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Get all story candidates
            stories_result = await db.execute(
                select(StoryCandidate).where(
                    StoryCandidate.project_id == project_id,
                    StoryCandidate.status.in_([StoryStatus.GENERATED, StoryStatus.RANKED])
                )
            )
            stories = stories_result.scalars().all()
            
            if not stories:
                return []
            
            # Score each story
            rankings = []
            for story in stories:
                ranking = await self._score_story(db, story)
                rankings.append(ranking)
            
            # Sort by composite score
            rankings.sort(key=lambda r: r.composite_score, reverse=True)
            
            # Assign ranks and update status
            for i, ranking in enumerate(rankings):
                ranking.rank = i + 1
                
                # Update story status and rank
                story_result = await db.execute(
                    select(StoryCandidate).where(StoryCandidate.id == ranking.story_candidate_id)
                )
                story = story_result.scalar_one_or_none()
                if story:
                    story.rank = ranking.rank
                    story.status = StoryStatus.RANKED
            
            await db.commit()
            return rankings
    
    async def _score_story(
        self,
        db: AsyncSession,
        story: StoryCandidate,
    ) -> StoryRankingResult:
        """Calculate detailed ranking scores for a story."""
        
        details = {}
        
        # 1. Coherence (0-1) - How well the narrative arc holds together
        coherence = self._calculate_coherence(story)
        details["coherence"] = coherence
        
        # 2. Engagement (0-1) - Potential to hold viewer attention
        engagement = self._calculate_engagement(story)
        details["engagement"] = engagement
        
        # 3. Completeness (0-1) - How well the story covers available footage
        completeness = self._calculate_completeness(db, story)
        details["completeness"] = completeness
        
        # 4. Footage Coverage (0-1) - Percentage of available shots used
        footage_coverage = await self._calculate_footage_coverage(db, story)
        details["footage_coverage"] = footage_coverage
        
        # 5. Confidence (0-1) - From the generation process
        confidence = story.confidence or 0.5
        details["confidence"] = confidence
        
        # Composite score
        composite = (
            self.weights["coherence"] * coherence +
            self.weights["engagement"] * engagement +
            self.weights["completeness"] * completeness +
            self.weights["footage_coverage"] * footage_coverage +
            self.weights["confidence"] * confidence
        )
        
        return StoryRankingResult(
            story_candidate_id=story.id,
            coherence_score=coherence,
            engagement_score=engagement,
            completeness_score=completeness,
            footage_coverage_score=footage_coverage,
            confidence_score=confidence,
            composite_score=composite,
            details=details,
        )
    
    def _calculate_coherence(self, story: StoryCandidate) -> float:
        """Calculate narrative coherence based on structure."""
        score = 0.5
        
        if not story.narrative_arc:
            return score
        
        arc = story.narrative_arc
        
        # Has acts structure
        if "acts" in arc and arc["acts"]:
            num_acts = len(arc["acts"])
            if 1 <= num_acts <= 5:
                score += 0.15
            
            # Check for proper progression
            durations = [a.get("duration", 0) for a in arc["acts"]]
            if all(d > 0 for d in durations):
                score += 0.1
        
        # Has themes
        if "themes" in arc and arc["themes"]:
            score += 0.1
        
        # Has defined tone
        if "tone" in arc and arc["tone"]:
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _calculate_engagement(self, story: StoryCandidate) -> float:
        """Calculate engagement potential."""
        score = 0.5
        
        # Shorter estimated duration = higher engagement potential
        if story.estimated_duration:
            if story.estimated_duration <= 60:  # 1 minute
                score += 0.2
            elif story.estimated_duration <= 180:  # 3 minutes
                score += 0.1
            elif story.estimated_duration <= 300:  # 5 minutes
                ...
            else:
                score -= 0.1
        
        # Hook structure (first act importance)
        if story.narrative_arc and "acts" in story.narrative_arc:
            first_act = story.narrative_arc["acts"][0] if story.narrative_arc["acts"] else None
            if first_act:
                # First act should be punchy
                first_duration = first_act.get("duration", 0)
                if 0 < first_duration <= 30:  # Strong hook
                    score += 0.15
        
        # Emotional/energetic tone boosts engagement
        if story.narrative_arc and story.narrative_arc.get("tone") in ["energetic", "emotional"]:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _calculate_completeness(self, db: AsyncSession, story: StoryCandidate) -> float:
        """How well the story incorporates available analysis."""
        score = 0.5
        
        if not story.narrative_arc:
            return score
        
        arc = story.narrative_arc
        
        # Has shots assigned
        if "total_shots" in arc:
            score += 0.15
        
        # Has themes
        if "themes" in arc and arc["themes"]:
            score += 0.1
        
        # Has structured acts
        if "acts" in arc and arc["acts"]:
            total_act_shots = sum(a.get("shot_count", 0) for a in arc["acts"])
            if total_act_shots > 0:
                score += 0.1
        
        return max(0.0, min(1.0, score))
    
    async def _calculate_footage_coverage(
        self, db: AsyncSession, story: StoryCandidate
    ) -> float:
        """Percentage of available shots referenced by the story."""
        # Get total shots in project
        total_shots_result = await db.execute(
            select(VideoShot)
            .join(VideoShot.media_asset)
            .where(VideoShot.media_asset.has(project_id=story.project_id))
        )
        total_shots = len(total_shots_result.scalars().all())
        
        if total_shots == 0:
            return 0.0
        
        # Story references some shots
        if "total_shots" in story.narrative_arc:
            story_shots = story.narrative_arc["total_shots"]
            return min(1.0, story_shots / total_shots)
        
        return 0.3
    
    async def select_best_story(
        self,
        project_id: uuid.UUID,
    ) -> Optional[StoryCandidate]:
        """Select the highest-ranked story candidate."""
        rankings = await self.rank_stories(project_id)
        
        if not rankings:
            return None
        
        best = rankings[0]
        
        async with database.async_session_maker() as db:
            story_result = await db.execute(
                select(StoryCandidate).where(StoryCandidate.id == best.story_candidate_id)
            )
            story = story_result.scalar_one_or_none()
            if story:
                story.status = StoryStatus.SELECTED
                await db.commit()
        
        return story


# Singleton
_story_ranker_service: Optional["StoryRankerService"] = None


def get_story_ranker_service(): return StoryRankerService()

