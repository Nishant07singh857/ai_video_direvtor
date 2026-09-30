import asyncio
from typing import Optional, List
from dataclasses import dataclass

import os
from video_engine.ingestion.processor import MediaProcessor


@dataclass
class ShotBoundary:
    """Represents a detected shot boundary."""
    start_time: float
    end_time: float
    duration: float
    shot_index: int
    confidence: Optional[float] = None
    detection_method: str = "histogram_diff"


class ShotDetector:
    """Deterministic shot boundary detection using FFmpeg.
    
    Uses FFmpeg's select filter with scene detection to find shot boundaries.
    This is a deterministic, computer-vision based approach that doesn't
    require any LLM or ML model.
    
    The method samples frames and computes visual differences using
    histogram comparison (or other scene change detection methods).
    """
    
    def __init__(
        self,
        threshold: float = 0.3,
        min_shot_duration: float = 0.5,
        frame_sampling: int = 1,
    ):
        """
        Args:
            threshold: Scene change detection threshold (0.0-1.0).
                       Lower = more sensitive, more shots detected.
            min_shot_duration: Minimum shot duration in seconds to avoid
                              detecting noise as shots.
            frame_sampling: Sample every N frames for analysis (1 = every frame).
                           Higher = faster but less precise.
        """
        self.threshold = threshold
        self.min_shot_duration = min_shot_duration
        self.frame_sampling = frame_sampling
        try:
            from app.core.config import settings
            configured_ffmpeg = settings.FFMPEG_PATH
        except Exception:
            configured_ffmpeg = None
        self.ffmpeg_path = configured_ffmpeg or os.getenv("FFMPEG_PATH", "ffmpeg") or "ffmpeg"
    
    async def detect_shots(self, video_path: str) -> List[ShotBoundary]:
        """Detect shot boundaries in a video file using FFmpeg's scene detection.
        
        Uses FFmpeg's `select` filter with `gt(scene,threshold)` to detect
        scene changes. This is a fast, deterministic approach that works
        without decoding every frame into memory.
        
        Returns:
            List of ShotBoundary objects with start/end times and metadata.
        """
        # Use FFmpeg to detect scene changes
        # The select filter with 'gt(scene,THRESHOLD)' outputs frames where
        # the scene change score exceeds the threshold
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video_path,
            "-vf", f"select=gt(scene\\,{self.threshold}),showinfo",
            "-f", "null",
            "-"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg shot detection failed: {stderr.decode()}")
        
        # Parse FFmpeg showinfo output to get shot boundaries
        boundaries = self._parse_shot_boundaries(
            stderr.decode(), 
            video_path
        )
        
        return boundaries
    
    def _parse_shot_boundaries(
        self, 
        ffmpeg_output: str,
        video_path: str
    ) -> List[ShotBoundary]:
        """Parse FFmpeg showinfo output to extract shot boundaries.
        
        FFmpeg showinfo output looks like:
        [Parsed_showinfo_1 @ 0x...] n:0 pts:0 pts_time:0 pos:0 ...
        [Parsed_showinfo_1 @ 0x...] n:1 pts:3000 pts_time:0.1 ...
        
        We need to get the timestamps of frames where scene changes occurred.
        """
        import re
        
        # Get video duration first
        from video_engine.ingestion.processor import MediaProcessor
        processor = MediaProcessor()
        metadata = processor.extract_metadata_sync(video_path)
        total_duration = metadata.duration or 0
        
        # Parse timestamps from showinfo output
        # Pattern: n:<frame_num> pts:<pts> pts_time:<seconds>
        time_pattern = r'pts_time:([\d.]+)'
        times = re.findall(time_pattern, ffmpeg_output)
        
        # Convert to float timestamps
        shot_times = [float(t) for t in times]
        shot_times = sorted(set(shot_times))  # Deduplicate and sort
        
        # Filter by minimum shot duration
        filtered_times = []
        for t in shot_times:
            if not filtered_times or (t - filtered_times[-1]) >= self.min_shot_duration:
                filtered_times.append(t)
        
        # Build shot boundaries
        boundaries = []
        prev_time = 0.0
        
        for i, shot_time in enumerate(filtered_times):
            if shot_time - prev_time >= self.min_shot_duration:
                boundaries.append(ShotBoundary(
                    start_time=prev_time,
                    end_time=shot_time,
                    duration=shot_time - prev_time,
                    shot_index=len(boundaries),
                    detection_method=f"histogram_diff_threshold_{self.threshold}",
                ))
                prev_time = shot_time
        
        # Add final shot if there's remaining duration
        if total_duration > prev_time + self.min_shot_duration:
            boundaries.append(ShotBoundary(
                start_time=prev_time,
                end_time=total_duration,
                duration=total_duration - prev_time,
                shot_index=len(boundaries),
                detection_method=f"histogram_diff_threshold_{self.threshold}",
            ))
        elif not boundaries and total_duration > 0:
            # No shots detected, single shot for entire video
            boundaries.append(ShotBoundary(
                start_time=0.0,
                end_time=total_duration,
                duration=total_duration,
                shot_index=0,
                detection_method="single_shot_fallback",
            ))
        
        return boundaries


class ShotDetectorOpenCV:
    """Alternative shot detector using OpenCV for frame-by-frame analysis.
    
    This is more precise but slower than the FFmpeg-based detector.
    Use when you need frame-accurate boundaries or custom visual features.
    """
    
    def __init__(
        self,
        threshold: float = 0.3,
        min_shot_duration: float = 0.5,
        frame_sampling: int = 1,
        method: str = "histogram",  # "histogram", "edge", "pixel"
    ):
        self.threshold = threshold
        self.min_shot_duration = min_shot_duration
        self.frame_sampling = frame_sampling
        self.method = method
    
    async def detect_shots(self, video_path: str) -> List[ShotBoundary]:
        """Detect shots using OpenCV frame-by-frame analysis."""
        try:
            import cv2
        except ImportError:
            raise RuntimeError("OpenCV not installed. Install opencv-python.")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        boundaries = []
        prev_hist = None
        frame_idx = 0
        shot_start_frame = 0
        shot_index = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % self.frame_sampling != 0:
                frame_idx += 1
                continue
            
            # Compute histogram or other features
            if self.method == "histogram":
                hist = cv2.calcHist([frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                hist = cv2.normalize(hist, hist).flatten()
            elif self.method == "edge":
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 100, 200)
                hist = cv2.calcHist([edges], [0], None, [256], [0, 256])
                hist = cv2.normalize(hist, hist).flatten()
            else:  # pixel difference
                hist = frame.flatten().astype(float)
            
            if prev_hist is not None:
                # Compute similarity
                if self.method == "pixel":
                    diff = cv2.absdiff(frame, prev_frame)
                    mean_diff = diff.mean() / 255.0
                else:
                    correlation = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                    mean_diff = 1.0 - correlation
                
                if mean_diff > self.threshold:
                    # Shot boundary detected
                    start_time = shot_start_frame / fps
                    end_time = frame_idx / fps
                    
                    if end_time - start_time >= self.min_shot_duration:
                        boundaries.append(ShotBoundary(
                            start_time=start_time,
                            end_time=end_time,
                            duration=end_time - start_time,
                            shot_index=shot_index,
                            confidence=1.0 - mean_diff,
                            detection_method=f"opencv_{self.method}_threshold_{self.threshold}",
                        ))
                        shot_index += 1
                        shot_start_frame = frame_idx
            
            prev_hist = hist
            prev_frame = frame.copy() if self.method == "pixel" else None
            frame_idx += 1
        
        # Add final shot
        cap.release()
        
        if duration > shot_start_frame / fps + 0.5:
            boundaries.append(ShotBoundary(
                start_time=shot_start_frame / fps,
                end_time=duration,
                duration=duration - shot_start_frame / fps,
                shot_index=shot_index,
                detection_method=f"opencv_{self.method}_threshold_{self.threshold}",
            ))
        
        return boundaries


# Singleton instances
_shot_detector_ffmpeg: Optional[ShotDetector] = None
_shot_detector_opencv: Optional[ShotDetectorOpenCV] = None




def get_shot_detector(): return ShotDetectorService()

