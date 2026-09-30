"""Standalone runtime checks for timeline compilation and FFmpeg probing.

These tests intentionally do not use the application's database fixtures.  They
create all media below pytest's temporary directory and only exercise the
renderer/compiler boundary.
"""

import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest

from video_engine.rendering.ffmpeg_renderer import FFmpegRenderer
from video_engine.rendering.timeline_to_ffmpeg import ResolvedClip, TimelineCompiler


FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


def _clip(clip_id, start, end, *, track=0, order=0, kind="video"):
    return ResolvedClip(
        clip_id=clip_id,
        track_type=kind,
        source_path="source.mp4",
        source_start=0,
        source_end=1,
        source_duration=1,
        timeline_start=start,
        timeline_end=end,
        timeline_duration=end - start,
        sequence_order=order,
        track_index=track,
    )


def test_compiler_uses_layer_for_z_order_and_timeline_for_placement():
    compiler = TimelineCompiler()
    result = compiler.compile(
        {"total_duration": 3, "tracks": []},
        [
            _clip("base-a", 0, 1, order=7),
            _clip("base-b", 2, 3, order=2),
            _clip("overlay", 1, 2, track=1, order=0),
        ],
        {"width": 64, "height": 64, "fps": 10},
    )

    assert result.total_duration == pytest.approx(3)
    filters = result.ffmpeg_inputs.filter_complex
    assert "concat=" not in filters
    assert "setpts=PTS-STARTPTS+2/TB" in filters
    assert "overlay=eof_action=pass:repeatlast=0" in filters


@pytest.mark.skipif(not FFMPEG or not FFPROBE, reason="ffmpeg and ffprobe are required")
def test_renderer_reports_media_duration_not_wall_clock(tmp_path: Path):
    source = tmp_path / "source.mp4"
    output = tmp_path / "render.mp4"
    subprocess.run(
        [
            FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=red:s=64x64:r=10",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=8000",
            "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-shortest", str(source),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    compiler = TimelineCompiler()
    compiled = compiler.compile(
        {"total_duration": 1.5, "tracks": []},
        [
            ResolvedClip("v", "video", str(source), 0, 1, 1, 0, 1.5, 1.5, 0),
            ResolvedClip("a", "audio", str(source), 0, 1, 1, 0, 1.5, 1.5, 0),
        ],
        {"width": 64, "height": 64, "fps": 10, "video_codec": "libx264", "crf": 35,
         "preset": "ultrafast", "audio_codec": "aac", "audio_bitrate": "32k"},
    )
    result = asyncio.run(FFmpegRenderer(FFMPEG, FFPROBE, timeout=60).render(
        inputs=compiled.ffmpeg_inputs.inputs,
        input_options=compiled.ffmpeg_inputs.input_options,
        filter_complex=compiled.ffmpeg_inputs.filter_complex,
        output_mapping=compiled.ffmpeg_inputs.output_mapping,
        output_options=compiled.ffmpeg_inputs.output_options,
        output_path=str(output),
        total_duration=compiled.total_duration,
    ))
    assert result.success, result.error_message
    assert result.duration == pytest.approx(1.5, abs=0.15)
    assert result.duration != pytest.approx(0, abs=0.01)
    assert result.audio_codec
