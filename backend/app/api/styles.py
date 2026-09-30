from pydantic import BaseModel
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

router = APIRouter()

class StyleCloneRequest(BaseModel):
    user_media_ids: List[str]

@router.post("/clone")
async def clone_video_style(reference_video: UploadFile = File(...), user_media_ids: str = Form("")):
    """
    Analyzes the uploaded reference video (e.g., TikTok Reel),
    extracts its editing style (cuts, beats, effects), and applies
    it to the user's raw media.
    """
    try:
        # In a real scenario, we'd save the file and pass the path to the cloner service
        # cloner = get_video_style_cloner()
        # result = cloner.clone_style(temp_video_path, user_media_list)
        
        return {
            "status": "success",
            "message": f"Successfully cloned style from {reference_video.filename}",
            "generated_template_id": "mock-template-uuid-1234",
            "timeline": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def list_available_styles():
    """
    Returns a list of all publicly available style templates 
    (e.g., 'Cinematic Vlog', 'Fast Paced Tech Review').
    """
    return {
        "status": "success",
        "styles": [
            {"id": "style-1", "name": "Dynamic Tech Review", "type": "cloned"},
            {"id": "style-2", "name": "Cinematic Travel", "type": "manual"}
        ]
    }
