"""Deep Computer Vision Analyzer for AI Video Director.

Provides frame-accurate visual analysis:
- Face & Speaker Detection (Deep Neural Network YuNet)
- A-Roll (Talking Head) vs B-Roll (Scene/Cutaway) classification
- Smart Auto-Reframe (Optimal crop center around detected speaker faces)
- Aesthetic Quality Assessment (Laplacian Sharpness, Exposure/Luminance)
- Motion & Pacing Quantification
"""

import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

import cv2
import numpy as np


@dataclass
class FaceBBox:
    x: int
    y: int
    w: int
    h: int
    center_x: float  # Normalized 0.0 to 1.0
    center_y: float  # Normalized 0.0 to 1.0
    confidence: float


@dataclass
class ShotVisualData:
    shot_idx: int
    start_time: float
    end_time: float
    duration: float
    shot_type: str  # "A-ROLL" or "B-ROLL"
    faces_detected: int
    dominant_face: Optional[FaceBBox] = None
    smart_crop_center_x: float = 0.5  # Normalized horizontal crop center (0.0 - 1.0)
    sharpness_score: float = 0.0
    sharpness_label: str = "normal"  # "crisp", "normal", "blurry"
    brightness_score: float = 128.0
    brightness_label: str = "good"  # "good", "dark", "overexposed"
    motion_energy: str = "medium"  # "static", "low", "medium", "high"


@dataclass
class VisualAnalysisResult:
    video_path: str
    width: int
    height: int
    fps: float
    duration: float
    total_frames: int
    shots: List[ShotVisualData] = field(default_factory=list)
    a_roll_count: int = 0
    b_roll_count: int = 0
    overall_quality: str = "high"
    avg_sharpness: float = 0.0
    recommended_reframe_center: float = 0.5
    ai_vision_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


class VisualAnalyzer:
    """Production-grade Computer Vision Analyzer for video content understanding."""

    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            default_path = Path(__file__).parent / "models" / "face_detection_yunet_2023mar.onnx"
            self.model_path = str(default_path)
        else:
            self.model_path = model_path

        self._detector: Optional[Any] = None
        self._init_detector()

    def _init_detector(self) -> None:
        """Initialize YuNet face detector if ONNX weights exist."""
        if os.path.exists(self.model_path):
            try:
                # Initialize with a dummy dimension; setInputSize is called per video
                self._detector = cv2.FaceDetectorYN_create(
                    self.model_path,
                    "",
                    (320, 320),
                    score_threshold=0.6,
                    nms_threshold=0.3,
                    top_k=5000,
                )
            except Exception:
                self._detector = None

    def analyze_video_sync(
        self,
        video_path: str,
        scene_cuts: Optional[List[float]] = None,
        max_samples_per_shot: int = 2,
    ) -> VisualAnalysisResult:
        """Synchronously analyze video frames across shot boundaries."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"OpenCV could not open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
        duration = total_frames / fps if fps > 0 else 0.0

        # Build shot time intervals
        intervals: List[tuple[float, float]] = []
        if scene_cuts and len(scene_cuts) > 0:
            clean_cuts = sorted(list(set([0.0] + [c for c in scene_cuts if c < duration] + [duration])))
            for i in range(len(clean_cuts) - 1):
                s, e = clean_cuts[i], clean_cuts[i + 1]
                if e - s >= 0.3:  # Only consider shots >= 0.3 seconds
                    intervals.append((s, e))
        
        # Fallback if no cuts or single cut: divide into 4-5 second chunks for sampling
        if not intervals:
            chunk = 4.0
            cur = 0.0
            while cur < duration:
                end = min(cur + chunk, duration)
                intervals.append((cur, end))
                cur = end

        # Configure detector input size
        if self._detector:
            try:
                self._detector.setInputSize((width, height))
            except Exception:
                pass

        shot_results: List[ShotVisualData] = []
        sharpness_list: List[float] = []

        for idx, (start_t, end_t) in enumerate(intervals):
            shot_dur = end_t - start_t
            sample_times = [
                start_t + min(0.2, shot_dur * 0.1),
                start_t + shot_dur * 0.5,
            ] if max_samples_per_shot >= 2 and shot_dur > 0.8 else [start_t + shot_dur * 0.5]

            faces_in_shot: List[FaceBBox] = []
            shot_sharpness: List[float] = []
            shot_brightness: List[float] = []
            prev_gray = None
            motion_diffs: List[float] = []

            for st in sample_times:
                f_idx = int(st * fps)
                if f_idx >= total_frames:
                    continue
                cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # 1. Sharpness via Laplacian variance
                lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                shot_sharpness.append(lap_var)
                sharpness_list.append(lap_var)

                # 2. Exposure & Brightness
                br = float(np.mean(gray))
                shot_brightness.append(br)

                # 3. Motion difference
                if prev_gray is not None:
                    diff = float(np.mean(cv2.absdiff(gray, prev_gray)))
                    motion_diffs.append(diff)
                prev_gray = gray

                # 4. Face Detection (YuNet)
                if self._detector:
                    try:
                        _, detections = self._detector.detect(frame)
                        if detections is not None:
                            for det in detections:
                                fx, fy, fw, fh = [int(v) for v in det[:4]]
                                conf = float(det[-1]) if len(det) > 4 else 0.85
                                # Filter tiny false positives (must be > 2% of frame height)
                                if fh >= height * 0.02 and fw >= width * 0.02:
                                    cx = (fx + fw / 2.0) / width
                                    cy = (fy + fh / 2.0) / height
                                    faces_in_shot.append(FaceBBox(
                                        x=fx, y=fy, w=fw, h=fh,
                                        center_x=round(cx, 3),
                                        center_y=round(cy, 3),
                                        confidence=round(conf, 2),
                                    ))
                    except Exception:
                        pass

            # Aggregate shot metrics
            avg_sharp = np.mean(shot_sharpness) if shot_sharpness else 100.0
            sharp_lbl = "crisp" if avg_sharp > 200 else ("normal" if avg_sharp > 50 else "blurry")

            avg_bright = np.mean(shot_brightness) if shot_brightness else 128.0
            bright_lbl = "dark" if avg_bright < 50 else ("overexposed" if avg_bright > 210 else "good")

            avg_diff = np.mean(motion_diffs) if motion_diffs else 10.0
            motion_lbl = "high" if avg_diff > 35 else ("medium" if avg_diff > 15 else ("low" if avg_diff > 5 else "static"))

            # Determine dominant face and smart crop center
            dominant_face = None
            smart_crop_x = 0.5
            if faces_in_shot:
                # Pick face with largest area (w * h)
                dominant_face = max(faces_in_shot, key=lambda f: f.w * f.h)
                smart_crop_x = dominant_face.center_x
                shot_type = "A-ROLL"
            else:
                shot_type = "B-ROLL"

            shot_results.append(ShotVisualData(
                shot_idx=idx,
                start_time=round(start_t, 2),
                end_time=round(end_t, 2),
                duration=round(shot_dur, 2),
                shot_type=shot_type,
                faces_detected=len(faces_in_shot),
                dominant_face=dominant_face,
                smart_crop_center_x=round(smart_crop_x, 3),
                sharpness_score=round(float(avg_sharp), 1),
                sharpness_label=sharp_lbl,
                brightness_score=round(float(avg_bright), 1),
                brightness_label=bright_lbl,
                motion_energy=motion_lbl,
            ))

        cap.release()

        # Video-level summary
        a_roll = sum(1 for s in shot_results if s.shot_type == "A-ROLL")
        b_roll = sum(1 for s in shot_results if s.shot_type == "B-ROLL")
        overall_sharp = float(np.mean(sharpness_list)) if sharpness_list else 100.0
        overall_qual = "high" if overall_sharp > 200 else ("medium" if overall_sharp > 50 else "poor")

        # Global recommended reframe center (median of A-roll face centers, or 0.5)
        a_roll_centers = [s.smart_crop_center_x for s in shot_results if s.shot_type == "A-ROLL"]
        rec_crop = float(np.median(a_roll_centers)) if a_roll_centers else 0.5

        # Human-readable AI summary
        summary = (
            f"Visual scan complete: {len(shot_results)} shots analyzed ({a_roll} A-Roll talking head, "
            f"{b_roll} B-Roll cutaway scenes). Visual quality is {overall_qual} with average sharpness {overall_sharp:.1f}. "
            f"Smart 9:16 reframe focal center is at {rec_crop*100:.1f}% width."
        )

        return VisualAnalysisResult(
            video_path=video_path,
            width=width,
            height=height,
            fps=round(fps, 2),
            duration=round(duration, 2),
            total_frames=total_frames,
            shots=shot_results,
            a_roll_count=a_roll,
            b_roll_count=b_roll,
            overall_quality=overall_qual,
            avg_sharpness=round(overall_sharp, 1),
            recommended_reframe_center=round(rec_crop, 3),
            ai_vision_summary=summary,
        )

    async def analyze_video(
        self,
        video_path: str,
        scene_cuts: Optional[List[float]] = None,
        max_samples_per_shot: int = 2,
    ) -> VisualAnalysisResult:
        """Asynchronously analyze video offloading CPU work to threadpool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self.analyze_video_sync,
            video_path,
            scene_cuts,
            max_samples_per_shot,
        )


_global_visual_analyzer: Optional[VisualAnalyzer] = None


def get_visual_analyzer() -> VisualAnalyzer:
    """Singleton getter for VisualAnalyzer."""
    global _global_visual_analyzer
    if _global_visual_analyzer is None:
        _global_visual_analyzer = VisualAnalyzer()
    return _global_visual_analyzer
