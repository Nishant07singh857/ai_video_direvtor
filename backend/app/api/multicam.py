
from fastapi import APIRouter
from app.services.multicam_service import MulticamService
from app.models.multicam import *

router = APIRouter()
service = MulticamService()

@router.get("/")
def get_multicam_info():
    return service.get_info()
