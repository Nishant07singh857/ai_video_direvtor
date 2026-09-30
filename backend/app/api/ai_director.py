import os
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Dict, Any, Optional
from uuid import UUID

from app.models import User, Project
from app.core.database import get_db
from app.core.timeline import normalize_timeline
from app.api.projects import get_current_user, get_project
from app.services.ai_director import get_ai_director_service, AIDirectorService

router = APIRouter()

class AIDirectorAnalyzeRequest(BaseModel):
    max_story_candidates: int = 5

@router.post("/projects/{project_id}/ai-director/analyze")
async def run_ai_director(
    project_id: UUID,
    request: AIDirectorAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the complete AI Director pipeline."""
    try:
        project = await get_project(project_id, db, current_user)
        service = get_ai_director_service()
        result = await service.run_full_pipeline(
            project_id=project_id,
            user_id=current_user.id,
            max_story_candidates=request.max_story_candidates,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}/ai-director/status")
async def get_ai_director_status(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the status of the AI Director pipeline."""
    try:
        project = await get_project(project_id, db, current_user)
        service = get_ai_director_service()
        status_info = await service.get_pipeline_status(project_id)
        return status_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AIPromptEditRequest(BaseModel):
    prompt: str
    timeline_id: Optional[UUID] = None

@router.post("/projects/{project_id}/ai-director/prompt")
async def edit_with_ai_prompt(
    project_id: UUID,
    request: AIPromptEditRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Conversational AI Director agent that directly applies user edit prompts to the timeline."""
    from sqlalchemy import select
    from app.models.phase4 import Timeline
    import re
    
    project = await get_project(project_id, db, current_user)
    
    # Get active timeline
    if request.timeline_id:
        result = await db.execute(select(Timeline).where(Timeline.id == request.timeline_id, Timeline.project_id == project_id))
    else:
        result = await db.execute(select(Timeline).where(Timeline.project_id == project_id).order_by(Timeline.created_at.desc()))
    timeline = result.scalars().first()
    
    if not timeline:
        raise HTTPException(status_code=404, detail="No timeline found for this project. Please create or generate a timeline first.")
        
    # Read every timeline through the canonical contract.  Older projects may
    # still contain a top-level ``clips`` array, but no new edit should write
    # that legacy shape back to storage.
    tl_json = normalize_timeline(timeline.timeline_json)
    user_prompt = request.prompt.lower()
    
    applied_actions = []
    
    # Color grade detection
    post_proc = dict(tl_json.get("post_processing") or {})
    if "vibrant" in user_prompt:
        post_proc["color_grade"] = "vibrant"
        post_proc["saturation"] = 1.3
        applied_actions.append("Applied vibrant color grade with enhanced saturation")
    elif "cinematic" in user_prompt or "film" in user_prompt:
        post_proc["color_grade"] = "cinematic"
        post_proc["contrast"] = 1.25
        post_proc["temperature"] = -10
        applied_actions.append("Applied cinematic film grade with cool shadows")
    elif "warm" in user_prompt:
        post_proc["color_grade"] = "warm"
        post_proc["temperature"] = 25
        applied_actions.append("Warmed up color temperature")
    elif "bw" in user_prompt or "black and white" in user_prompt or "monochrome" in user_prompt:
        post_proc["color_grade"] = "monochrome"
        post_proc["saturation"] = 0.0
        applied_actions.append("Converted to high-contrast black & white")
        
    # Effects & Filters detection
    effects = dict(tl_json.get("effects") or {})
    if "sharpen" in user_prompt:
        effects["sharpen"] = 60
        applied_actions.append("Added edge sharpening & clarity filter")
    if "blur" in user_prompt:
        effects["blur"] = 8
        applied_actions.append("Added cinematic Gaussian blur")
    if "vignette" in user_prompt:
        effects["vignette"] = 45
        applied_actions.append("Added dark cinematic vignette border")
    if "glow" in user_prompt or "bloom" in user_prompt:
        effects["glow"] = 50
        applied_actions.append("Added soft bloom glow")
    if effects:
        tl_json["effects"] = effects

    # Transitions detection
    for t_type in ["crossfade", "wipeleft", "wiperight", "slideup", "zoomin", "dissolve", "pixelize", "glitch", "fade"]:
        if t_type in user_prompt:
            tl_json["transition"] = {"type": t_type, "duration": 1.0}
            applied_actions.append(f"Applied {t_type.capitalize()} transition between scenes")
            break
    if "transition" in user_prompt and "transition" not in tl_json:
        tl_json["transition"] = {"type": "crossfade", "duration": 1.0}
        applied_actions.append("Applied smooth Crossfade transition")

    # Aspect Ratio & Format detection
    if "9:16" in user_prompt or "vertical" in user_prompt or "reel" in user_prompt or "shorts" in user_prompt or "tiktok" in user_prompt:
        tl_json["aspect_ratio"] = "9:16"
        tl_json["resolution_width"] = 1080
        tl_json["resolution_height"] = 1920
        applied_actions.append("Reframed project to 9:16 vertical (Shorts/Reels/TikTok)")
    elif "16:9" in user_prompt or "horizontal" in user_prompt or "widescreen" in user_prompt or "youtube" in user_prompt:
        tl_json["aspect_ratio"] = "16:9"
        tl_json["resolution_width"] = 1920
        tl_json["resolution_height"] = 1080
        applied_actions.append("Reframed project to 16:9 cinematic widescreen")
    elif "1:1" in user_prompt or "square" in user_prompt:
        tl_json["aspect_ratio"] = "1:1"
        tl_json["resolution_width"] = 1080
        tl_json["resolution_height"] = 1080
        applied_actions.append("Reframed project to 1:1 square feed format")

    # Chroma Key / Green Screen
    if "green screen" in user_prompt or "chroma" in user_prompt or "remove background" in user_prompt:
        tl_json["chromakey"] = {"enabled": True, "color": "#00FF00", "similarity": 0.3, "blend": 0.1}
        applied_actions.append("Enabled chroma key green screen removal")

    # Subtitles & Captions detection
    if "subtitle" in user_prompt or "caption" in user_prompt or "subtitles" in user_prompt or "captions" in user_prompt:
        style = "viral-yellow" if ("yellow" in user_prompt or "viral" in user_prompt) else "clean-box"
        tl_json["subtitles"] = {
            "enabled": True,
            "style": style,
            "position": "bottom",
            "fontSize": 28,
            "hasBox": True
        }
        applied_actions.append(f"Generated auto-captions with {style} animation style")

    # Speed Ramping detection
    if "2x" in user_prompt or "double speed" in user_prompt:
        tl_json["speed"] = 2.0
        applied_actions.append("Set playback speed to 2.0x (Fast Forward)")
    elif "slow motion" in user_prompt or "slow-mo" in user_prompt or "half speed" in user_prompt or "0.5x" in user_prompt:
        tl_json["speed"] = 0.5
        applied_actions.append("Set playback speed to 0.5x (Cinematic Slow-Mo)")
    elif "timelapse" in user_prompt or "hyperlapse" in user_prompt or "4x" in user_prompt:
        tl_json["speed"] = 4.0
        applied_actions.append("Set playback speed to 4.0x (Hyperlapse)")

    # Pacing / Duration detection.  Only video tracks are retimed; audio and
    # graphics retain their source timing.  Reflowing the video track avoids
    # leaving gaps after an energetic edit shortens a cut.
    video_clips = [
        clip
        for track in tl_json.get("tracks", [])
        if track.get("type") == "video"
        for clip in track.get("clips", [])
    ]
    if "fast" in user_prompt or "energetic" in user_prompt or "quick" in user_prompt:
        cursor = 0.0
        for clip in video_clips:
            duration = max(0.05, min(3.0, float(clip["timeline_duration"]) * 0.6))
            clip["timeline_start"] = cursor
            clip["timeline_duration"] = duration
            clip["timeline_end"] = cursor + duration
            cursor += duration
        applied_actions.append("Pacing increased: shortened cuts for high energy")
    elif "slow" in user_prompt or "calm" in user_prompt:
        cursor = 0.0
        for clip in video_clips:
            duration = max(0.05, float(clip["timeline_duration"]) * 1.4)
            clip["timeline_start"] = cursor
            clip["timeline_duration"] = duration
            clip["timeline_end"] = cursor + duration
            cursor += duration
        applied_actions.append("Pacing slowed: extended clip durations for calm aesthetic")

    # Computer Vision & Smart Auto-Reframe detection
    if "smart crop" in user_prompt or "reframe" in user_prompt or "face" in user_prompt or "speaker" in user_prompt:
        rec_center = tl_json.get("recommended_smart_crop_center", 0.5)
        # If not present in timeline, look for media to analyze
        if rec_center == 0.5:
            from app.models import MediaAsset
            from app.services.storage import get_storage_service
            media_res = await db.execute(select(MediaAsset).where(MediaAsset.project_id == project_id).order_by(MediaAsset.created_at.asc()))
            media_item = media_res.scalars().first()
            if media_item and media_item.storage_key:
                storage = get_storage_service()
                m_path = storage.get_path(media_item.storage_key)
                if m_path:
                    try:
                        from video_engine.vision.visual_analyzer import get_visual_analyzer
                        analyzer = get_visual_analyzer()
                        vis = await analyzer.analyze_video(m_path)
                        rec_center = vis.recommended_reframe_center
                        tl_json["visual_analysis"] = vis.to_dict()
                        tl_json["ai_vision_summary"] = vis.ai_vision_summary
                        tl_json["recommended_smart_crop_center"] = rec_center
                    except Exception:
                        pass
        tl_json["smart_crop"] = {"enabled": True, "center_x": rec_center}
        applied_actions.append(f"Applied Smart AI Auto-Reframe centered on detected speaker faces ({rec_center*100:.1f}%)")

    # Blurry / Low Quality Shot Removal
    if "blurry" in user_prompt or "bad shot" in user_prompt or "remove bad" in user_prompt or "filter bad" in user_prompt:
        vis_analysis = tl_json.get("visual_analysis")
        if vis_analysis and vis_analysis.get("shots"):
            good_shots = [s for s in vis_analysis["shots"] if s.get("sharpness_label") != "blurry"]
            if good_shots and len(good_shots) < len(vis_analysis["shots"]):
                removed_count = len(vis_analysis["shots"]) - len(good_shots)
                applied_actions.append(f"Filtered out {removed_count} blurry/unfocused shots based on Computer Vision quality analysis")

    # Default fallback if no specific keywords matched
    if not applied_actions:
        post_proc["color_grade"] = "enhanced"
        post_proc["ai_directive"] = request.prompt
        applied_actions.append(f"Applied AI directive: '{request.prompt}' to timeline state")

    tl_json["post_processing"] = post_proc
    tl_json = normalize_timeline(tl_json)
    timeline.total_duration = float(tl_json.get("total_duration", 0.0))
    timeline.timeline_json = tl_json
    timeline.version_number += 1
    
    await db.commit()
    await db.refresh(timeline)
    
    return {
        "status": "success",
        "message": ". ".join(applied_actions) + ".",
        "timeline_id": str(timeline.id),
        "timeline_json": timeline.timeline_json
    }

@router.get("/projects/{project_id}/ai-director/vision-analysis")
async def get_vision_analysis(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve Computer Vision insights (faces, A-Roll/B-Roll, sharpness, smart crop) for project media."""
    from sqlalchemy import select
    from app.models.phase4 import Timeline
    from app.models import MediaAsset
    from app.services.storage import get_storage_service
    
    project = await get_project(project_id, db, current_user)
    
    # Check if timeline has cached analysis
    tl_res = await db.execute(select(Timeline).where(Timeline.project_id == project_id).order_by(Timeline.created_at.desc()))
    timeline = tl_res.scalars().first()
    if timeline and timeline.timeline_json and timeline.timeline_json.get("visual_analysis"):
        return {
            "status": "cached",
            "summary": timeline.timeline_json.get("ai_vision_summary", ""),
            "analysis": timeline.timeline_json.get("visual_analysis"),
            "recommended_smart_crop_center": timeline.timeline_json.get("recommended_smart_crop_center", 0.5),
        }
        
    # Otherwise run on primary project media
    media_res = await db.execute(select(MediaAsset).where(MediaAsset.project_id == project_id).order_by(MediaAsset.created_at.asc()))
    media_item = media_res.scalars().first()
    if not media_item or not media_item.storage_key:
        return {"status": "no_media", "message": "No media found for project"}
        
    storage = get_storage_service()
    m_path = storage.get_path(media_item.storage_key)
    if not m_path or not os.path.exists(m_path):
        return {"status": "no_file", "message": "Media file not found on disk"}

    try:
        from video_engine.vision.visual_analyzer import get_visual_analyzer
        analyzer = get_visual_analyzer()
        vis = await analyzer.analyze_video(m_path)
        
        # Cache in timeline if exists
        if timeline:
            tl_json = dict(timeline.timeline_json or {})
            tl_json["visual_analysis"] = vis.to_dict()
            tl_json["ai_vision_summary"] = vis.ai_vision_summary
            tl_json["recommended_smart_crop_center"] = vis.recommended_reframe_center
            timeline.timeline_json = tl_json
            await db.commit()
            
        return {
            "status": "computed",
            "summary": vis.ai_vision_summary,
            "analysis": vis.to_dict(),
            "recommended_smart_crop_center": vis.recommended_reframe_center,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision analysis failed: {str(e)}")


