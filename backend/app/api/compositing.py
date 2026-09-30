
from fastapi import APIRouter
from app.services.compositing_service import CompositingService
from app.models.compositing import *

router = APIRouter()
service = CompositingService()

@router.get("/")
def get_compositing_info():
    return service.get_info()
