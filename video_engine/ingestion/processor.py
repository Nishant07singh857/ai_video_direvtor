import asyncio
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

import os


@dataclass
class MediaMetadata:
    """Extracted media metadata."""
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    bitrate: Optional[int] = None
    format_name: Optional[str] = None
    streams: Optional[list] = None


class MediaProcessor:
    """Media processing service using FFmpeg/FFprobe."""

    def __init__(self):
        try:
            from app.core.config import settings
            configured_probe = settings.FFPROBE_PATH
            configured_ffmpeg = settings.FFMPEG_PATH
        except Exception:
            configured_probe = configured_ffmpeg = None
        self.ffprobe_path = configured_probe or os.getenv("FFPROBE_PATH", "ffprobe") or "ffprobe"
        self.ffmpeg_path = configured_ffmpeg or os.getenv("FFMPEG_PATH", "ffmpeg") or "ffmpeg"

    async def extract_metadata(self, file_path: str) -> MediaMetadata:
        """Extract metadata from a media file using FFprobe."""
        try:
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"FFprobe failed: {stderr.decode()}")
            
            data = json.loads(stdout.decode())
            return self._parse_metadata(data)
            
        except FileNotFoundError:
            raise RuntimeError("FFprobe not found. Please install FFmpeg.")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse FFprobe output: {e}")

    def extract_metadata_sync(self, file_path: str) -> MediaMetadata:
        """Synchronous metadata path used by the FFmpeg shot parser."""
        try:
            result = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("FFprobe not found. Please install FFmpeg.") from exc
        if result.returncode != 0:
            raise RuntimeError(f"FFprobe failed: {result.stderr[-2000:]}")
        try:
            return self._parse_metadata(json.loads(result.stdout))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to parse FFprobe output: {exc}") from exc
    

    def _parse_metadata(self, data: Dict[str, Any]) -> MediaMetadata:
        """Parse FFprobe JSON output into MediaMetadata."""
        metadata = MediaMetadata()
        
        # Format info
        format_info = data.get("format", {})
        metadata.duration = float(format_info.get("duration", 0)) if format_info.get("duration") else None
        metadata.bitrate = int(format_info.get("bit_rate", 0)) if format_info.get("bit_rate") else None
        metadata.format_name = format_info.get("format_name")
        
        # Stream info
        streams = data.get("streams", [])
        metadata.streams = streams
        
        for stream in streams:
            if stream.get("codec_type") == "video":
                metadata.width = stream.get("width")
                metadata.height = stream.get("height")
                metadata.video_codec = stream.get("codec_name")
                
                # Parse fps
                r_frame_rate = stream.get("r_frame_rate", "0/1")
                try:
                    num, den = map(int, r_frame_rate.split("/"))
                    if den > 0:
                        metadata.fps = num / den
                except (ValueError, ZeroDivisionError):
                    ...
                    
            elif stream.get("codec_type") == "audio":
                metadata.audio_codec = stream.get("codec_name")
        
        return metadata

    async def generate_thumbnail(
        self,
        input_path: str,
        output_path: str,
        timestamp: str = "00:00:01",
        width: int = 320
    ) -> bool:
        """Generate a thumbnail from a video file."""
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                self.ffmpeg_path,
                "-y",  # Overwrite output
                "-ss", timestamp,
                "-i", input_path,
                "-vframes", "1",
                "-vf", f"scale={width}:-1",
                "-q:v", "2",
                "-update", "1",  # Allow overwriting single image file (required on Windows)
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
            
            return True
            
        except FileNotFoundError:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")

    async def generate_proxy(
        self,
        input_path: str,
        output_path: str,
        width: int = 1280,
        height: int = 720,
        bitrate: str = "2M"
    ) -> bool:
        """Generate a proxy/preview video."""
        try:
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", input_path,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-b:v", bitrate,
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
            
            return True
            
        except FileNotFoundError:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")



# Singleton instance
_media_processor: Optional[MediaProcessor] = None


def get_media_processor() -> MediaProcessor:
    return MediaProcessor()

