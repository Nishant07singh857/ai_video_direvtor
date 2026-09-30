import asyncio
from dataclasses import dataclass

import os
from typing import Optional, Dict, Any


@dataclass
class AudioInfo:
    """Audio stream information extracted via FFprobe."""
    has_audio: bool = False
    audio_streams: int = 0
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    codec: Optional[str] = None
    bitrate: Optional[int] = None
    duration: Optional[float] = None
    codec_long_name: Optional[str] = None
    codec_time_base: Optional[str] = None


class AudioAnalyzer:
    """Extracts technical audio information from media files.
    
    Uses FFprobe to extract real audio stream metadata without
    inventing or fabricating any information.
    """
    
    def __init__(self):
        try:
            from app.core.config import settings
            configured_probe = settings.FFPROBE_PATH
            configured_ffmpeg = settings.FFMPEG_PATH
        except Exception:
            configured_probe = configured_ffmpeg = None
        self.ffprobe_path = configured_probe or os.getenv("FFPROBE_PATH", "ffprobe") or "ffprobe"
        self.ffmpeg_path = configured_ffmpeg or os.getenv("FFMPEG_PATH", "ffmpeg") or "ffmpeg"
    
    async def analyze(self, file_path: str) -> AudioInfo:
        """Extract audio stream information from a media file.
        
        Uses FFprobe to extract audio stream metadata including:
        - presence of audio
        - number of audio streams
        - codec, sample rate, channels, bitrate, duration
        
        Returns:
            AudioInfo object with all extracted information
        """
        try:
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-select_streams", "a",
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                # FFprobe might fail if there are no audio streams
                # Check if it's a "no streams" error
                stderr_text = stderr.decode() if stderr else ""
                if "does not contain any stream" in stderr_text:
                    return AudioInfo(has_audio=False, audio_streams=0)
                raise RuntimeError(f"FFprobe failed: {stderr_text}")
            
            if not stdout or not stdout.strip():
                return AudioInfo(has_audio=False, audio_streams=0)
            
            import json
            data = json.loads(stdout.decode())
            return self._parse_audio_info(data, file_path)
            
        except FileNotFoundError:
            raise RuntimeError("FFprobe not found. Please install FFmpeg.")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse FFprobe output: {e}")
    
    def _parse_audio_info(self, data: Dict[str, Any], file_path: str) -> AudioInfo:
        """Parse FFprobe JSON output into AudioInfo."""
        streams = data.get("streams", [])
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        
        info = AudioInfo(
            has_audio=len(audio_streams) > 0,
            audio_streams=len(audio_streams),
        )
        
        if not audio_streams:
            return info
        
        # Use first audio stream for primary info
        primary = audio_streams[0]
        
        info.sample_rate = int(primary.get("sample_rate", 0)) if primary.get("sample_rate") else None
        info.channels = primary.get("channels")
        info.codec = primary.get("codec_name")
        info.codec_long_name = primary.get("codec_long_name")
        info.codec_time_base = primary.get("codec_time_base")
        
        # Bitrate
        bitrate = primary.get("bit_rate")
        info.bitrate = int(bitrate) if bitrate else None
        
        # Duration
        duration = primary.get("duration")
        info.duration = float(duration) if duration else None
        
        # If no duration in audio stream, try format duration
        if info.duration is None:
            # Try getting duration from format
            try:
                import subprocess
                cmd = [
                    self.ffprobe_path,
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    file_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout:
                    import json
                    fmt_data = json.loads(result.stdout)
                    fmt_duration = fmt_data.get("format", {}).get("duration")
                    info.duration = float(fmt_duration) if fmt_duration else None
            except Exception:
                ...
        
        return info


# Singleton instance
_audio_analyzer: Optional["AudioAnalyzer"] = None


def get_audio_analyzer() -> AudioAnalyzer:
    global _audio_analyzer
    if _audio_analyzer is None:
        _audio_analyzer = AudioAnalyzer()
    return _audio_analyzer

