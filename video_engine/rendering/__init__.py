"""
Video Engine Rendering Package.
"""

from video_engine.rendering.timeline_to_ffmpeg import (
    TimelineCompiler,
    ResolvedClip,
    CompileResult,
    FFmpegInputs,
    create_timeline_compiler,
)

from video_engine.rendering.ffmpeg_renderer import (
    FFmpegRenderer,
    RenderProgress,
    RenderResult,
    create_ffmpeg_renderer,
)

from video_engine.rendering.preview import (
    PreviewSettings,
    DEFAULT_PREVIEW_SETTINGS,
    get_preview_settings,
    create_preview_settings,
)

from video_engine.rendering.export import (
    ExportPreset,
    ExportPlatform,
    EXPORT_PRESETS,
    get_export_presets,
    get_preset_by_name,
    get_presets_by_platform,
    get_default_preset,
    create_custom_preset,
)

__all__ = [
    # Timeline compiler
    "TimelineCompiler",
    "ResolvedClip",
    "CompileResult",
    "FFmpegInputs",
    "create_timeline_compiler",
    # FFmpeg renderer
    "FFmpegRenderer",
    "RenderProgress",
    "RenderResult",
    "create_ffmpeg_renderer",
    # Preview
    "PreviewSettings",
    "DEFAULT_PREVIEW_SETTINGS",
    "get_preview_settings",
    "create_preview_settings",
    # Export
    "ExportPreset",
    "ExportPlatform",
    "EXPORT_PRESETS",
    "get_export_presets",
    "get_preset_by_name",
    "get_presets_by_platform",
    "get_default_preset",
    "create_custom_preset",
]