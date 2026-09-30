from fastapi import APIRouter
from app.services.auto_director import InvincibleAutoDirector

router = APIRouter()
director = InvincibleAutoDirector()

@router.get("/status")
def get_status():
    return {"status": "AutoDirector is ready", "dictionary_path": director.dictionary_path}
