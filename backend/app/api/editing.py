import uuid
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.timeline import normalize_timeline
from app.models.editing import EditOperation, EditOperationType
from app.models.phase4 import Timeline
from app.models.project import Project
from app.models.user import User
from app.api.projects import get_current_user, get_project

from fastapi import APIRouter, Depends, HTTPException, status
router = APIRouter()

import copy

def apply_edit_to_timeline(
    timeline_json: dict, 
    operation_type: EditOperationType, 
    parameters: dict, 
    target_item_id: str
) -> dict:
    updated_json = normalize_timeline(timeline_json)
    
    for track in updated_json["tracks"]:
        if "clips" not in track:
            continue
            
        clips = track["clips"]
        for i, clip in enumerate(clips):
            if clip.get("id") == target_item_id:
                if operation_type == EditOperationType.TRIM:
                    # Update source_start and source_end
                    if "trim_start" in parameters:
                        clip["source_start"] = parameters["trim_start"]
                    elif "source_start" in parameters:
                        clip["source_start"] = parameters["source_start"]
                        
                    if "trim_end" in parameters:
                        clip["source_end"] = parameters["trim_end"]
                    elif "source_end" in parameters:
                        clip["source_end"] = parameters["source_end"]
                        
                    clip["source_duration"] = clip["source_end"] - clip["source_start"]
                    clip["timeline_duration"] = clip["source_duration"]
                    clip["timeline_end"] = clip["timeline_start"] + clip["timeline_duration"]
                    
                elif operation_type == EditOperationType.SPLIT:
                    split_time = parameters.get("split_time")
                    if split_time is not None:
                        duration1 = split_time - clip["timeline_start"]
                        
                        clip1 = copy.deepcopy(clip)
                        clip1["id"] = f"{clip['id']}_1"
                        clip1["source_end"] = clip1["source_start"] + duration1
                        clip1["source_duration"] = duration1
                        clip1["timeline_end"] = split_time
                        clip1["timeline_duration"] = duration1
                        
                        clip2 = copy.deepcopy(clip)
                        clip2["id"] = f"{clip['id']}_2"
                        clip2["source_start"] = clip1["source_end"]
                        clip2["source_duration"] = clip["source_end"] - clip2["source_start"]
                        clip2["timeline_start"] = split_time
                        clip2["timeline_duration"] = clip2["source_duration"]
                        
                        track["clips"] = clips[:i] + [clip1, clip2] + clips[i+1:]
                        
                elif operation_type == EditOperationType.DELETE:
                    deleted_duration = clip["timeline_duration"]
                    track["clips"].pop(i)
                    # Shift subsequent clips backward
                    for j in range(i, len(track["clips"])):
                        track["clips"][j]["timeline_start"] -= deleted_duration
                        track["clips"][j]["timeline_end"] -= deleted_duration
                        
                elif operation_type == EditOperationType.MOVE:
                    new_start = parameters.get("new_start_time", parameters.get("timeline_start"))
                    if new_start is not None:
                        duration = clip["timeline_duration"]
                        clip["timeline_start"] = new_start
                        clip["timeline_end"] = new_start + duration
                        
                updated_json["total_duration"] = max(
                    [
                        clip.get("timeline_end", 0.0)
                        for current_track in updated_json.get("tracks", [])
                        for clip in current_track.get("clips", [])
                    ]
                    + [0.0]
                )
                updated_json["duration"] = updated_json["total_duration"]
                return updated_json

    updated_json["total_duration"] = max(
        [
            clip.get("timeline_end", 0.0)
            for current_track in updated_json.get("tracks", [])
            for clip in current_track.get("clips", [])
        ]
        + [0.0]
    )
    updated_json["duration"] = updated_json["total_duration"]
    return updated_json

async def get_timeline(
    timeline_id: uuid.UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
) -> Timeline:
    result = await db.execute(
        select(Timeline).where(
            Timeline.id == timeline_id,
            Timeline.project_id == project.id,
        )
    )
    timeline = result.scalar_one_or_none()
    if not timeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeline not found",
        )
    return timeline

@router.get("/projects/{project_id}/timelines")
async def list_timelines(
    project_id: uuid.UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Timeline)
        .where(Timeline.project_id == project.id)
        .order_by(Timeline.created_at.desc())
    )
    timelines = result.scalars().all()
    return timelines

@router.get("/projects/{project_id}/timelines/{timeline_id}")
async def get_timeline_endpoint(
    project_id: uuid.UUID,
    timeline_id: uuid.UUID,
    timeline: Timeline = Depends(get_timeline),
):
    return timeline

@router.patch("/projects/{project_id}/timelines/{timeline_id}")
async def update_timeline(
    project_id: uuid.UUID,
    timeline_id: uuid.UUID,
    data: Dict[str, Any],
    project: Project = Depends(get_project),
    timeline: Timeline = Depends(get_timeline),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a canonical timeline with optimistic concurrency protection.

    ``expected_version`` is transport metadata, not timeline content.  A
    stale editor receives 409 rather than silently overwriting a newer AI or
    human edit.
    """
    raw_expected_version = data.pop("expected_version", None)
    if raw_expected_version is not None:
        try:
            expected_version = int(raw_expected_version)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="expected_version must be an integer") from exc
        if expected_version != timeline.version_number:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Timeline changed since it was loaded. Refresh before saving.",
            )

    current_json = dict(timeline.timeline_json or {})
    current_json.update(data)
    canonical_json = normalize_timeline(current_json)
    next_version = timeline.version_number + 1
    try:
        result = await db.execute(
            update(Timeline)
            .where(
                Timeline.id == timeline.id,
                Timeline.version_number == timeline.version_number,
            )
            .values(
                timeline_json=canonical_json,
                total_duration=float(canonical_json.get("total_duration", 0.0)),
                version_number=next_version,
            )
        )
        if result.rowcount != 1:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Timeline changed since it was loaded. Refresh before saving.",
            )
        await db.commit()
        timeline = await db.get(Timeline, timeline.id)
        if timeline is None:
            raise HTTPException(status_code=404, detail="Timeline not found after update")
        await db.refresh(timeline)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return timeline


from pydantic import BaseModel
class TimelineCreate(BaseModel):
    name: str = "Timeline"
    resolution_width: int = 1920
    resolution_height: int = 1080
    fps: float = 30.0

@router.post("/projects/{project_id}/timelines", status_code=status.HTTP_201_CREATED)
async def create_timeline(
    project_id: uuid.UUID,
    data: TimelineCreate,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    timeline = Timeline(
        project_id=project_id,
        version_number=1,
        timeline_json={
            "name": data.name,
            "resolution_width": data.resolution_width,
            "resolution_height": data.resolution_height,
            "fps": data.fps,
            "tracks": []
        },
        total_duration=0.0,
    )
    db.add(timeline)
    try:
        await db.commit()
        await db.refresh(timeline)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return timeline

@router.post("/projects/{project_id}/timelines/{timeline_id}/edits")
async def apply_edit_operation(
    project_id: uuid.UUID,
    timeline_id: uuid.UUID,
    operation_type: EditOperationType,
    parameters: Dict[str, Any],
    target_item_id: Optional[str] = None,
    project: Project = Depends(get_project),
    timeline: Timeline = Depends(get_timeline),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Apply an edit operation (TRIM, SPLIT, DELETE, MOVE) to a timeline.
    """
    # Get the max sequence order to append the new operation
    result = await db.execute(
        select(func.max(EditOperation.sequence_order)).where(
            EditOperation.timeline_id == timeline_id
        )
    )
    max_seq = result.scalar() or 0
    
    # Create the operation
    edit_op = EditOperation(
        project_id=project_id,
        timeline_id=timeline_id,
        target_item_id=target_item_id,
        operation_type=operation_type,
        parameters=parameters,
        sequence_order=max_seq + 1,
    )
    db.add(edit_op)
    
    # Apply to timeline_json
    if timeline.timeline_json:
        # sqlalchemy JSON tracking requires assignment to register change
        # dict mutation directly doesn't always trigger update
        updated_json = apply_edit_to_timeline(
            timeline.timeline_json,
            operation_type,
            parameters,
            target_item_id
        )
        # Re-assign to trigger dirty tracking
        # Wait, for SQLAlchemy to track JSON mutations reliably, we create a new dict, which we did inside apply_edit_to_timeline
        # Just assign the copy back
        timeline.timeline_json = updated_json
    
    # Update timeline version
    timeline.version_number += 1
    
    try:
        await db.commit()
        await db.refresh(edit_op)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    return {
        "id": edit_op.id,
        "operation_type": edit_op.operation_type,
        "parameters": edit_op.parameters,
        "sequence_order": edit_op.sequence_order,
        "target_item_id": edit_op.target_item_id,
    }

@router.get("/projects/{project_id}/timelines/{timeline_id}/edits")
async def list_edit_operations(
    project_id: uuid.UUID,
    timeline_id: uuid.UUID,
    project: Project = Depends(get_project),
    timeline: Timeline = Depends(get_timeline),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all edit operations for a timeline."""
    result = await db.execute(
        select(EditOperation)
        .where(EditOperation.timeline_id == timeline_id)
        .order_by(EditOperation.sequence_order.asc())
    )
    edits = result.scalars().all()
    
    return {
        "edits": [
            {
                "id": edit.id,
                "operation_type": edit.operation_type,
                "parameters": edit.parameters,
                "sequence_order": edit.sequence_order,
                "target_item_id": edit.target_item_id,
                "is_undone": edit.is_undone,
            }
            for edit in edits
        ]
    }

@router.post("/projects/{project_id}/timelines/{timeline_id}/undo")
async def undo_last_edit(
    project_id: uuid.UUID,
    timeline_id: uuid.UUID,
    project: Project = Depends(get_project),
    timeline: Timeline = Depends(get_timeline),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Undo the last edit operation."""
    # Find last applied operation
    result = await db.execute(
        select(EditOperation)
        .where(
            EditOperation.timeline_id == timeline_id,
            EditOperation.is_undone == False
        )
        .order_by(EditOperation.sequence_order.desc())
        .limit(1)
    )
    last_edit = result.scalar_one_or_none()
    
    if not last_edit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No edit operations to undo",
        )
        
    last_edit.is_undone = True
    timeline.version_number += 1
    
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success", "undone_operation_id": last_edit.id}
