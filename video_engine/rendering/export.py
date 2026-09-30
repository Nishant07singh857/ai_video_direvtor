"""
Export rendering settings and presets.
High-quality rendering for final output.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class ExportPlatform(str, Enum):
    """Target platform for export."""
    GENERIC = "generic"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    SHORTS = "shorts"
    REELS = "reels"
    TIKTOK = "tiktok"
    CUSTOM = "custom"


@dataclass
class ExportPreset:
    """Settings for export rendering."""
    name: str
    platform: ExportPlatform
    width: int
    height: int
    fps: int = 30
    video_codec: str = "libx264"
    video_bitrate: Optional[str] = None  # Use CRF if None
    crf: int = 23
    preset: str = "medium"
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"
    pixel_format: str = "yuv420p"
    audio_sample_rate: int = 48000
    container: str = "mp4"
    # Advanced options
    profile: Optional[str] = None  # e.g., "high" for H.264
    level: Optional[str] = None    # e.g., "4.1" for H.264
    color_primaries: Optional[str] = None
    color_transfer: Optional[str] = None
    color_space: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for FFmpeg."""
        d = {
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
        # Add advanced options if set
        if self.profile:
            d["profile"] = self.profile
        if self.level:
            d["level"] = self.level
        if self.color_primaries:
            d["color_primaries"] = self.color_primaries
        if self.color_transfer:
            d["color_transfer"] = self.color_transfer
        if self.color_space:
            d["color_space"] = self.color_space
        return d


# Default export presets
EXPORT_PRESETS: List[ExportPreset] = [
    # Preview (fast, low quality)
    ExportPreset(
        name="Preview (Fast)",
        platform=ExportPlatform.CUSTOM,
        width=640,
        height=360,
        fps=30,
        crf=28,
        preset="ultrafast",
    ),

    # Generic 1080p
    ExportPreset(
        name="Generic 1080p",
        platform=ExportPlatform.GENERIC,
        width=1920,
        height=1080,
        fps=30,
        crf=23,
        preset="medium",
    ),

    # YouTube 1080p
    ExportPreset(
        name="YouTube 1080p",
        platform=ExportPlatform.YOUTUBE,
        width=1920,
        height=1080,
        fps=30,
        crf=23,
        preset="medium",
        profile="high",
        level="4.1",
    ),

    # YouTube 4K
    ExportPreset(
        name="YouTube 4K",
        platform=ExportPlatform.YOUTUBE,
        width=3840,
        height=2160,
        fps=30,
        crf=21,
        preset="slow",
        profile="high",
        level="5.1",
    ),

    # Shorts/Reels/TikTok (vertical 1080x1920)
    ExportPreset(
        name="Shorts/Reels 1080x1920",
        platform=ExportPlatform.SHORTS,
        width=1080,
        height=1920,
        fps=30,
        crf=23,
        preset="medium",
        profile="high",
        level="4.1",
    ),

    # Instagram Feed (square 1080x1080)
    ExportPreset(
        name="Instagram Feed 1080x1080",
        platform=ExportPlatform.INSTAGRAM,
        width=1080,
        height=1080,
        fps=30,
        crf=23,
        preset="medium",
        profile="high",
        level="4.1",
    ),

    # Instagram Story/Reels (same as Shorts)
    ExportPreset(
        name="Instagram Story/Reels 1080x1920",
        platform=ExportPlatform.REELS,
        width=1080,
        height=1920,
        fps=30,
        crf=23,
        preset="medium",
        profile="high",
        level="4.1",
    ),

    # High Quality Generic
    ExportPreset(
        name="High Quality 1080p",
        platform=ExportPlatform.GENERIC,
        width=1920,
        height=1080,
        fps=30,
        crf=18,
        preset="slow",
        profile="high",
        level="4.1",
    ),

    # 4K High Quality
    ExportPreset(
        name="High Quality 4K",
        platform=ExportPlatform.GENERIC,
        width=3840,
        height=2160,
        fps=30,
        crf=18,
        preset="slow",
        profile="high",
        level="5.1",
    ),
]


def get_export_presets() -> List[ExportPreset]:
    """Get all available export presets."""
    return EXPORT_PRESETS


def get_preset_by_name(name: str) -> Optional[ExportPreset]:
    """Get preset by name."""
    for preset in EXPORT_PRESETS:
        if preset.name == name:
            return preset
    return None


def get_presets_by_platform(platform: ExportPlatform) -> List[ExportPreset]:
    """Get all presets for a platform."""
    return [p for p in EXPORT_PRESETS if p.platform == platform]


def get_default_preset(platform: ExportPlatform = ExportPlatform.GENERIC) -> ExportPreset:
    """Get the default preset for a platform."""
    presets = get_presets_by_platform(platform)
    if not presets:
        # Fall back to generic
        presets = get_presets_by_platform(ExportPlatform.GENERIC)
    return presets[0] if presets else EXPORT_PRESETS[1]  # Generic 1080p


def create_custom_preset(
    name: str,
    width: int,
    height: int,
    fps: int = 30,
    crf: int = 23,
    preset: str = "medium",
    platform: ExportPlatform = ExportPlatform.CUSTOM,
) -> ExportPreset:
    """Create a custom export preset."""
    return ExportPreset(
        name=name,
        platform=platform,
        width=width,
        height=height,
        fps=fps,
        crf=crf,
        preset=preset,
    )