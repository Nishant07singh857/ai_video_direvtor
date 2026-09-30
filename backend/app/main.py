import sys
from contextlib import asynccontextmanager
from pathlib import Path
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _ROOT_DIR / "backend"
for _path in [str(_ROOT_DIR), str(_BACKEND_DIR)]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
import logging
from app.api import styles, rlhf

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run safe idempotent startup work and keep shutdown explicit."""
    try:
        from app.services.render_presets import ensure_default_render_presets
        await ensure_default_render_presets()
    except Exception as exc:
        # Migrations may run after the API container starts.  Do not hide the
        # failure; keep health endpoints available and let the operator see it.
        logger.warning("render preset seeding skipped: %s", exc)
    yield


app = FastAPI(title="AI Video Director API", version="1.0.0", lifespan=lifespan)



ALLOWED_ORIGINS = settings.cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Range"],
)

from app.api import billing
from app.api import collaboration
from app.api import compositing
from app.api import image_editing
from app.api import media_management
from app.api import multicam
from app.api import project_management
from app.api import screenplay
from app.api import admin, ai_director, analysis, editing, health, media, projects, rendering, search, styles, templates, rlhf, ai_critic, ai_memory, dataset_builder, ai_provider, audio_engine, auto_director, link_extractor, model_training, social_ai

# Include all core routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(projects.router, prefix="/api/v1", tags=["Projects"])
app.include_router(media.router, prefix="/api/v1", tags=["Media"])
app.include_router(editing.router, prefix="/api/v1", tags=["Editing"])
app.include_router(rendering.router, prefix="/api/v1/rendering", tags=["Rendering"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(templates.router, prefix="/api/v1/templates", tags=["Templates"])
app.include_router(styles.router, prefix="/api/v1", tags=["Styles"])
app.include_router(rlhf.router, prefix="/api/v1/rlhf", tags=["Continuous Learning"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(ai_director.router, prefix="/api/v1", tags=["AI Director"])
app.include_router(ai_critic.router, prefix="/api/v1/ai-critic", tags=["AI Critic"])
app.include_router(ai_memory.router, prefix="/api/v1/ai-memory", tags=["AI Memory"])
app.include_router(dataset_builder.router, prefix="/api/v1/dataset-builder", tags=["Dataset Builder"])
app.include_router(ai_provider.router, prefix="/api/v1/ai-provider", tags=["AI Provider"])
app.include_router(audio_engine.router, prefix="/api/v1/audio-engine", tags=["Audio Engine"])
app.include_router(auto_director.router, prefix="/api/v1/auto-director", tags=["Auto Director"])
app.include_router(link_extractor.router, prefix="/api/v1/link-extractor", tags=["Link Extractor"])
app.include_router(model_training.router, prefix="/api/v1/model-training", tags=["Model Training"])
app.include_router(social_ai.router, prefix="/api/v1/social-ai", tags=["Social AI"])

app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])

app.include_router(collaboration.router, prefix="/api/v1/collaboration", tags=["Collaboration"])

app.include_router(compositing.router, prefix="/api/v1/compositing", tags=["Compositing"])

app.include_router(image_editing.router, prefix="/api/v1/image-editing", tags=["Image Editing"])

app.include_router(media_management.router, prefix="/api/v1/media-management", tags=["Media Management"])

app.include_router(multicam.router, prefix="/api/v1/multicam", tags=["Multicam"])

app.include_router(project_management.router, prefix="/api/v1/project-management", tags=["Project Management"])

app.include_router(screenplay.router, prefix="/api/v1/screenplay", tags=["Screenplay"])

@app.get("/")
def root():
    return {"status": "ok", "message": "AI Video Director Engine Running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}


