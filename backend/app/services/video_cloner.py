"""Video style cloner service for Phase 52 - clone editing style from a reference video."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

from app.services.template_engine import TemplateEngine
from app.core import database
from app.core.config import settings
from video_engine.ingestion.processor import MediaProcessor


class VideoStyleCloner:
    """Analyzes a reference video and clones its editing style onto new media."""

    def __init__(self, template_engine: TemplateEngine | None = None) -> None:
        self._engine = template_engine or TemplateEngine()

    async def analyze_reference_video(self, video_path: str) -> Dict[str, Any]:
        """Analyze a reference video to extract comprehensive metadata.

        Returns:
            Dict containing scene_cuts, audio_lufs, color_style, estimated_pacing, etc.
        """
        import re
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Reference video not found: {video_path}")

        safe_path = str(path.absolute()).replace("\\", "/").replace(":", "\\:")
        ffprobe_path = settings.FFPROBE_PATH or "ffprobe"
        ffmpeg_path = settings.FFMPEG_PATH or "ffmpeg"
        
        scene_cuts = [0.0]
        try:
            cmd_cuts = [
                ffprobe_path,
                "-v", "quiet",
                "-show_frames",
                "-show_entries", "frame=pkt_pts_time",
                "-of", "json",
                "-f", "lavfi",
                f"movie={safe_path},select=gt(scene\\,0.3)"
            ]
            process_cuts = await asyncio.create_subprocess_exec(
                *cmd_cuts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_cuts, _ = await process_cuts.communicate()
            
            if process_cuts.returncode == 0 and stdout_cuts:
                data = json.loads(stdout_cuts.decode('utf-8'))
                for frame in data.get("frames", []):
                    pts_time = frame.get("pkt_pts_time")
                    if pts_time is not None:
                        scene_cuts.append(float(pts_time))
        except Exception:
            ...

        scene_cuts = sorted(list(set(scene_cuts)))
        
        estimated_pacing = "medium"
        if len(scene_cuts) > 10:
            estimated_pacing = "fast"
        elif len(scene_cuts) < 3:
            estimated_pacing = "slow"

        audio_lufs = -24.0
        try:
            cmd_audio = [
                ffmpeg_path,
                "-i", str(path.absolute()),
                "-af", "volumedetect",
                "-vn",
                "-sn",
                "-dn",
                "-f", "null",
                "-"
            ]
            process_audio = await asyncio.create_subprocess_exec(
                *cmd_audio,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr_audio = await process_audio.communicate()
            if stderr_audio:
                out_str = stderr_audio.decode('utf-8')
                match = re.search(r"mean_volume:\s*([-.\d]+)\s*dB", out_str)
                if match:
                    audio_lufs = float(match.group(1))
        except Exception:
            ...

        color_style = "neutral"
        try:
            cmd_color = [
                ffmpeg_path,
                "-i", str(path.absolute()),
                "-vf", "signalstats,metadata=print:file=-",
                "-f", "null",
                "-"
            ]
            process_color = await asyncio.create_subprocess_exec(
                *cmd_color,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_color, stderr_color = await process_color.communicate()
            out_str = (stdout_color.decode('utf-8') if stdout_color else "") + \
                      (stderr_color.decode('utf-8') if stderr_color else "")
            
            match = re.search(r"lavfi\.signalstats\.YAVG=([\d.]+)", out_str)
            if match:
                yavg = float(match.group(1))
                if yavg < 80:
                    color_style = "dark"
                elif yavg > 170:
                    color_style = "bright"
                else:
                    color_style = "neutral"
        except Exception:
            ...

        try:
            metadata = await MediaProcessor().extract_metadata(str(path.absolute()))
            duration = float(metadata.duration or 0.0)
        except Exception:
            duration = 0.0
        if duration > 0 and (not scene_cuts or scene_cuts[-1] < duration - 0.05):
            scene_cuts.append(duration)
        scene_cuts = sorted(list(set(scene_cuts)))

        return {
            "source_path": video_path,
            "scene_cuts": scene_cuts,
            "duration": duration,
            "audio_lufs": audio_lufs,
            "color_style": color_style,
            "estimated_pacing": estimated_pacing,
            "detected_cuts": scene_cuts,
            "detected_beats": [],
            "detected_effects": [],
        }

    @staticmethod
    def generate_template_from_reference(
        analysis_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Convert analysis output into a VideoTemplate-compatible dict.

        Args:
            analysis_result: Output of ``analyze_reference_video``.

        Returns:
            Dict matching VideoTemplate fields (beatmap, media_slots, global_effects).
        """
        cuts: List[float] = sorted(set(float(c) for c in analysis_result.get("detected_cuts", []) if c is not None))
        duration = float(analysis_result.get("duration", 0.0) or 0.0)
        if not cuts:
            cuts = [0.0, duration] if duration > 0 else [0.0]
        elif duration > cuts[-1]:
            cuts.append(duration)
        beats: List[float] = analysis_result.get("detected_beats", [])
        effects: List[Dict[str, Any]] = analysis_result.get("detected_effects", [])

        # Build media_slots from consecutive cut pairs
        media_slots: List[Dict[str, Any]] = []
        for idx in range(len(cuts) - 1):
            slot_duration = max(0.05, round(cuts[idx + 1] - cuts[idx], 3))
            media_slots.append({
                "slot_index": idx,
                "duration": slot_duration,
                "target_theme": "general",
                "aspect_ratio": "16:9",
            })

        # Map effects to a global_effects dict
        effect_types = list({e["effect_type"] for e in effects})
        transition_map: List[Dict[str, Any]] = [
            {"at": e["timestamp"], "type": e["effect_type"]} for e in effects
        ]

        return {
            "name": f"Cloned template",
            "description": "Auto-generated from an uploaded reference video",
            "beatmap": beats,
            "media_slots": media_slots,
            "global_effects": {
                "color_lut": None,
                "transitions": transition_map,
                "detected_effect_types": effect_types,
            },
            "is_public": False,
        }

    async def clone_style(
        self,
        reference_video_path: str,
        user_media_list: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """End-to-end: analyse reference â†’ generate template â†’ apply to user media.

        Returns:
            Dict with ``template`` (the generated template dict) and
            ``timeline`` (the rendered timeline JSON).
        """
        analysis = await self.analyze_reference_video(reference_video_path)
        template_dict = self.generate_template_from_reference(analysis)

        # Persist the template so TemplateEngine can load it
        from app.models.template import VideoTemplate

        template = VideoTemplate(
            name=template_dict["name"],
            description=template_dict["description"],
            beatmap=template_dict["beatmap"],
            media_slots=template_dict["media_slots"],
            global_effects=template_dict["global_effects"],
            is_public=template_dict["is_public"],
        )
        async with database.async_session_maker() as db:
            db.add(template)
            await db.commit()
            await db.refresh(template)

        timeline = await self._engine.apply_template(template.id, user_media_list)

        return {
            "template_id": str(template.id),
            "template": template_dict,
            "timeline": timeline,
            "analysis": analysis,
        }



def get_video_style_cloner(): return VideoStyleCloner()

