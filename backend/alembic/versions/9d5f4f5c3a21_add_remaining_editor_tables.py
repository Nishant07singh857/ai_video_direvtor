"""Add the editor, collaboration, review, and template tables.

Revision ID: 9d5f4f5c3a21
Revises: 57d207bfe42c
Create Date: 2026-09-29

The first production migrations covered authentication, media analysis,
AI-director timelines, and rendering.  The application models also contain
the durable editor subsystems that were previously only created by local
``Base.metadata.create_all`` calls.  This revision brings those mapped tables
into the migration chain without dropping or rewriting any existing table.
"""

from typing import Sequence, Union

from alembic import context, op
from sqlalchemy import inspect

from app.core.database import Base
import app.models  # noqa: F401 - register the mapped tables


revision: str = "9d5f4f5c3a21"
down_revision: Union[str, None] = "57d207bfe42c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Frozen names for this revision.  Keeping this allow-list prevents a future
# model added to the application from being silently created by an old
# migration.
REMAINING_TABLES = frozenset(
    {
        "media_tags",
        "model_registry",
        "notifications",
        "user_preferences",
        "ai_error_events",
        "editor_decision_patterns",
        "media_bins",
        "multicam_sequences",
        "review_comments",
        "review_links",
        "screenplays",
        "characters",
        "error_to_learning_pipeline",
        "media_asset_tags",
        "media_bin_assets",
        "media_markers",
        "multicam_angles",
        "proxy_media",
        "scenes",
        "style_clones",
        "video_templates",
        "clip_compositing",
        "collaborator_cursors",
        "dialogue_lines",
        "edit_operations",
        "effects",
        "graphics_layers",
        "image_on_timeline",
        "project_locks",
        "render_cache",
        "takes",
        "color_adjustments",
    }
)


def upgrade() -> None:
    """Create only the tables introduced by this revision, in FK order."""
    bind = op.get_bind()
    existing = set() if context.is_offline_mode() else set(inspect(bind).get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name in REMAINING_TABLES and table.name not in existing:
            table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    """Drop only tables owned by this revision, in reverse FK order."""
    bind = op.get_bind()
    existing = set(REMAINING_TABLES) if context.is_offline_mode() else set(inspect(bind).get_table_names())
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in REMAINING_TABLES and table.name in existing:
            table.drop(bind=bind, checkfirst=True)
