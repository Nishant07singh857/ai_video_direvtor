import logging
from typing import Dict, List, Optional

from app.models.analysis import TranscriptSegment
from app.models.editing import EditOperationType
from app.services.nlp_editor import StructuredEditOperation

logger = logging.getLogger(__name__)

FILLER_WORDS = {"um", "uh", "ah", "like", "you know", "so", "actually", "basically"}

class TranscriptEditorService:
    """Service to handle text-based editing operations."""
    
    def generate_delete_operations(
        self,
        deleted_segments: List[Dict[str, float]],
        target_item_id: Optional[str] = None
    ) -> List[StructuredEditOperation]:
        """
        Generate EDL structures (StructuredEditOperation) to delete specific sections.
        deleted_segments is a list of dictionaries with 'start_time' and 'end_time'.
        """
        operations = []
        
        if not deleted_segments:
            return operations
            
        # Sort segments by start_time to process them in order
        sorted_segments = sorted(deleted_segments, key=lambda x: x["start_time"])
        
        # Merge overlapping or touching segments
        merged_segments = [dict(sorted_segments[0])]
        
        for current in sorted_segments[1:]:
            previous = merged_segments[-1]
            if current["start_time"] <= previous["end_time"]:
                previous["end_time"] = max(previous["end_time"], current["end_time"])
            else:
                merged_segments.append(dict(current))
                
        # Generate DELETE operations
        for seg in merged_segments:
            op = StructuredEditOperation(
                target_item_id=target_item_id,
                operation_type=EditOperationType.DELETE,
                parameters={
                    "start_time": seg["start_time"],
                    "end_time": seg["end_time"]
                }
            )
            operations.append(op)
            
        return operations


_transcript_editor_service: Optional[TranscriptEditorService] = None


def get_transcript_editor_service() -> TranscriptEditorService:
    global _transcript_editor_service
    if _transcript_editor_service is None:
        _transcript_editor_service = TranscriptEditorService()
    return _transcript_editor_service

        
