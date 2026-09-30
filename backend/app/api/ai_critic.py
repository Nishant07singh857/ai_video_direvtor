from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from app.services.ai_critic import AICriticService, CriticReport

router = APIRouter()
critic_service = AICriticService()

class TimelineRequest(BaseModel):
    timeline: Dict[str, Any]

@router.post("/analyze", response_model=CriticReport)
async def analyze_timeline(request: TimelineRequest):
    try:
        report = await critic_service.analyze(request.timeline)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
