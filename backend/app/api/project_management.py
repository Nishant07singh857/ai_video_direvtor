
from fastapi import APIRouter
from app.services.project_management_service import ProjectManagementService
from app.models.project_management import *

router = APIRouter()
service = ProjectManagementService()

@router.get("/")
def get_project_management_info():
    return service.get_info()
