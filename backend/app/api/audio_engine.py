from fastapi import APIRouter
from video_engine.audio.engine import AudioEngine

router = APIRouter()
engine = AudioEngine()

@router.get("/config")
def get_config():
    return {
        "ducking_target_volume": engine.ducking_target_volume,
        "ducking_attack_time": engine.ducking_attack_time,
        "ducking_release_time": engine.ducking_release_time,
        "base_music_volume": engine.base_music_volume,
    }
