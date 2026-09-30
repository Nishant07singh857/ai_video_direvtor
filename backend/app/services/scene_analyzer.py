from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class SceneBoundary:
    """Represents a scene boundary."""
    start_time: float
    end_time: float
    duration: float
    scene_index: int
    label: Optional[str] = None
    description: Optional[str] = None
    confidence: Optional[float] = None
    detection_method: str = "temporal_grouping"


class SceneAnalyzer(ABC):
    """Abstract base class for scene analysis.
    
    Scene analysis is different from shot detection:
    - Shots are individual camera takes (visual continuity)
    - Scenes are semantic units (same location, characters, time)
    
    This interface defines the contract for scene analysis.
    Current implementation provides a deterministic baseline.
    Future implementations can use vision-language models for
    semantic scene understanding.
    """
    
    @abstractmethod
    async def analyze(
        self,
        video_path: str,
        shot_boundaries: List[Dict[str, Any]],
        media_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SceneBoundary]:
        """Analyze video and group shots into scenes.
        
        Args:
            video_path: Path to the video file
            shot_boundaries: List of detected shot boundaries with
                           start_time, end_time, duration, shot_index
            media_metadata: Optional metadata about the media
            
        Returns:
            List of SceneBoundary objects
        """
        ...
    
    @property
    @abstractmethod
    def analyzer_name(self) -> str:
        """Human-readable name of the analyzer."""
        ...
    
    @property
    @abstractmethod
    def supports_semantic_labels(self) -> bool:
        """Whether this analyzer provides semantic scene labels."""
        ...


@dataclass
class TemporalSceneGroupingConfig:
    """Configuration for temporal scene grouping."""
    max_gap: float = 2.0           # Max gap between shots to group (seconds)
    min_scene_duration: float = 3.0  # Minimum scene duration
    max_scene_duration: float = 60.0  # Maximum scene duration before forced split
    similarity_threshold: float = 0.3  # Visual similarity threshold (future use)


class TemporalSceneAnalyzer(SceneAnalyzer):
    """Deterministic scene analyzer based on temporal grouping.
    
    Groups consecutive shots into scenes based on temporal proximity.
    This is a baseline implementation that doesn't require any
    visual-language model. It groups shots that are close in time,
    assuming they belong to the same scene.
    
    Limitations:
    - Does not provide semantic labels
    - Cannot detect scene changes without visual discontinuity
    - Purely temporal grouping
    
    Future: Replace with vision-language model for semantic scene understanding.
    """
    
    def __init__(self, config: Optional[TemporalSceneGroupingConfig] = None):
        self.config = config or TemporalSceneGroupingConfig()
        self._analyzer_name = "TemporalSceneAnalyzer (baseline)"
        self._supports_semantic_labels = False
    
    @property
    def analyzer_name(self) -> str:
        return self._analyzer_name
    
    @property
    def supports_semantic_labels(self) -> bool:
        return self._supports_semantic_labels
    
    async def analyze(
        self,
        video_path: str,
        shot_boundaries: List[Dict[str, Any]],
        media_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Group shots into scenes based on temporal proximity.
        
        Groups consecutive shots that are close in time (gap < max_gap)
        into the same scene. Splits when gap exceeds threshold or
        scene would exceed max_scene_duration.
        """
        if not shot_boundaries:
            return []
        
        scenes = []
        current_scene_shots = []
        scene_start = None
        scene_index = 0
        
        for i, shot in enumerate(shot_boundaries):
            if not current_scene_shots:
                # Start new scene
                current_scene_shots = [shot]
                scene_start = shot["start_time"]
            else:
                # Check if we should continue the scene or start a new one
                prev_shot = current_scene_shots[-1]
                gap = shot["start_time"] - prev_shot["end_time"]
                scene_duration = shot["end_time"] - scene_start
                
                should_split = (
                    gap > self.config.max_gap or
                    scene_duration > self.config.max_scene_duration
                )
                
                if should_split:
                    # Finalize current scene
                    scenes.append({
                        "start_time": scene_start,
                        "end_time": prev_shot["end_time"],
                        "duration": prev_shot["end_time"] - scene_start,
                        "scene_index": scene_index,
                        "label": None,
                        "description": None,
                        "confidence": 0.5,  # Low confidence for temporal-only
                        "detection_method": "temporal_grouping",
                        "shot_indices": [s["shot_index"] for s in current_scene_shots],
                    })
                    scene_index += 1
                    
                    # Start new scene
                    current_scene_shots = [shot]
                    scene_start = shot["start_time"]
                else:
                    # Continue current scene
                    current_scene_shots.append(shot)
        
        # Don't forget the last scene
        if current_scene_shots and scene_start is not None:
            last_shot = current_scene_shots[-1]
            scenes.append({
                "start_time": scene_start,
                "end_time": last_shot["end_time"],
                "duration": last_shot["end_time"] - scene_start,
                "scene_index": scene_index,
                "label": None,
                "description": None,
                "confidence": 0.5,
                "detection_method": "temporal_grouping",
                "shot_indices": [s["shot_index"] for s in current_scene_shots],
            })
        
        # Filter out scenes that are too short
        scenes = [s for s in scenes if s["duration"] >= self.config.min_scene_duration]
        
        return scenes
    
    @property
    def analyzer_name(self) -> str:
        return self._analyzer_name
    
    @property
    def supports_semantic_labels(self) -> bool:
        return self._supports_semantic_labels


# Vision-Language Model Scene Analyzer Interface
class VisionLanguageSceneAnalyzer(SceneAnalyzer):
    """Interface for future vision-language model scene analyzer.
    
    This class defines the interface for a semantic scene analyzer
    that uses vision-language models (e.g., GPT-4V, LLaVA, CLIP).
    Currently a placeholder - actual implementation requires model integration.
    """
    
    def __init__(self, model_name: str = "vision-language-model"):
        self._analyzer_name = f"VisionLanguageSceneAnalyzer ({model_name})"
        self._supports_semantic_labels = True
        self._model_available = False
    
    @property
    def analyzer_name(self) -> str:
        return self._analyzer_name
    
    @property
    def supports_semantic_labels(self) -> bool:
        return self._supports_semantic_labels
    
    async def analyze(
        self,
        video_path: str,
        shot_boundaries: List[Dict[str, Any]],
        media_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Analyze scenes using vision-language model.
        
        Not implemented - requires model integration.
        """
        import asyncio
        cmd = [
            "ffprobe",
            "-show_frames",
            "-of", "compact=p=0",
            "-f", "lavfi",
            f"movie={video_path},select=gt(scene\\,0.3)"
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return [{"status": "analyzed", "output": stdout.decode("utf-8")}]
    
    @property
    def analyzer_name(self) -> str:
        return self._analyzer_name
    
    @property
    def supports_semantic_labels(self) -> bool:
        return self._supports_semantic_labels


# Factory function
_scene_analyzer: Optional[SceneAnalyzer] = None


def get_scene_analyzer() -> SceneAnalyzer:
    global _scene_analyzer
    if _scene_analyzer is None:
        _scene_analyzer = TemporalSceneAnalyzer()
    return _scene_analyzer
