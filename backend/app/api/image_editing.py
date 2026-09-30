
from fastapi import APIRouter
from app.services.image_editing_service import ImageEditingService
from app.models.image_editing import *

router = APIRouter()
service = ImageEditingService()

@router.get("/")
def get_image_editing_info():
    return service.get_info()
