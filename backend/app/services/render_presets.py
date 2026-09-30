"""Idempotent seed data for the built-in render presets."""

from __future__ import annotations

from sqlalchemy import select

from app.core import database
from app.models import RenderPreset, RenderPresetPlatform


DEFAULT_PRESETS = (
    dict(name="Preview (Fast)", platform=RenderPresetPlatform.CUSTOM, width=640, height=360, fps=30, crf=28, preset="ultrafast", is_default=True),
    dict(name="YouTube 1080p", platform=RenderPresetPlatform.YOUTUBE, width=1920, height=1080, fps=30, crf=23, preset="medium", is_default=True),
    dict(name="YouTube 4K", platform=RenderPresetPlatform.YOUTUBE, width=3840, height=2160, fps=30, crf=21, preset="slow", is_default=False),
    dict(name="Shorts/Reels 1080x1920", platform=RenderPresetPlatform.SHORTS, width=1080, height=1920, fps=30, crf=23, preset="medium", is_default=True),
    dict(name="Instagram Feed 1080x1080", platform=RenderPresetPlatform.INSTAGRAM, width=1080, height=1080, fps=30, crf=23, preset="medium", is_default=True),
    dict(name="Generic 1080p", platform=RenderPresetPlatform.GENERIC, width=1920, height=1080, fps=30, crf=23, preset="medium", is_default=False),
)


async def ensure_default_render_presets() -> int:
    """Insert missing defaults and return the number of rows inserted."""

    inserted = 0
    async with database.async_session_maker() as db:
        existing = await db.execute(select(RenderPreset.name))
        existing_names = set(existing.scalars().all())
        for values in DEFAULT_PRESETS:
            if values["name"] in existing_names:
                continue
            db.add(
                RenderPreset(
                    **values,
                    video_codec="libx264",
                    video_bitrate=None,
                    audio_codec="aac",
                    audio_bitrate="128k",
                    pixel_format="yuv420p",
                    container="mp4",
                )
            )
            inserted += 1
            existing_names.add(values["name"])
        await db.commit()
    return inserted
