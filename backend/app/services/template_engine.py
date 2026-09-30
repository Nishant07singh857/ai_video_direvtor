"""Template engine service for Phase 51 - applies templates to user media."""


import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core import database
from app.core.timeline import TIMELINE_SCHEMA
from app.models.template import VideoTemplate

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _TemplateSnapshot:
    """Lightweight carrier of template fields used outside the DB session."""
    id: uuid.UUID
    name: str
    audio_asset_id: uuid.UUID | None
    audio_storage_key: str | None


class TemplateEngine:
    """Applies a VideoTemplate to user-provided media, producing a timeline JSON."""

    async def apply_template(
        self,
        template_id: uuid.UUID,
        user_media_list: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Apply a template to user media and return a renderer-ready timeline JSON.

        Args:
            template_id: UUID of the saved VideoTemplate.
            user_media_list: List of dicts with keys:
                media_asset_id, storage_key, duration, theme, width, height.

        Returns:
            Timeline JSON compatible with the existing FFmpeg compiler.
        """
        async with database.async_session_maker() as db:
            result = await db.execute(
                select(VideoTemplate)
                .options(selectinload(VideoTemplate.audio_asset))
                .where(VideoTemplate.id == template_id)
            )
            template = result.scalar_one_or_none()
            if template is None:
                raise ValueError(f"Template {template_id} not found")

            # Extract all data while session is still open to avoid
            # DetachedInstanceError on lazy-loaded JSON columns.
            slots: List[Dict[str, Any]] = template.media_slots or []
            beatmap: List[float] = template.beatmap or []
            effects: Dict[str, Any] = template.global_effects or {}
            # Capture scalar fields needed by _build_timeline
            template_snapshot = _TemplateSnapshot(
                id=template.id,
                name=template.name,
                audio_asset_id=template.audio_asset_id,
                audio_storage_key=template.audio_asset.storage_key if template.audio_asset else None,
            )

        # Assign best-matching media to each slot
        remaining = list(user_media_list)
        assignments: List[Dict[str, Any]] = []

        for slot in sorted(slots, key=lambda s: s.get("slot_index", 0)):
            best_media: Optional[Dict[str, Any]] = None
            best_score = -1.0
            for media in remaining:
                score = self._score_media_for_slot(media, slot)
                if score > best_score:
                    best_score = score
                    best_media = media
            if best_media is not None:
                assignments.append({"slot": slot, "media": best_media, "score": best_score})
                remaining.remove(best_media)
            else:
                assignments.append({"slot": slot, "media": None, "score": 0.0})

        # Build timeline JSON
        return self._build_timeline(template_snapshot, assignments, beatmap, effects)

    @staticmethod
    def _score_media_for_slot(media: Dict[str, Any], slot: Dict[str, Any]) -> float:
        """Score how well a media item fits a template slot.

        Scoring factors (mock):
          - Duration closeness (0-0.5 range)
          - Theme keyword match (0 or 0.5)
        """
        score = 0.0

        media_dur = media.get("duration") or 0.0
        slot_dur = slot.get("duration") or 0.0
        if slot_dur > 0:
            ratio = min(media_dur, slot_dur) / max(media_dur, slot_dur) if max(media_dur, slot_dur) > 0 else 0.0
            score += ratio * 0.5

        media_theme = (media.get("theme") or "").lower()
        slot_theme = (slot.get("target_theme") or "").lower()
        if media_theme and slot_theme and media_theme == slot_theme:
            score += 0.5

        return score

    @staticmethod
    def _build_timeline(
        template: _TemplateSnapshot,
        assignments: List[Dict[str, Any]],
        beatmap: List[float],
        effects: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Produce a timeline JSON from slot assignments."""
        clips: List[Dict[str, Any]] = []
        timeline_cursor = 0.0

        for assignment in assignments:
            slot = assignment["slot"]
            media = assignment["media"]
            slot_dur = slot.get("duration", 3.0)
            if media and media.get("duration"):
                slot_dur = min(float(slot_dur), float(media["duration"]))
            slot_dur = max(0.05, float(slot_dur))

            clip: Dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "type": "video",
                "source": {
                    "media_asset_id": media["media_asset_id"] if media else None,
                    "storage_key": media.get("storage_key") if media else None,
                },
                "source_start": 0.0,
                "source_end": slot_dur,
                "source_duration": slot_dur,
                "timeline_start": timeline_cursor,
                "timeline_end": timeline_cursor + slot_dur,
                "timeline_duration": slot_dur,
                "sequence_order": slot.get("slot_index", 0),
                "properties": {
                    "aspect_ratio": slot.get("aspect_ratio"),
                },
            }
            clips.append(clip)
            timeline_cursor += slot_dur

        tracks = [{"type": "video", "track_index": 0, "clips": clips}]

        # Attach audio track if template has an audio asset
        if template.audio_asset_id and template.audio_storage_key:
            tracks.append({
                "type": "audio",
                "track_index": 1,
                "clips": [{
                    "id": str(uuid.uuid4()),
                    "type": "audio",
                     "source": {
                         "media_asset_id": str(template.audio_asset_id),
                         "storage_key": template.audio_storage_key,
                     },
                     "source_start": 0.0,
                     "source_end": timeline_cursor,
                     "source_duration": timeline_cursor,
                     "timeline_start": 0.0,
                     "timeline_duration": timeline_cursor,
                     "timeline_end": timeline_cursor,
                     "sequence_order": 0,
                     "properties": {"role": "background_music"},
                 }],
            })

        return {
            "version": 1,
            "schema": TIMELINE_SCHEMA,
            "template_id": str(template.id),
            "template_name": template.name,
            "duration": timeline_cursor,
            "total_duration": timeline_cursor,
            "tracks": tracks,
            "beatmap": beatmap,
            "global_effects": effects,
        }



def get_template_engine(): return TemplateEngine()

