"""
Timeline to FFmpeg compiler.
Converts Phase 4 timeline JSON into FFmpeg filter_complex and arguments.
"""

import os
import math
import platform
import uuid
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# Phase 15: Recognized image file extensions for still-image timeline inputs
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"})


@dataclass
class ResolvedClip:
    """A clip with resolved source file path."""
    clip_id: str
    track_type: str  # 'video' or 'audio'
    source_path: str
    source_start: float
    source_end: float
    source_duration: float
    timeline_start: float
    timeline_end: float
    timeline_duration: float
    sequence_order: int
    properties: Dict[str, Any] = field(default_factory=dict)
    track_index: int = 0  # Layer, independent of sequence_order within a track.


@dataclass
class FFmpegInputs:
    """FFmpeg input file specifications."""
    inputs: List[str]  # input file paths
    input_options: List[List[str]]  # per-input options
    filter_complex: str
    output_mapping: List[str]  # -map arguments
    output_options: List[str]


@dataclass
class CompileResult:
    """Result of timeline compilation."""
    ffmpeg_inputs: FFmpegInputs
    total_duration: float
    video_track_count: int
    audio_track_count: int
    warnings: List[str] = field(default_factory=list)


class TimelineCompiler:
    """Compile timeline JSON to FFmpeg command."""

    def __init__(self):
        self._input_index = 0
        self._filter_index = 0

    # --- Font & drawtext helpers ---

    # Common font filename mappings (family name -> filename)
    _FONT_FILE_MAP: Dict[str, str] = {
        "arial": "arial.ttf",
        "arial bold": "arialbd.ttf",
        "helvetica": "Helvetica.ttf",
        "times new roman": "times.ttf",
        "courier new": "cour.ttf",
        "roboto": "Roboto-Regular.ttf",
        "roboto bold": "Roboto-Bold.ttf",
    }

    @staticmethod
    def _get_system_font_dirs() -> List[str]:
        """Return standard system font directories for the current OS."""
        system = platform.system()
        if system == "Windows":
            windir = os.environ.get("WINDIR", r"C:\Windows")
            return [os.path.join(windir, "Fonts")]
        elif system == "Darwin":
            return [
                "/System/Library/Fonts",
                "/Library/Fonts",
                os.path.expanduser("~/Library/Fonts"),
            ]
        else:  # Linux / other
            return [
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.local/share/fonts"),
            ]

    @classmethod
    def _resolve_font_path(cls, font_family: str) -> Optional[str]:
        """
        Resolve a font family name to an absolute .ttf path.

        Returns the path if found, or None to let FFmpeg use fontconfig fallback.
        """
        filename = cls._FONT_FILE_MAP.get(font_family.lower())
        if not filename:
            # Try "<family>.ttf" as a guess
            filename = font_family.replace(" ", "") + ".ttf"

        for font_dir in cls._get_system_font_dirs():
            candidate = os.path.join(font_dir, filename)
            if os.path.isfile(candidate):
                return candidate

        # Not found — return None so caller can use `font` param instead
        return None

    @staticmethod
    def _escape_drawtext(text: str) -> str:
        """
        Escape text for FFmpeg drawtext filter.

        FFmpeg drawtext requires escaping of: \\ : '
        The escaping order matters — backslashes first.
        """
        text = text.replace("\\", "\\\\")
        text = text.replace(":", "\\:")
        text = text.replace("'", "'\\\\\\''")
        return text

    @staticmethod
    def _escape_filter_path(path: str) -> str:
        """
        Escape a file path for FFmpeg filter option.

        On Windows, forward-slashes are safer inside FFmpeg filters.
        Colons (e.g. C:\\) must also be escaped.
        """
        # Normalise to forward slashes (works cross-platform in FFmpeg)
        path = path.replace("\\", "/")
        # Escape colons for drawtext/lut3d filter syntax
        path = path.replace(":", "\\:")
        return path

    def compile(
        self,
        timeline_json: Dict[str, Any],
        resolved_clips: List[ResolvedClip],
        output_settings: Dict[str, Any],
    ) -> CompileResult:
        """
        Compile timeline to FFmpeg arguments.

        Args:
            timeline_json: The timeline JSON from Phase 4
            resolved_clips: List of clips with resolved source paths
            output_settings: Dict with width, height, fps, codec, crf, preset, etc.

        Returns:
            CompileResult with FFmpeg inputs, filter_complex, and output options
        """
        for clip in resolved_clips:
            values = (clip.source_start, clip.source_end, clip.source_duration,
                      clip.timeline_start, clip.timeline_end, clip.timeline_duration)
            if not all(math.isfinite(v) for v in values):
                raise ValueError(f"Clip {clip.clip_id} has non-finite timing")
            if (clip.source_start < 0 or clip.timeline_start < 0
                    or clip.source_duration <= 0 or clip.timeline_duration <= 0
                    or not math.isclose(clip.source_end - clip.source_start, clip.source_duration, abs_tol=1e-6)
                    or not math.isclose(clip.timeline_end - clip.timeline_start, clip.timeline_duration, abs_tol=1e-6)):
                raise ValueError(f"Clip {clip.clip_id} has invalid timing")
            if clip.track_type not in {"video", "audio"}:
                raise ValueError(f"Unsupported track type: {clip.track_type}")
        # Only explicit audio tracks are mixed; video input audio is not auto-mapped.
        # Group clips by track type
        video_clips = [c for c in resolved_clips if c.track_type == "video"]
        audio_clips = [c for c in resolved_clips if c.track_type == "audio"]

        # Build inputs
        all_inputs = []
        all_input_options = []

        # Add video inputs
        for clip in video_clips:
            all_inputs.append(clip.source_path)
            ext = os.path.splitext(clip.source_path)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                # Phase 15: Still image → zoompan generates frames, so do not loop input
                all_input_options.append([
                    "-t", str(clip.timeline_duration),
                ])
            else:
                all_input_options.append([
                    "-ss", str(clip.source_start),
                    "-t", str(clip.source_duration),
                    "-avoid_negative_ts", "make_zero",
                ])

        # Add audio inputs
        for clip in audio_clips:
            all_inputs.append(clip.source_path)
            all_input_options.append([
                "-ss", str(clip.source_start),
                "-t", str(clip.source_duration),
                "-avoid_negative_ts", "make_zero",
            ])

        # Extract audio metadata for effects
        metadata = timeline_json.get("metadata", {})
        audio_meta = metadata.get("audio", {})
        audio_settings = timeline_json.get("audio_settings", {})
        
        apply_normalize = audio_meta.get("normalize", audio_settings.get("normalize", False))
        apply_ducking = audio_meta.get("ducking", audio_settings.get("ducking", False))

        # Extract video color metadata
        video_meta = metadata.get("video", {})
        global_color_meta = video_meta.get("color_correction", video_meta.get("color", timeline_json.get("color_settings", {})))

        # Extract graphics layers for text overlays (Phase 14)
        graphics_layers = timeline_json.get("graphics_layers", [])

        clips_max = max([c.timeline_end for c in resolved_clips] + [0.0])
        graphics_max = max([g.get("start_time", 0.0) + g.get("duration", 5.0)
                            for g in graphics_layers] + [0.0])
        total_duration = max(clips_max, graphics_max, float(timeline_json.get("total_duration", 0)))
        if not math.isfinite(total_duration) or total_duration <= 0:
            raise ValueError("Timeline must have a finite positive duration")
        # Build filter complex
        filter_complex, has_video, has_audio = self._build_filter_complex(
            video_clips, audio_clips, output_settings, apply_normalize, apply_ducking,
            global_color_meta, graphics_layers, total_duration,
        )

        # Build output mapping
        output_mapping = []
        if has_video:
            output_mapping.extend(["-map", "[video_out]"])
        if has_audio:
            output_mapping.extend(["-map", "[audio_out]"])

        # Build output options
        output_options = self._build_output_options(output_settings)
        output_options.extend(["-t", str(total_duration)])

        return CompileResult(
            ffmpeg_inputs=FFmpegInputs(
                inputs=all_inputs,
                input_options=all_input_options,
                filter_complex=filter_complex,
                output_mapping=output_mapping,
                output_options=output_options,
            ),
            total_duration=total_duration,
            video_track_count=len({c.track_index for c in video_clips}),
            audio_track_count=len({c.track_index for c in audio_clips}),
        )

    def _build_output_options(self, settings: Dict[str, Any]) -> List[str]:
        """Build FFmpeg output options from settings."""
        opts = []

        # Hardware acceleration
        hwaccel = settings.get("hwaccel")
        if hwaccel == "nvenc":
            opts.extend(["-c:v", settings.get("video_codec", "h264_nvenc")])
            if settings.get("video_bitrate"):
                opts.extend(["-b:v", settings["video_bitrate"]])
            else:
                opts.extend(["-cq", str(settings.get("crf", 23))])
            opts.extend(["-preset", settings.get("preset", "p4")])
        elif hwaccel == "qsv":
            opts.extend(["-c:v", settings.get("video_codec", "h264_qsv")])
            if settings.get("video_bitrate"):
                opts.extend(["-b:v", settings["video_bitrate"]])
            else:
                opts.extend(["-global_quality", str(settings.get("crf", 23))])
            opts.extend(["-preset", settings.get("preset", "medium")])
        elif hwaccel == "videotoolbox":
            opts.extend(["-c:v", settings.get("video_codec", "h264_videotoolbox")])
            if settings.get("video_bitrate"):
                opts.extend(["-b:v", settings["video_bitrate"]])
            else:
                opts.extend(["-q:v", str(settings.get("crf", 50))])
        else:
            # Video codec (software)
            opts.extend(["-c:v", settings.get("video_codec", "libx264")])

            # CRF or bitrate
            if settings.get("video_bitrate"):
                opts.extend(["-b:v", settings["video_bitrate"]])
            else:
                opts.extend(["-crf", str(settings.get("crf", 23))])

            # Encoder preset
            opts.extend(["-preset", settings.get("preset", "medium")])

        # Pixel format
        opts.extend(["-pix_fmt", settings.get("pixel_format", "yuv420p")])

        # Audio codec
        opts.extend(["-c:a", settings.get("audio_codec", "aac")])

        # Audio bitrate
        opts.extend(["-b:a", settings.get("audio_bitrate", "128k")])

        # Audio sample rate
        if settings.get("audio_sample_rate"):
            opts.extend(["-ar", str(settings["audio_sample_rate"])])

        # Fast start for web playback
        opts.extend(["-movflags", "+faststart"])

        # Threads
        opts.extend(["-threads", "2"])

        return opts

    # --- Phase 16: Generic effect system ---

    # Maps known effect names to FFmpeg filter builders.
    # Each builder receives the effect dict and returns an FFmpeg filter string.
    _EFFECT_MAP: Dict[str, Any] = {
        "BLUR": lambda e: (
            f"boxblur={e.get('radius', 2)}:{e.get('radius', 2)}"
            f":enable='between(t,{e.get('start', 0)},{e.get('end', 9999)})'"
            if "start" in e or "end" in e
            else f"boxblur={e.get('radius', 2)}:{e.get('radius', 2)}"
        ),
        "SHARPEN": lambda e: (
            f"unsharp={e.get('luma_x', 5)}:{e.get('luma_y', 5)}"
            f":{e.get('luma_amount', 1.0)}"
            f":{e.get('chroma_x', 5)}:{e.get('chroma_y', 5)}"
            f":{e.get('chroma_amount', 0.0)}"
        ),
        "SPEED_RAMP": lambda e: (
            f"setpts={e.get('factor', 1.0)}*PTS"
        ),
        "CHROMA_KEY": lambda e: (
            f"colorkey={e.get('color', '0x00FF00')}:{e.get('similarity', 0.3)}:{e.get('blend', 0.1)}"
        ),
        "VIGNETTE": lambda e: (
            f"vignette=PI/4*{e.get('intensity', 0.5)}"
        ),
        "GLOW": lambda e: (
            f"gblur=sigma={e.get('radius', 10)}:steps=2"
        ),
    }

    def _build_clip_effects(self, props: Dict[str, Any]) -> List[str]:
        """
        Read clip properties['effects'] and return a list of FFmpeg filter strings.

        Expected format in clip properties:
            "effects": [
                {"type": "BLUR", "radius": 4},
                {"type": "SHARPEN", "luma_amount": 1.5},
                {"type": "SPEED_RAMP", "factor": 0.5},
            ]
        """
        effects = props.get("effects", [])
        filters: List[str] = []
        for effect in effects:
            effect_type = effect.get("type", "").upper()
            builder = self._EFFECT_MAP.get(effect_type)
            if builder:
                filters.append(builder(effect))
        return filters

    def _build_filter_complex(
        self,
        video_clips: List[ResolvedClip],
        audio_clips: List[ResolvedClip],
        output_settings: Dict[str, Any],
        apply_normalize: bool,
        apply_ducking: bool,
        global_color_meta: Dict[str, Any] = None,
        graphics_layers: List[Dict[str, Any]] = None,
        total_duration: float = 0.0,
    ) -> Tuple[str, bool, bool]:
        """Build the FFmpeg filter complex string."""
        if global_color_meta is None:
            global_color_meta = {}
        if graphics_layers is None:
            graphics_layers = []
        filter_parts = []
        video_filter_labels = []

        sorted_video_clips = sorted(video_clips, key=lambda c: (c.track_index, c.timeline_start, c.sequence_order))

        has_video = bool(sorted_video_clips or graphics_layers)

        if has_video:
            all_clips = video_clips + audio_clips
            clips_max = max([c.timeline_end for c in all_clips] + [0.0]) if all_clips else 0.0
            graphics_max = max([(g.get("start_time", 0.0) + g.get("duration", 5.0)) for g in graphics_layers] + [0.0]) if graphics_layers else 0.0
            total_duration = max(total_duration, clips_max, graphics_max) or 1.0

            for i, clip in enumerate(sorted_video_clips):
                # We need the original input index from `video_clips` order
                input_idx = video_clips.index(clip)
                label = f"v{i}_prep"
                
                props = clip.properties
                color_meta = props.get("color_correction", props.get("color", {}))
                
                # 1. Color correction
                eq_params = []
                if "brightness" in color_meta:
                    eq_params.append(f"brightness={color_meta['brightness']}")
                if "contrast" in color_meta:
                    eq_params.append(f"contrast={color_meta['contrast']}")
                if "saturation" in color_meta:
                    eq_params.append(f"saturation={color_meta['saturation']}")
                
                color_filter = ""
                if eq_params:
                    color_filter += f"eq={':'.join(eq_params)},"
                    
                if "lut_path" in color_meta:
                    lut_escaped = self._escape_filter_path(color_meta['lut_path'])
                    color_filter += f"lut3d=file='{lut_escaped}',"
                elif "lut" in color_meta:
                    lut_escaped = self._escape_filter_path(color_meta['lut'])
                    color_filter += f"lut3d=file='{lut_escaped}',"

                # 2. Scale & Pad
                w = output_settings['width']
                h = output_settings['height']
                fps = output_settings.get('fps', 30)

                prep_filters = ["setpts=PTS-STARTPTS"]
                if os.path.splitext(clip.source_path)[1].lower() not in IMAGE_EXTENSIONS:
                    prep_filters.append(f"setpts={clip.timeline_duration / clip.source_duration}*PTS")

                # Phase 15: Ken Burns zoompan for still-image inputs
                ext = os.path.splitext(clip.source_path)[1].lower()
                if ext in IMAGE_EXTENSIONS:
                    ken = props.get("ken_burns", {})
                    zoom_start = ken.get("zoom_start", 1.0)
                    zoom_end = ken.get("zoom_end", 1.2)
                    pan_x = ken.get("pan_x", "iw/2-(iw/zoom/2)")
                    pan_y = ken.get("pan_y", "ih/2-(ih/zoom/2)")
                    total_frames = int(clip.timeline_duration * fps)
                    # Linear zoom interpolation across the clip duration
                    zoom_expr = f"{zoom_start}+({zoom_end}-{zoom_start})*on/{max(total_frames, 1)}"
                    prep_filters.append(
                        f"zoompan=z='{zoom_expr}':x='{pan_x}':y='{pan_y}'"
                        f":d={total_frames}:s={w}x{h}:fps={fps}"
                    )

                # 2. Scale & Pad / Smart Auto-Reframe Crop
                smart_crop = props.get("smart_crop") or output_settings.get("smart_crop", {})
                if isinstance(smart_crop, dict) and smart_crop.get("enabled"):
                    center_x = float(smart_crop.get("center_x", 0.5))
                    prep_filters.extend([
                        f"crop=w='min(iw,ih*{w}/{h})':h='min(ih,iw*{h}/{w})':x='min(max(0,iw*{center_x}-(min(iw,ih*{w}/{h}))/2),iw-(min(iw,ih*{w}/{h})))':y='(ih-min(ih,iw*{h}/{w}))/2'",
                        f"scale={w}:{h}",
                        "setsar=1",
                        f"fps={fps}"
                    ])
                else:
                    prep_filters.extend([
                        f"scale={w}:{h}:force_original_aspect_ratio=decrease",
                        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
                        "setsar=1",
                        f"fps={fps}"
                    ])
                
                if color_filter:
                    prep_filters.append(color_filter.rstrip(","))
                    
                # 3. Format & Opacity (add alpha channel before rotate/effects)
                prep_filters.append("format=yuva420p")

                if "opacity" in props:
                    opacity = props["opacity"]
                    prep_filters.append(f"colorchannelmixer=aa={opacity}")

                # 4. Rotate
                if "rotate" in props:
                    angle = props["rotate"]
                    # Convert degrees to radians for rotate filter
                    prep_filters.append(f"rotate={angle}*PI/180:c=none:ow=rotw({angle}*PI/180):oh=roth({angle}*PI/180)")

                # Phase 16: Apply generic clip effects
                prep_filters.extend(self._build_clip_effects(props))

                # 5. Chromakey
                if "chromakey" in props:
                    ck = props["chromakey"]
                    color = ck.get("color", "0x00FF00")
                    sim = ck.get("similarity", 0.1)
                    blend = ck.get("blend", 0.1)
                    prep_filters.append(f"chromakey={color}:{sim}:{blend}")

                # Shift timestamps to match timeline_start
                prep_filters.append(f"trim=duration={clip.timeline_duration}")
                prep_filters.append(f"setpts=PTS-STARTPTS+{clip.timeline_start}/TB")

                # Combine prep filters
                filter_parts.append(f"[{input_idx}:v]{','.join(prep_filters)}[{label}]")

            # A full-length background preserves leading, internal and trailing gaps.
            filter_parts.append(
                f"color=c=black:s={output_settings['width']}x{output_settings['height']}:"
                f"r={output_settings.get('fps', 30)}:d={total_duration}[bg]"
            )
            current_bg = "bg"

            # 6. Overlay upper-layer clips onto current background
            for i, clip in enumerate(sorted_video_clips):
                label = f"v{i}_prep"
                start = clip.timeline_start
                end = clip.timeline_end
                
                next_bg = f"bg_{i}"
                props = clip.properties
                blend_mode = props.get("blend_mode", "normal").lower()
                
                if blend_mode == "normal":
                    overlay_filter = f"[{current_bg}][{label}]overlay=eof_action=pass:repeatlast=0:enable='gte(t,{start})*lt(t,{end})'"
                else:
                    blend_map = {
                        "multiply": "multiply",
                        "screen": "screen",
                        "overlay": "overlay",
                        "darken": "darken",
                        "lighten": "lighten",
                        "color_burn": "colorburn",
                        "color_dodge": "colordodge",
                        "addition": "addition",
                        "difference": "difference",
                        "exclusion": "exclusion",
                        "hard_light": "hardlight",
                        "soft_light": "softlight"
                    }
                    ffmpeg_blend = blend_map.get(blend_mode, "normal")
                    
                    if ffmpeg_blend == "normal":
                        overlay_filter = f"[{current_bg}][{label}]overlay=eof_action=pass:repeatlast=0:enable='gte(t,{start})*lt(t,{end})'"
                    else:
                        overlay_filter = f"[{current_bg}][{label}]blend=all_mode={ffmpeg_blend}:enable='gte(t,{start})*lt(t,{end})'"
                
                filter_parts.append(f"{overlay_filter}[{next_bg}]")
                current_bg = next_bg

            # --- Phase 14: Text overlay drawtext filters ---
            text_layers = [
                layer for layer in graphics_layers
                if layer.get("layer_type") in ("text", "subtitle", "lower_third")
                and layer.get("content")
            ]

            for t_idx, layer in enumerate(text_layers):
                escaped_text = self._escape_drawtext(layer["content"])
                font_size = layer.get("font_size", 48)
                font_color = layer.get("font_color", "#FFFFFF")
                start_time = layer.get("start_time", 0.0)
                duration = layer.get("duration", 5.0)
                end_time = start_time + duration

                # Position: model stores 0-1 normalized, convert to pixels
                pos_x = layer.get("position_x", 0.5)
                pos_y = layer.get("position_y", 0.9)
                x_expr = f"(w*{pos_x})-(tw/2)"
                y_expr = f"(h*{pos_y})-(th/2)"

                # Font: resolve to absolute path or fall back to font= param
                font_family = layer.get("font_family", "Arial")
                font_path = self._resolve_font_path(font_family)
                if font_path:
                    font_param = f"fontfile='{self._escape_filter_path(font_path)}'"
                else:
                    # Fallback: let FFmpeg/fontconfig resolve by name
                    font_param = f"font='{self._escape_drawtext(font_family)}'"

                # Background box (optional)
                box_params = ""
                bg_color = layer.get("background_color")
                if bg_color:
                    box_params = f":box=1:boxcolor={bg_color}:boxborderw=5"

                drawtext = (
                    f"drawtext={font_param}"
                    f":fontsize={font_size}"
                    f":fontcolor={font_color}"
                    f":text='{escaped_text}'"
                    f":x={x_expr}:y={y_expr}"
                    f":enable='between(t,{start_time},{end_time})'"
                    f"{box_params}"
                )

                next_label = f"txt_{t_idx}"
                filter_parts.append(f"[{current_bg}]{drawtext}[{next_label}]")
                current_bg = next_label

            # Global color correction
            global_eq = []
            if "brightness" in global_color_meta:
                global_eq.append(f"brightness={global_color_meta['brightness']}")
            if "contrast" in global_color_meta:
                global_eq.append(f"contrast={global_color_meta['contrast']}")
            if "saturation" in global_color_meta:
                global_eq.append(f"saturation={global_color_meta['saturation']}")
            
            global_color_filter = ""
            if global_eq:
                global_color_filter += f"eq={':'.join(global_eq)}"
                
            lut_file = global_color_meta.get("lut_path", global_color_meta.get("lut"))
            if lut_file:
                lut_escaped = self._escape_filter_path(lut_file)
                if global_color_filter:
                    global_color_filter += f",lut3d=file='{lut_escaped}'"
                else:
                    global_color_filter = f"lut3d=file='{lut_escaped}'"
                    
            if global_color_filter:
                filter_parts.append(f"[{current_bg}]{global_color_filter}[video_out]")
            else:
                filter_parts.append(f"[{current_bg}]copy[video_out]")

        # Process audio tracks
        audio_input_offset = len(video_clips)
        primary_clips = []
        secondary_clips = []
        for i, clip in enumerate(audio_clips):
            role = clip.properties.get("role", "primary")
            if role in ("background_music", "music", "secondary"):
                secondary_clips.append((i, clip))
            else:
                primary_clips.append((i, clip))

        def build_audio_stream(clips, stream_name):
            if not clips:
                return False
            labels = []
            for idx, c in clips:
                input_idx = audio_input_offset + idx
                lbl = f"a{idx}"
                delay_ms = max(0, int(c.timeline_start * 1000))
                tempo = c.source_duration / c.timeline_duration
                tempo_filters = []
                while tempo > 2:
                    tempo_filters.append("atempo=2")
                    tempo /= 2
                while tempo < 0.5:
                    tempo_filters.append("atempo=0.5")
                    tempo *= 2
                tempo_filters.append(f"atempo={tempo}")
                volume = 0 if c.properties.get("muted") else float(c.properties.get("volume", 1.0))
                if not math.isfinite(volume) or volume < 0:
                    raise ValueError(f"Clip {c.clip_id} has invalid volume")
                audio_filter = (
                    f"[{input_idx}:a]asetpts=PTS-STARTPTS,{','.join(tempo_filters)},"
                    f"atrim=duration={c.timeline_duration},volume={volume},"
                    f"aresample={output_settings.get('audio_sample_rate', 48000)},"
                    f"aformat=channel_layouts=stereo:sample_fmts=fltp,"
                    f"adelay={delay_ms}|{delay_ms}[{lbl}]"
                )
                filter_parts.append(audio_filter)
                labels.append(lbl)
            
            if len(labels) == 1:
                filter_parts.append(f"[{labels[0]}]acopy[{stream_name}]")
            else:
                amix_inputs = "".join(f"[{lbl}]" for lbl in labels)
                filter_parts.append(f"{amix_inputs}amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0[{stream_name}]")
            return True

        has_primary = build_audio_stream(primary_clips, "primary_audio")
        has_secondary = build_audio_stream(secondary_clips, "secondary_audio")

        current_audio = None
        
        if apply_ducking and has_primary and has_secondary:
            # Sidechain compression for ducking
            filter_parts.append("[primary_audio]asplit=2[primary_out][primary_sc]")
            filter_parts.append("[secondary_audio][primary_sc]sidechaincompress=threshold=0.05:ratio=4:attack=5:release=50[secondary_ducked]")
            filter_parts.append("[primary_out][secondary_ducked]amix=inputs=2:duration=longest:dropout_transition=2:normalize=0[mixed_audio]")
            current_audio = "mixed_audio"
        elif has_primary and has_secondary:
            filter_parts.append("[primary_audio][secondary_audio]amix=inputs=2:duration=longest:dropout_transition=2:normalize=0[mixed_audio]")
            current_audio = "mixed_audio"
        elif has_primary:
            current_audio = "primary_audio"
        elif has_secondary:
            current_audio = "secondary_audio"

        has_audio = False
        if current_audio:
            has_audio = True
            if apply_normalize:
                # EBU R128 normalization (loudnorm)
                filter_parts.append(f"[{current_audio}]loudnorm=I=-16:TP=-1.5:LRA=11,apad,atrim=duration={total_duration}[audio_out]")
            else:
                filter_parts.append(f"[{current_audio}]apad,atrim=duration={total_duration}[audio_out]")

        filter_complex = ";".join(filter_parts) if filter_parts else ""
        return filter_complex, has_video, has_audio


def create_timeline_compiler() -> TimelineCompiler:
    """Factory function."""
    return TimelineCompiler()
