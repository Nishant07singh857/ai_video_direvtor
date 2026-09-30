"""Canonical timeline contract shared by AI, editing and rendering.

The application historically accepted two shapes: a legacy top-level
``clips`` array and the renderer-ready ``tracks[].clips[]`` shape.  Keeping
the compatibility conversion in one small, deterministic module prevents the
UI, render workers and AI pipeline from silently disagreeing about a timeline.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping


TIMELINE_SCHEMA = "ai-video-director-timeline-v1"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if result >= 0 else default


def _normalise_clip(raw: Mapping[str, Any], cursor: float, track_type: str) -> dict[str, Any]:
    clip = deepcopy(dict(raw))
    source = deepcopy(clip.get("source") or {})

    storage_key = source.get("storage_key") or clip.get("storage_key")
    media_asset_id = source.get("media_asset_id") or clip.get("media_asset_id")
    if storage_key is not None:
        source["storage_key"] = storage_key
    if media_asset_id is not None:
        source["media_asset_id"] = str(media_asset_id)

    start = _number(
        clip.get("timeline_start", clip.get("start", clip.get("start_time", cursor))),
        cursor,
    )
    raw_duration = clip.get("timeline_duration", clip.get("duration"))
    if raw_duration is None:
        raw_end = _number(clip.get("end", start), start)
        raw_start = _number(clip.get("start", start), start)
        raw_duration = raw_end - raw_start
    duration = _number(raw_duration, 0.0)
    if duration <= 0:
        source_start = _number(clip.get("source_start", 0.0))
        source_end = _number(clip.get("source_end", source_start))
        duration = max(0.0, source_end - source_start)
    if duration <= 0:
        duration = 0.001

    source_start = _number(clip.get("source_start", 0.0))
    source_end = _number(clip.get("source_end", source_start + duration))
    if source_end <= source_start:
        source_end = source_start + duration

    clip["id"] = str(clip.get("id") or f"clip-{int(start * 1000)}")
    clip["type"] = clip.get("type") or track_type
    clip["source"] = source
    clip["source_start"] = source_start
    clip["source_end"] = source_end
    clip["source_duration"] = max(source_end - source_start, duration)
    clip["timeline_start"] = start
    clip["timeline_duration"] = duration
    clip["timeline_end"] = start + duration
    clip["sequence_order"] = int(clip.get("sequence_order", 0) or 0)
    clip["properties"] = deepcopy(clip.get("properties") or {})
    return clip


def normalize_timeline(timeline_json: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a renderer-ready copy of a timeline.

    This function is intentionally tolerant when reading old project data,
    but always emits the canonical schema.  It never invents source media: a
    clip without a storage key remains visible to the editor and is rejected
    by the render resolver instead of being replaced with fake footage.
    """

    data = deepcopy(dict(timeline_json or {}))
    raw_tracks = data.get("tracks")
    tracks: list[dict[str, Any]] = []

    if isinstance(raw_tracks, list) and raw_tracks:
        for track_index, raw_track in enumerate(raw_tracks):
            if not isinstance(raw_track, Mapping):
                continue
            track_type = str(raw_track.get("type") or "video")
            raw_clips = raw_track.get("clips") or []
            cursor = 0.0
            clips: list[dict[str, Any]] = []
            if isinstance(raw_clips, list):
                for raw_clip in raw_clips:
                    if not isinstance(raw_clip, Mapping):
                        continue
                    clip = _normalise_clip(raw_clip, cursor, track_type)
                    clips.append(clip)
                    cursor = max(cursor, clip["timeline_end"])
            track = deepcopy(dict(raw_track))
            track["id"] = str(track.get("id") or f"{track_type}-{track_index + 1}")
            track["type"] = track_type
            track["track_index"] = int(track.get("track_index", track_index) or track_index)
            track["clips"] = clips
            tracks.append(track)
    else:
        legacy_clips = data.get("clips") or []
        clips: list[dict[str, Any]] = []
        cursor = 0.0
        if isinstance(legacy_clips, list):
            for raw_clip in legacy_clips:
                if not isinstance(raw_clip, Mapping):
                    continue
                clip = _normalise_clip(raw_clip, cursor, "video")
                clips.append(clip)
                cursor = max(cursor, clip["timeline_end"])
        tracks.append({"id": "video-1", "type": "video", "track_index": 0, "clips": clips})

    data["tracks"] = tracks
    data.pop("clips", None)
    data["version"] = int(data.get("version", 1) or 1)
    data["schema"] = TIMELINE_SCHEMA
    total_duration = max(
        [
            clip["timeline_end"]
            for track in tracks
            for clip in track.get("clips", [])
            if isinstance(clip, Mapping)
        ]
        + [_number(data.get("total_duration", data.get("duration", 0.0)))]
    )
    data["duration"] = total_duration
    data["total_duration"] = total_duration
    return data


def iter_timeline_clips(timeline_json: Mapping[str, Any] | None) -> Iterable[tuple[dict[str, Any], dict[str, Any]]]:
    """Yield ``(track, clip)`` pairs from any supported timeline shape."""

    timeline = normalize_timeline(timeline_json)
    for track in timeline.get("tracks", []):
        for clip in track.get("clips", []):
            yield track, clip


def validate_timeline(timeline_json: Mapping[str, Any] | None) -> list[str]:
    """Validate structural and source-grounding constraints before render."""

    errors: list[str] = []
    timeline = normalize_timeline(timeline_json)
    seen_ids: set[str] = set()
    for track, clip in iter_timeline_clips(timeline):
        clip_id = str(clip.get("id"))
        if clip_id in seen_ids:
            errors.append(f"duplicate clip id: {clip_id}")
        seen_ids.add(clip_id)
        if clip["timeline_end"] <= clip["timeline_start"]:
            errors.append(f"clip {clip_id} has non-positive timeline duration")
        if clip["source_end"] <= clip["source_start"]:
            errors.append(f"clip {clip_id} has invalid source range")
        if track.get("type") in {"video", "audio"} and not clip.get("source", {}).get("storage_key"):
            errors.append(f"clip {clip_id} has no source storage key")
    return errors
