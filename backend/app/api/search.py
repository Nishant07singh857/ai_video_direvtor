from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import MediaAsset, Project, TranscriptSegment, User, VideoShot

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])

class SearchResult(BaseModel):
    id: UUID
    media_asset_id: UUID
    start_time: float
    end_time: float
    duration: float
    shot_index: int
    confidence: Optional[float]
    similarity: float

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]

@router.get("/search", response_model=SearchResponse)
async def search_video_segments(
    query: str = Query(..., min_length=1, description="Text query to search for in video segments"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return"),
    project_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search for video segments using semantic text search.
    Requires that VideoShot entities have embeddings computed and stored.
    """
    try:
        # The portable baseline searches persisted transcripts.  A future
        # embedding provider can add a vector-ranked branch without exposing
        # another user's assets; ownership is enforced in this query.
        normalized_query = query.strip().lower()
        stmt = (
            select(VideoShot)
            .join(MediaAsset, MediaAsset.id == VideoShot.media_asset_id)
            .join(Project, Project.id == MediaAsset.project_id)
            .join(TranscriptSegment, TranscriptSegment.media_asset_id == MediaAsset.id)
            .where(
                Project.user_id == current_user.id,
                TranscriptSegment.text.ilike(f"%{normalized_query}%"),
            )
        )
        if project_id is not None:
            stmt = stmt.where(Project.id == project_id)
        stmt = stmt.order_by(VideoShot.start_time).limit(limit).distinct()
        result = await db.execute(stmt)
        shots = result.scalars().all()
        
        # 3. Format the results
        search_results = []
        for shot in shots:
            search_results.append(
                SearchResult(
                    id=shot.id,
                    media_asset_id=shot.media_asset_id,
                    start_time=shot.start_time,
                    end_time=shot.end_time,
                    duration=shot.duration,
                    shot_index=shot.shot_index,
                    confidence=shot.confidence,
                    similarity=1.0
                )
            )
            
        return SearchResponse(query=query, results=search_results)
        
    except Exception as e:
        logger.exception("Error during transcript search")
        raise HTTPException(status_code=500, detail="An error occurred during search") from e
