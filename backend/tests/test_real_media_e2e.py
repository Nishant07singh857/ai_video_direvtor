"""Isolated upload-to-download verification using synthetic media only."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from pathlib import Path
from uuid import UUID

import pytest

from app.core.config import settings
from app.models import MediaAsset, RenderPreset, RenderPresetPlatform
from app.services.storage import LocalStorageService


FFMPEG = shutil.which(settings.FFMPEG_PATH or "ffmpeg")
FFPROBE = shutil.which(settings.FFPROBE_PATH or "ffprobe")


async def _wait_for_media(client, project_id: str, media_id: str, headers: dict) -> dict:
    for _ in range(60):
        response = await client.get(
            f"{settings.API_V1_PREFIX}/media/{media_id}",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        if payload["status"] in {"ready", "failed"}:
            assert payload["status"] == "ready", payload
            return payload
        await asyncio.sleep(0.1)
    raise AssertionError(f"Media analysis did not finish: {project_id}/{media_id}")


async def _wait_for_render(client, project_id: str, render_id: str, headers: dict) -> dict:
    for _ in range(120):
        response = await client.get(
            f"{settings.API_V1_PREFIX}/rendering/projects/{project_id}/renders/{render_id}",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        if payload["status"] in {"completed", "failed", "cancelled"}:
            assert payload["status"] == "completed", payload
            return payload
        await asyncio.sleep(0.1)
    raise AssertionError(f"Render did not finish: {project_id}/{render_id}")


@pytest.mark.skipif(not FFMPEG or not FFPROBE, reason="ffmpeg and ffprobe are required")
async def test_real_upload_template_preview_export_download(
    client,
    db_session,
    auth_headers,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Exercise the production contracts without touching configured media."""
    storage_module = __import__("app.services.storage", fromlist=["_local_storage"])
    isolated_storage = LocalStorageService(str(tmp_path / "media"))
    monkeypatch.setattr(storage_module, "_local_storage", isolated_storage)
    monkeypatch.setattr(settings, "CELERY_ENABLED", False)
    monkeypatch.setattr(settings, "RENDER_SYNC_FALLBACK", True)

    source = tmp_path / "synthetic.mp4"
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=160x90:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=8000",
            "-t",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(source),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    project_response = await client.post(
        f"{settings.API_V1_PREFIX}/projects",
        json={"name": "Isolated E2E"},
        headers=auth_headers,
    )
    assert project_response.status_code == 201, project_response.text
    project_id = project_response.json()["id"]

    async def upload(filename: str) -> dict:
        response = await client.post(
            f"{settings.API_V1_PREFIX}/projects/{project_id}/media",
            files={"file": (filename, source.read_bytes(), "video/mp4")},
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text
        return await _wait_for_media(client, project_id, response.json()["id"], auth_headers)

    reference = await upload("reference.mp4")
    raw = await upload("raw.mp4")
    assert reference["duration"] == pytest.approx(2.0, abs=0.2)
    assert raw["width"] == 160
    assert raw["height"] == 90

    clone_response = await client.post(
        f"{settings.API_V1_PREFIX}/templates/projects/{project_id}/clone",
        json={
            "reference_media_id": reference["id"],
            "raw_media_ids": [raw["id"]],
        },
        headers=auth_headers,
    )
    assert clone_response.status_code == 200, clone_response.text
    clone_payload = clone_response.json()
    timeline_id = clone_payload["timeline_id"]
    clip = clone_payload["timeline"]["tracks"][0]["clips"][0]
    raw_asset = await db_session.get(MediaAsset, UUID(raw["id"]))
    assert raw_asset is not None
    assert clip["source"]["media_asset_id"] == raw["id"]
    assert clip["source"]["storage_key"] == raw_asset.storage_key

    preview_preset = RenderPreset(
        name="Preview (Fast)",
        platform=RenderPresetPlatform.CUSTOM,
        width=160,
        height=90,
        fps=24,
        video_codec="libx264",
        crf=35,
        preset="ultrafast",
        audio_codec="aac",
        audio_bitrate="64k",
        pixel_format="yuv420p",
        container="mp4",
        is_default=True,
    )
    preset = RenderPreset(
        name="Isolated Export",
        platform=RenderPresetPlatform.CUSTOM,
        width=160,
        height=90,
        fps=24,
        video_codec="libx264",
        crf=35,
        preset="ultrafast",
        audio_codec="aac",
        audio_bitrate="64k",
        pixel_format="yuv420p",
        container="mp4",
        is_default=False,
    )
    db_session.add_all([preview_preset, preset])
    await db_session.commit()
    await db_session.refresh(preset)

    async def render(path: str, body: dict | None = None) -> dict:
        response = await client.post(
            f"{settings.API_V1_PREFIX}/rendering/projects/{project_id}/timelines/{timeline_id}/{path}",
            json=body,
            headers=auth_headers,
        )
        assert response.status_code == 202, response.text
        return await _wait_for_render(client, project_id, response.json()["render_job_id"], auth_headers)

    preview = await render("preview")
    export = await render("export", {"preset_id": str(preset.id)})
    for job in (preview, export):
        assert job["output_size"] > 0
        assert job["duration"] == pytest.approx(2.0, abs=0.2)
        download = await client.get(
            f"{settings.API_V1_PREFIX}/rendering/projects/{project_id}/renders/{job['id']}/download",
            headers=auth_headers,
        )
        assert download.status_code == 200, download.text
        output = tmp_path / f"{job['id']}.mp4"
        output.write_bytes(download.content)
        probe = subprocess.run(
            [FFPROBE, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(output)],
            check=True,
            capture_output=True,
            text=True,
        )
        metadata = json.loads(probe.stdout)
        video_stream = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
        assert int(video_stream["width"]) == job["width"]
        assert int(video_stream["height"]) == job["height"]
