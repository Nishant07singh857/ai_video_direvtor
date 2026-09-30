from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from app.services.ai_memory import AIMemoryEngine

router = APIRouter()
memory_engine = AIMemoryEngine()

class MemoryFailureRequest(BaseModel):
    ai_decision: str
    user_correction: str

@router.post("/analyze_failure")
def analyze_failure(request: MemoryFailureRequest):
    try:
        root_cause = memory_engine._analyze_failure(request.ai_decision, request.user_correction)
        return {"root_cause": root_cause}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
