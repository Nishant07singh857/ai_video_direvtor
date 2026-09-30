"""Source-grounding checks for AI-produced edits."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from app.core.timeline import normalize_timeline, validate_timeline


class GroundingViolationError(ValueError):
    """Raised when an EDL references invalid or unapproved source material."""


class SourceGroundingChecker:
    """Validate that generated clips remain tied to uploaded source assets."""

    def check(
        self,
        timeline_json: Mapping[str, Any] | None,
        allowed_storage_keys: Iterable[str] | None = None,
    ) -> list[str]:
        errors = validate_timeline(timeline_json)
        allowed = set(allowed_storage_keys or [])
        if allowed:
            timeline = normalize_timeline(timeline_json)
            for track in timeline["tracks"]:
                for clip in track.get("clips", []):
                    key = clip.get("source", {}).get("storage_key")
                    if key and key not in allowed:
                        errors.append(f"clip {clip.get('id')} references unapproved source: {key}")
        return errors

    def enforce(
        self,
        timeline_json: Mapping[str, Any] | None,
        allowed_storage_keys: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        errors = self.check(timeline_json, allowed_storage_keys)
        if errors:
            raise GroundingViolationError("; ".join(errors))
        return normalize_timeline(timeline_json)


def get_source_grounding_checker() -> SourceGroundingChecker:
    return SourceGroundingChecker()
