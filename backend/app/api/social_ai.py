from fastapi import APIRouter
from app.services.social_ai import SocialAIEngine

router = APIRouter()
social_engine = SocialAIEngine()

@router.get("/status")
def status():
    return {"status": "SocialAIEngine is ready."}
