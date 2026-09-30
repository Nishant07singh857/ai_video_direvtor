"""
FFmpeg Renderer.
Executes FFmpeg commands safely with progress tracking and error handling.
"""

import asyncio
import subprocess
import tempfile
import os
import shutil
import signal
import time
import collections
import inspect
import json
import math
from fractions import Fraction
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RenderProgress:
    """Progress information during rendering."""
    frame: int = 0
    fps: float = 0.0
    bitrate: str = ""
    total_size: str = ""
    out_time: float = 0.0
    dup_frames: int = 0
    drop_frames: int = 0
    speed: str = ""
    progress_percent: float = 0.0


@dataclass
class RenderResult:
    """Result of a render operation."""
    success: bool
    output_path: str
    duration: float
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    bitrate: Optional[int] = None
    error_message: Optional[str] = None
    ffmpeg_cmd: Optional[str] = None
    stderr: Optional[str] = None


class FFmpegRenderer:
    """Safe FFmpeg command execution with progress tracking."""

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        timeout: int = 3600,
    ):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.timeout = timeout
        self._process: Optional[asyncio.subprocess.Process] = None
        self._cancelled = False

    def cancel(self):
        """Cancel the current render."""
        self._cancelled = True
        if self._process and self._process.returncode is None:
            try:
                # Send SIGTERM (graceful) then SIGKILL if needed
                self._process.terminate()
            except Exception:
                pass

    def _parse_progress_line(self, line: str, total_duration: float) -> Optional[RenderProgress]:
        """Parse FFmpeg progress output line."""
        # FFmpeg progress format: key=value lines
        if "=" not in line:
            return None

        parts = line.strip().split("=")
        if len(parts) != 2:
            return None

        key, value = parts
        progress = RenderProgress()

        try:
            if key == "frame":
                progress.frame = int(value)
            elif key == "fps":
                progress.fps = float(value)
            elif key == "bitrate":
                progress.bitrate = value
            elif key == "total_size":
                progress.total_size = value
            elif key in {"out_time_us", "out_time_ms"}:
                progress.out_time = float(value) / 1_000_000
                if total_duration > 0:
                    progress.progress_percent = min(100.0, (progress.out_time / total_duration) * 100)
            elif key == "out_time":
                # Alternative format
                h, m, s = value.split(":")
                progress.out_time = int(h) * 3600 + int(m) * 60 + float(s)
                if total_duration > 0:
                    progress.progress_percent = min(100.0, (progress.out_time / total_duration) * 100)
            elif key == "dup_frames":
                progress.dup_frames = int(value)
            elif key == "drop_frames":
                progress.drop_frames = int(value)
            elif key == "speed":
                progress.speed = value
            elif key == "progress":
                if value == "end":
                    progress.progress_percent = 100.0
        except ValueError:
            pass

        # Non-time lines carry zeros, not a new progress estimate.
        if key not in {"out_time_us", "out_time_ms", "out_time", "progress"}:
            return None
        if not math.isfinite(progress.progress_percent):
            return None
        progress.progress_percent = max(0.0, progress.progress_percent)
        return progress

    async def render(
        self,
        inputs: List[str],
        input_options: List[List[str]],
        filter_complex: str,
        output_mapping: List[str],
        output_options: List[str],
        output_path: str,
        total_duration: float,
        progress_callback: Optional[Callable[[RenderProgress], None]] = None,
    ) -> RenderResult:
        """
        Execute FFmpeg render.

        Args:
            inputs: List of input file paths
            input_options: Per-input options
            filter_complex: FFmpeg filter_complex string
            output_mapping: -map arguments
            output_options: Output encoding options
            output_path: Output file path
            total_duration: Expected total duration for progress calculation
            progress_callback: Optional callback for progress updates

        Returns:
            RenderResult with success status and output info
        """
        if self._process is not None:
            raise RuntimeError("Renderer is already in use")
        # Cancellation belongs to one render invocation, not the renderer
        # instance.  cancel() is meaningful only while this process is live.
        self._cancelled = False
        if len(inputs) != len(input_options):
            raise ValueError("Each input must have its own options")
        if not math.isfinite(total_duration) or total_duration <= 0:
            raise ValueError("Expected duration must be finite and positive")
        if self._cancelled:
            return RenderResult(False, output_path, 0, 0, error_message="Render cancelled by user")

        # Ensure output directory exists
        await asyncio.to_thread(Path(output_path).parent.mkdir, parents=True, exist_ok=True)

        # Build command
        cmd = [self.ffmpeg_path, "-y", "-nostdin", "-filter_complex_threads", "1"]

        # Add inputs with options
        for i, (input_file, opts) in enumerate(zip(inputs, input_options)):
            cmd.extend(opts)
            cmd.extend(["-i", input_file])

        # Add filter complex
        if filter_complex:
            cmd.extend(["-filter_complex", filter_complex])

        # Add output mapping
        cmd.extend(output_mapping)

        # Add output options
        cmd.extend(output_options)

        # Add progress output
        cmd.extend(["-progress", "pipe:1", "-nostats"])

        # Add output file
        cmd.append(output_path)

        ffmpeg_cmd_str = " ".join(cmd)
        print(f"FFmpeg command: {ffmpeg_cmd_str}")

        # Execute
        start_time = time.time()
        stderr_lines = collections.deque(maxlen=100)

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            if self._cancelled:
                self.cancel()

            async def read_stdout():
                if not self._process.stdout:
                    return
                while True:
                    line = await self._process.stdout.readline()
                    if not line:
                        break
                    line_str = line.decode('utf-8', errors='replace').strip()
                    if self._cancelled:
                        try:
                            self._process.terminate()
                        except ProcessLookupError:
                            pass
                        break
                    if line_str:
                        prog = self._parse_progress_line(line_str, total_duration)
                        if prog and progress_callback:
                            callback_result = progress_callback(prog)
                            if inspect.isawaitable(callback_result):
                                await callback_result

            async def read_stderr():
                if not self._process.stderr:
                    return
                while True:
                    line = await self._process.stderr.readline()
                    if not line:
                        break
                    line_str = line.decode('utf-8', errors='replace').strip()
                    if line_str:
                        stderr_lines.append(line_str)

            # Concurrently read stdout (for progress) and stderr (for errors/logs)
            # Wait for completion with timeout
            try:
                _, _, return_code = await asyncio.wait_for(
                    asyncio.gather(read_stdout(), read_stderr(), self._process.wait()),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                try:
                    self._process.kill()
                except ProcessLookupError:
                    pass
                await self._process.wait()
                return RenderResult(
                    success=False,
                    output_path=output_path,
                    duration=0,
                    file_size=0,
                    error_message=f"Render timed out after {self.timeout}s",
                    ffmpeg_cmd=ffmpeg_cmd_str,
                )

            if self._cancelled:
                return RenderResult(
                    success=False,
                    output_path=output_path,
                    duration=0,
                    file_size=0,
                    error_message="Render cancelled by user",
                    ffmpeg_cmd=ffmpeg_cmd_str,
                )

            elapsed = time.time() - start_time

            if return_code != 0:
                error_msg = "\n".join(list(stderr_lines)[-20:]) if stderr_lines else "FFmpeg failed"
                return RenderResult(
                    success=False,
                    output_path=output_path,
                    duration=0,
                    file_size=0,
                    error_message=f"FFmpeg exited with code {return_code}: {error_msg}",
                    ffmpeg_cmd=ffmpeg_cmd_str,
                    stderr="\n".join(stderr_lines),
                )

            # Validate output
            if not await asyncio.to_thread(os.path.exists, output_path):
                return RenderResult(
                    success=False,
                    output_path=output_path,
                    duration=0,
                    file_size=0,
                    error_message="Output file was not created",
                    ffmpeg_cmd=ffmpeg_cmd_str,
                    stderr="\n".join(stderr_lines),
                )

            file_size = await asyncio.to_thread(os.path.getsize, output_path)
            if file_size == 0:
                return RenderResult(
                    success=False,
                    output_path=output_path,
                    duration=0,
                    file_size=0,
                    error_message="Output file is empty",
                    ffmpeg_cmd=ffmpeg_cmd_str,
                    stderr="\n".join(stderr_lines),
                )

            # Probe output for metadata
            metadata = await self._probe_output(output_path)
            duration = metadata.get("duration", 0)
            format_name = str(metadata.get("format_name") or "")
            extension = Path(output_path).suffix.lower()
            expected_container = extension == ".mp4" and "mp4" in format_name.split(",")
            if (not metadata.get("width") or not metadata.get("height")
                    or not metadata.get("video_codec") or not metadata.get("fps")
                    or not metadata.get("has_video") or (not expected_container and extension == ".mp4")
                    or not math.isfinite(duration) or duration <= 0
                    or not math.isfinite(float(metadata.get("video_duration") or duration))
                    or float(metadata.get("video_duration") or duration) <= 0):
                return RenderResult(
                    success=False,
                    output_path=output_path,
                    duration=0,
                    file_size=file_size,
                    error_message="FFprobe could not verify an MP4 video stream and positive duration",
                    ffmpeg_cmd=ffmpeg_cmd_str,
                    stderr="\n".join(stderr_lines),
                )

            tolerance = max(0.1, 2 / metadata["fps"])
            if abs(duration - total_duration) > tolerance:
                return RenderResult(
                    False, output_path, duration, file_size,
                    error_message=f"Output duration {duration:.3f}s differs from timeline {total_duration:.3f}s",
                    ffmpeg_cmd=ffmpeg_cmd_str,
                )

            return RenderResult(
                success=True,
                output_path=output_path,
                duration=duration,
                file_size=file_size,
                width=metadata.get("width"),
                height=metadata.get("height"),
                fps=metadata.get("fps"),
                video_codec=metadata.get("video_codec"),
                audio_codec=metadata.get("audio_codec"),
                bitrate=metadata.get("bitrate"),
                ffmpeg_cmd=ffmpeg_cmd_str,
                stderr="\n".join(stderr_lines),
            )

        except Exception as e:
            return RenderResult(
                success=False,
                output_path=output_path,
                duration=0,
                file_size=0,
                error_message=f"Render failed: {str(e)}",
                ffmpeg_cmd=ffmpeg_cmd_str,
            )
        finally:
            if self._process and self._process.returncode is None:
                try:
                    self._process.kill()
                except ProcessLookupError:
                    pass
                await self._process.wait()
            self._process = None

    async def _probe_output(self, file_path: str) -> Dict[str, Any]:
        """Run ffprobe on output file to get metadata."""
        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-show_streams", "-show_format",
            "-of", "json",
            file_path,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                await proc.wait()
                raise
            if proc.returncode == 0:
                data = json.loads(stdout.decode('utf-8'))
                streams = data.get("streams", [])
                stream = next((s for s in streams if s.get("codec_type") == "video"
                               and not s.get("disposition", {}).get("attached_pic")), {})
                audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
                fmt = data.get("format", {})

                def positive(value):
                    try:
                        number = float(value)
                        return number if math.isfinite(number) and number > 0 else None
                    except (ValueError, TypeError):
                        return None

                fps = None
                for rate in (stream.get("avg_frame_rate"), stream.get("r_frame_rate")):
                    try:
                        fps = positive(float(Fraction(rate)))
                    except (ValueError, TypeError, ZeroDivisionError):
                        continue
                    if fps:
                        break
                # An explicitly invalid container duration must not be hidden by a fallback.
                duration = positive(fmt.get("duration", stream.get("duration", audio.get("duration"))))
                bitrate = positive(fmt.get("bit_rate", stream.get("bit_rate")))
                return {
                    "width": positive(stream.get("width")),
                    "height": positive(stream.get("height")),
                    "fps": fps,
                    "duration": duration or 0,
                    "video_codec": stream.get("codec_name"),
                    "audio_codec": audio.get("codec_name"),
                    "video_duration": positive(stream.get("duration")),
                    "format_name": fmt.get("format_name"),
                    "has_video": bool(stream),
                    "bitrate": int(bitrate) if bitrate else None,
                }
        except Exception:
            pass

        return {}


def create_ffmpeg_renderer(
    ffmpeg_path: str = "ffmpeg",
    ffprobe_path: str = "ffprobe",
    timeout: int = 3600,
) -> FFmpegRenderer:
    """Factory function."""
    return FFmpegRenderer(ffmpeg_path, ffprobe_path, timeout)
