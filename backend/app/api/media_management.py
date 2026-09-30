
from fastapi import APIRouter
from app.services.media_management_service import MediaManagementService
from app.models.media_management import *

router = APIRouter()
service = MediaManagementService()

@router.get("/")
def get_media_management_info():
    return service.get_info()
