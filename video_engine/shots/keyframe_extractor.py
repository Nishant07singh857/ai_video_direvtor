import asyncio
import uuid
import os
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from video_engine.ingestion.processor import MediaProcessor

@dataclass
class ExtractedKeyframe:
    """Represents an extracted keyframe."""
    timestamp: float
    frame_index: Optional[int]
    storage_key: str
    width: int
    height: int
    shot_index: Optional[int] = None

class KeyframeExtractor:
    """Extracts representative keyframes from video shots."""
    
    def __init__(
        self,
        max_keyframes_per_shot: int = 2,
        keyframe_width: int = 640,
        quality: int = 2,
        ffmpeg_path: str = "ffmpeg"
    ):
        self.max_keyframes_per_shot = max_keyframes_per_shot
        self.keyframe_width = keyframe_width
        self.quality = quality
        try:
            from app.core.config import settings
            configured_ffmpeg = settings.FFMPEG_PATH
        except Exception:
            configured_ffmpeg = None
        self.ffmpeg_path = configured_ffmpeg or os.getenv("FFMPEG_PATH", ffmpeg_path) or ffmpeg_path
        self._processor = MediaProcessor()
    
    async def extract_keyframes_for_shot(
        self,
        video_path: str,
        shot_start: float,
        shot_end: float,
        shot_index: int,
        output_dir: str,
    ) -> List[ExtractedKeyframe]:
        shot_duration = shot_end - shot_start
        if shot_duration <= 0:
            return []
        
        timestamps = []
        first_frame_time = min(shot_start + 0.1, shot_start + shot_duration * 0.1)
        timestamps.append((first_frame_time, "first"))
        
        if self.max_keyframes_per_shot >= 2:
            middle_time = (shot_start + shot_end) / 2
            timestamps.append((middle_time, "middle"))
        
        keyframes = []
        for timestamp, label in timestamps:
            if timestamp >= shot_end:
                continue
                
            try:
                keyframe = await self._extract_single_keyframe(
                    video_path=video_path,
                    timestamp=timestamp,
                    shot_index=shot_index,
                    label=label,
                    output_dir=output_dir
                )
                if keyframe:
                    keyframes.append(keyframe)
            except Exception:
                continue
        
        return keyframes
    
    async def _extract_single_keyframe(
        self,
        video_path: str,
        timestamp: float,
        shot_index: int,
        label: str,
        output_dir: str
    ) -> Optional[ExtractedKeyframe]:
        shot_key = f"shot_{shot_index}_{label}_{uuid.uuid4().hex[:8]}.jpg"
        output_path = os.path.join(output_dir, shot_key)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", str(timestamp),
            "-i", video_path,
            "-vframes", "1",
            "-vf", f"scale={self.keyframe_width}:-1",
            "-q:v", str(self.quality),
            "-update", "1",
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg keyframe extraction failed: {stderr.decode() if stderr else ''}")
        
        try:
            import cv2
            frame = cv2.imread(output_path)
            if frame is not None:
                height, width = frame.shape[:2]
            else:
                width, height = 640, 360
        except ImportError:
            width, height = 640, 360
        
        frame_index = int(timestamp * 30)
        
        return ExtractedKeyframe(
            timestamp=timestamp,
            frame_index=frame_index,
            storage_key=shot_key,
            width=width,
            height=height,
            shot_index=shot_index,
        )


_keyframe_extractor: Optional[KeyframeExtractor] = None


def get_keyframe_extractor() -> KeyframeExtractor:
    global _keyframe_extractor
    if _keyframe_extractor is None:
        _keyframe_extractor = KeyframeExtractor()
    return _keyframe_extractor
