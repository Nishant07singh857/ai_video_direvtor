import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from dataclasses import dataclass

@dataclass
class TimelineValidationResult:
    """Result of timeline validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class TimelineBuilder:
    """Generates renderer-ready timeline JSON from story sequences."""
    
    def __init__(self):
        pass
    
    def get_timeline_schema_version(self) -> int:
        """Return the current timeline schema version."""
        return 1
    
    def build_timeline_json(
        self,
        project_id: str,
        story_id: str,
        story_title: str,
        story_description: str,
        narrative_arc: dict,
        estimated_duration: float,
        confidence: float,
        story_shots: List[Any],
        video_shots: Dict[str, Any],
        media_assets: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build the renderer-ready timeline JSON."""
        tracks = []
        
        # Video track
        video_clips = []
        timeline_time = 0.0
        
        for i, ss in enumerate(story_shots):
            vs = video_shots.get(str(ss.video_shot_id))
            if not vs:
                continue
            
            # Get media asset for storage key and filename
            media_asset = media_assets.get(str(vs.media_asset_id))
            
            clip = {
                "id": str(ss.id),
                "type": "video",
                "source": {
                    "media_asset_id": str(vs.media_asset_id),
                    "shot_id": str(vs.id),
                    "storage_key": media_asset.storage_key if media_asset else None,
                    "original_filename": media_asset.original_filename if media_asset else None,
                },
                "source_start": ss.start_time,
                "source_end": ss.end_time,
                "source_duration": ss.end_time - ss.start_time,
                "timeline_start": timeline_time,
                "timeline_end": timeline_time + (ss.end_time - ss.start_time),
                "timeline_duration": ss.end_time - ss.start_time,
                "sequence_order": ss.sequence_order,
                "narrative_role": ss.role.value if hasattr(ss.role, 'value') else str(ss.role),
                "properties": {
                    "width": media_asset.width if media_asset else None,
                    "height": media_asset.height if media_asset else None,
                    "fps": media_asset.fps if media_asset else None,
                    "video_codec": media_asset.video_codec if media_asset else None,
                } if media_asset else {},
            }
            video_clips.append(clip)
            timeline_time += ss.end_time - ss.start_time
        
        if video_clips:
            tracks.append({
                "type": "video",
                "track_index": 0,
                "clips": video_clips,
            })
        
        # Audio track
        audio_clips = []
        audio_timeline_time = 0.0
        for ss in story_shots:
            vs = video_shots.get(str(ss.video_shot_id))
            if not vs:
                continue
            
            media_asset = media_assets.get(str(vs.media_asset_id))
            
            audio_clips.append({
                "id": f"{ss.id}_audio",
                "type": "audio",
                "source": {
                    "media_asset_id": str(vs.media_asset_id),
                    "shot_id": str(vs.id),
                    "storage_key": media_asset.storage_key if media_asset else None,
                    "original_filename": media_asset.original_filename if media_asset else None,
                },
                "source_start": ss.start_time,
                "source_end": ss.end_time,
                "timeline_start": audio_timeline_time,
                "timeline_end": audio_timeline_time + (ss.end_time - ss.start_time),
                "sequence_order": ss.sequence_order + 1000,
            })
            audio_timeline_time += ss.end_time - ss.start_time
        
        if audio_clips:
            tracks.append({
                "type": "audio",
                "track_index": 1,
                "clips": audio_clips,
            })
        
        return {
            "version": self.get_timeline_schema_version(),
            "schema": "ai-video-director-timeline-v1",
            "project_id": str(project_id),
            "story_id": str(story_id),
            "title": story_title,
            "description": story_description,
            "duration": timeline_time,
            "total_duration": timeline_time,
            "tracks": tracks,
            "metadata": {
                "structure": narrative_arc.get("structure", "unknown") if narrative_arc else "unknown",
                "themes": narrative_arc.get("themes", []) if narrative_arc else [],
                "tone": narrative_arc.get("tone", "neutral") if narrative_arc else "neutral",
                "estimated_duration": estimated_duration,
                "confidence": confidence,
                "generated_at": datetime.now(UTC).isoformat(),
            },
        }
    
    def validate_timeline(
        self,
        timeline_json: Dict[str, Any],
        video_shots: Dict[str, Any],
    ) -> TimelineValidationResult:
        """Validate generated timeline for consistency and correctness."""
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ["version", "schema", "project_id", "duration", "tracks"]
        for field in required_fields:
            if field not in timeline_json:
                errors.append(f"Missing required field: {field}")
        
        # Validate tracks
        if "tracks" in timeline_json:
            video_track_found = False
            for track_idx, track in enumerate(timeline_json["tracks"]):
                if track.get("type") == "video":
                    video_track_found = True
                    track_errors = self._validate_video_track(track, track_idx, video_shots)
                    errors.extend(track_errors)
            
            if not video_track_found:
                warnings.append("No video track found in timeline")
        
        # Validate duration consistency
        if "duration" in timeline_json:
            declared_duration = timeline_json["duration"]
            max_timeline_end = 0.0
            for track in timeline_json.get("tracks", []):
                for clip in track.get("clips", []):
                    if "timeline_end" in clip:
                        max_timeline_end = max(max_timeline_end, clip["timeline_end"])
            
            if abs(declared_duration - max_timeline_end) > 0.1:
                errors.append(
                    f"Duration mismatch: declared {declared_duration}s, "
                    f"calculated from clips {max_timeline_end}s"
                )
        
        # Validate no negative timestamps
        for track in timeline_json.get("tracks", []):
            for clip in track.get("clips", []):
                for field in ["source_start", "source_end", "timeline_start", "timeline_end"]:
                    if field in clip and clip[field] < 0:
                        errors.append(f"Negative {field} in clip {clip.get('id')}: {clip[field]}")
                
                if "source_start" in clip and "source_end" in clip:
                    if clip["source_start"] >= clip["source_end"]:
                        errors.append(f"Invalid source range in clip {clip.get('id')}: "
                                    f"{clip['source_start']} >= {clip['source_end']}")
        
        # Check for duplicate sequence orders
        sequence_orders = []
        for track in timeline_json.get("tracks", []):
            for clip in track.get("clips", []):
                if "sequence_order" in clip:
                    sequence_orders.append(clip["sequence_order"])
        
        if len(sequence_orders) != len(set(sequence_orders)):
            errors.append("Duplicate sequence_order values found")
        
        return TimelineValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def _validate_video_track(
        self,
        track: Dict[str, Any],
        track_idx: int,
        video_shots: Dict[str, Any],
    ) -> List[str]:
        """Validate a video track."""
        errors = []
        
        clips = track.get("clips", [])
        if not clips:
            errors.append(f"Track {track_idx}: No clips in video track")
            return errors
        
        # Check clip references
        for clip in clips:
            source = clip.get("source", {})
            shot_id_str = source.get("shot_id")
            if shot_id_str:
                if shot_id_str not in video_shots:
                    errors.append(f"Clip {clip.get('id')}: Referenced shot {shot_id_str} not found")
            
            # Validate timing
            if "source_start" in clip and "source_end" in clip:
                if clip["source_start"] >= clip["source_end"]:
                    errors.append(f"Clip {clip.get('id')}: source_start >= source_end")
            
            if "timeline_start" in clip and "timeline_end" in clip:
                if clip["timeline_start"] >= clip["timeline_end"]:
                    errors.append(f"Clip {clip.get('id')}: timeline_start >= timeline_end")
        
        return errors
