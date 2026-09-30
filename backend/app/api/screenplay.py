
from fastapi import APIRouter
from app.services.screenplay_service import ScreenplayService
from app.models.screenplay import *

router = APIRouter()
service = ScreenplayService()

@router.get("/")
def get_screenplay_info():
    return service.get_info()
