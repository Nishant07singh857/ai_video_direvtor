from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from app.services.rlhf_learning_loop import ContinuousLearningEngine

router = APIRouter()
rlhf_engine = ContinuousLearningEngine()

class CorrectionRequest(BaseModel):
    original_prompt: str
    ai_output: str
    user_correction: str
    new_correct_output: str

@router.post("/correction")
async def submit_correction(request: CorrectionRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Captures user feedback when the AI makes a mistake (RLHF).
    Saves it to the JSONL log and triggers background fine-tuning.
    """
    success = rlhf_engine.capture_user_correction(
        original_prompt=request.original_prompt,
        ai_output=request.ai_output,
        user_correction=request.user_correction,
        new_correct_output=request.new_correct_output
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write correction to database.")
        
    # Trigger the heavy fine-tuning job in the background so the API returns instantly
    background_tasks.add_task(rlhf_engine.trigger_background_retraining)
    
    return {
        "status": "success",
        "message": "Correction saved. The AI is retraining in the background and will not make this mistake again."
    }
