import pytest
from httpx import AsyncClient
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import RenderJob, RenderJobStatus, RenderJobType, Timeline, RenderPreset

@pytest.fixture
async def sample_project(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Render Test Project", "description": "test"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()

@pytest.fixture
async def sample_timeline(client: AsyncClient, auth_headers: dict, sample_project, db_session: AsyncSession):
    # Ensure RenderPreset exists
    from app.models import RenderPreset, RenderPresetPlatform
    from sqlalchemy import select
    result = await db_session.execute(select(RenderPreset).where(RenderPreset.name == "Preview (Fast)"))
    if not result.scalar_one_or_none():
        preset = RenderPreset(
            name="Preview (Fast)",
            platform=RenderPresetPlatform.GENERIC,
            width=640,
            height=360,
            fps=30,
            video_codec="libx264",
            video_bitrate="1M",
            crf=28,
            preset="ultrafast",
            audio_codec="aac",
            audio_bitrate="128k",
            pixel_format="yuv420p",
            container="mp4",
            is_default=True
        )
        db_session.add(preset)
        await db_session.commit()

    project_id = sample_project["id"]
    resp = await client.post(
        f"/api/v1/projects/{project_id}/timelines",
        json={"name": "Render Timeline", "resolution_width": 1920, "resolution_height": 1080, "fps": 30.0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()

async def test_list_render_presets(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/rendering/render-presets", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "presets" in data
    assert isinstance(data["presets"], list)

async def test_get_nonexistent_preset(client: AsyncClient, auth_headers: dict):
    random_id = str(uuid4())
    response = await client.get(f"/api/v1/rendering/render-presets/{random_id}", headers=auth_headers)
    assert response.status_code == 404

async def test_preview_render(client: AsyncClient, auth_headers: dict, sample_project, sample_timeline):
    project_id = sample_project["id"]
    timeline_id = sample_timeline["id"]
    
    # Start preview
    resp = await client.post(
        f"/api/v1/rendering/projects/{project_id}/timelines/{timeline_id}/preview",
        headers=auth_headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "render_job_id" in data
    assert data["status"] == "queued"
    job_id = data["render_job_id"]
    
    # Check job status
    status_resp = await client.get(
        f"/api/v1/rendering/projects/{project_id}/renders/{job_id}",
        headers=auth_headers,
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["id"] == job_id
    assert status_data["job_type"] == "preview"
    
    # List jobs
    list_resp = await client.get(
        f"/api/v1/rendering/projects/{project_id}/renders",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(j["id"] == job_id for j in list_data["renders"])
    
    # Cancel job
    cancel_resp = await client.delete(
        f"/api/v1/rendering/projects/{project_id}/renders/{job_id}",
        headers=auth_headers,
    )
    assert cancel_resp.status_code in (200, 400)

async def test_export_render_missing_preset(client: AsyncClient, auth_headers: dict, sample_project, sample_timeline):
    project_id = sample_project["id"]
    timeline_id = sample_timeline["id"]
    
    # For export render, preset_id can be optional but if default not found it might fail or pick default
    # If preset_id not provided and no default exists, let's see what happens.
    # We will provide an invalid preset just to test failure.
    invalid_preset = str(uuid4())
    resp = await client.post(
        f"/api/v1/rendering/projects/{project_id}/timelines/{timeline_id}/export?preset_id={invalid_preset}",
        headers=auth_headers,
    )
    # The service returns 400 with "Render preset not found"
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"].lower()
