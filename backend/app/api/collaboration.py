
from fastapi import APIRouter
from app.services.collaboration_service import CollaborationService
from app.models.collaboration import *

router = APIRouter()
service = CollaborationService()

@router.get("/")
def get_collaboration_info():
    return service.get_info()
