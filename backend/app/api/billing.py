
from fastapi import APIRouter
from app.services.billing_service import BillingService
from app.models.billing import *

router = APIRouter()
service = BillingService()

@router.get("/")
def get_billing_info():
    return service.get_info()
