"""Deterministic quality checks for AI-generated timelines."""

from __future__ import annotations

from typing import Any, Mapping

from app.core.timeline import normalize_timeline, validate_timeline


class AIEvaluator:
    """Evaluate structural edit quality without inventing model scores."""

    def evaluate_timeline(self, timeline_json: Mapping[str, Any] | None) -> dict[str, Any]:
        timeline = normalize_timeline(timeline_json)
        errors = validate_timeline(timeline)
        clips = [clip for track in timeline["tracks"] for clip in track.get("clips", [])]
        duration = float(timeline.get("total_duration", 0.0) or 0.0)
        covered = sum(float(clip.get("timeline_duration", 0.0) or 0.0) for clip in clips)
        return {
            "valid": not errors,
            "errors": errors,
            "clip_count": len(clips),
            "duration": duration,
            "covered_duration": covered,
            "coverage_ratio": round(covered / duration, 4) if duration else 0.0,
        }


def get_ai_evaluator() -> AIEvaluator:
    return AIEvaluator()
