"""Regression tests for the canonical editor and template contracts."""

from __future__ import annotations

from app.core.config import settings
from app.core.timeline import normalize_timeline, validate_timeline
from app.models import MediaAsset, MediaStatus, Project
from app.models.template import VideoTemplate


def test_legacy_clip_shape_normalizes_to_renderer_shape() -> None:
    timeline = normalize_timeline(
        {
            "clips": [
                {
                    "id": "legacy-1",
                    "source": {"media_asset_id": "asset-1", "storage_key": "projects/p/raw.mp4"},
                    "start": 0,
                    "end": 2,
                }
            ]
        }
    )
    assert timeline["schema"] == "ai-video-director-timeline-v1"
    assert timeline["tracks"][0]["clips"][0]["timeline_duration"] == 2.0
    assert not validate_timeline(timeline)


async def test_timeline_update_uses_optimistic_version(client, auth_headers):
    project_response = await client.post(
        f"{settings.API_V1_PREFIX}/projects",
        json={"name": "Contract Project"},
        headers=auth_headers,
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    timeline_response = await client.post(
        f"{settings.API_V1_PREFIX}/projects/{project_id}/timelines",
        json={"name": "Contract Timeline"},
        headers=auth_headers,
    )
    assert timeline_response.status_code == 201
    timeline = timeline_response.json()

    stale = await client.patch(
        f"{settings.API_V1_PREFIX}/projects/{project_id}/timelines/{timeline['id']}",
        json={"expected_version": 0, "color_settings": {"saturation": 10}},
        headers=auth_headers,
    )
    assert stale.status_code == 409

    updated = await client.patch(
        f"{settings.API_V1_PREFIX}/projects/{project_id}/timelines/{timeline['id']}",
        json={"expected_version": 1, "color_settings": {"saturation": 10}},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["version_number"] == 2
    assert "expected_version" not in updated.json()["timeline_json"]


async def test_saved_template_apply_persists_project_timeline(
    client,
    auth_headers,
    test_user,
    db_session,
):
    project = Project(user_id=test_user.id, name="Template Project")
    db_session.add(project)
    await db_session.flush()
    asset = MediaAsset(
        project_id=project.id,
        original_filename="raw.mp4",
        storage_key=f"projects/{project.id}/raw.mp4",
        media_type="video",
        mime_type="video/mp4",
        file_size=100,
        checksum="a" * 64,
        duration=2.0,
        width=320,
        height=180,
        fps=30,
        status=MediaStatus.READY,
    )
    template = VideoTemplate(
        name="Public Beat Template",
        description="test",
        beatmap=[0.0, 1.0],
        media_slots=[{"slot_index": 0, "duration": 1.0, "target_theme": "general"}],
        global_effects={},
        is_public=True,
    )
    db_session.add_all([asset, template])
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(asset)
    await db_session.refresh(template)

    response = await client.post(
        f"{settings.API_V1_PREFIX}/templates/projects/{project.id}/apply",
        json={"template_id": str(template.id), "raw_media_ids": [str(asset.id)]},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["timeline_id"]
    clip = payload["timeline"]["tracks"][0]["clips"][0]
    assert clip["source"]["media_asset_id"] == str(asset.id)
    assert clip["source"]["storage_key"] == asset.storage_key
