from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_provider import MockAIProvider

router = APIRouter()
provider = MockAIProvider()

class TextPrompt(BaseModel):
    prompt: str

class VisionPrompt(BaseModel):
    image_url: str
    prompt: str

class AudioPrompt(BaseModel):
    audio_url: str

@router.post("/generate_text")
async def generate_text(req: TextPrompt):
    res = await provider.generate_text(req.prompt)
    return {"result": res}

@router.post("/analyze_vision")
async def analyze_vision(req: VisionPrompt):
    res = await provider.analyze_vision(req.image_url, req.prompt)
    return {"result": res}

@router.post("/process_audio")
async def process_audio(req: AudioPrompt):
    res = await provider.process_audio(req.audio_url)
    return res
