"""
Preview rendering settings and utilities.
Fast, low-resolution rendering for quick feedback.
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class PreviewSettings:
    """Settings for preview rendering."""
    width: int = 640
    height: int = 360
    fps: int = 30
    video_codec: str = "libx264"
    video_bitrate: str = None  # Use CRF instead
    crf: int = 28
    preset: str = "ultrafast"
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"
    pixel_format: str = "yuv420p"
    audio_sample_rate: int = 48000
    container: str = "mp4"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for FFmpeg."""
        return {
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "video_codec": self.video_codec,
            "video_bitrate": self.video_bitrate,
            "crf": self.crf,
            "preset": self.preset,
            "audio_codec": self.audio_codec,
            "audio_bitrate": self.audio_bitrate,
            "pixel_format": self.pixel_format,
            "audio_sample_rate": self.audio_sample_rate,
            "container": self.container,
        }


# Default preview settings
DEFAULT_PREVIEW_SETTINGS = PreviewSettings()


def get_preview_settings() -> PreviewSettings:
    """Get default preview settings."""
    return DEFAULT_PREVIEW_SETTINGS


def create_preview_settings(
    width: int = 640,
    height: int = 360,
    fps: int = 30,
    crf: int = 28,
) -> PreviewSettings:
    """Create custom preview settings."""
    return PreviewSettings(
        width=width,
        height=height,
        fps=fps,
        crf=crf,
    )