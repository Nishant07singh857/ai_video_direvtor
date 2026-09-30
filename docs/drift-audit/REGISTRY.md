# Codebase Drift Audit Registry

## 1. Frontend UI vs Application State Drift
**Issue:** Advanced NLE workspace components are fully built but entirely unlinked from the main application view.
**Details:** 
- The project has a comprehensive suite of Non-Linear Editor (NLE) React components in `frontend/src/components/`, including `NLEWorkspace.tsx`, `AudioMixer.tsx`, `LumetriPanel.tsx`, `TransformPanel.tsx`, `EffectsPanel.tsx`, `EssentialGraphicsPanel.tsx`, and more.
- However, the main project entry point (`frontend/src/app/projects/[id]/page.tsx`) implements a basic Next.js dashboard using simple Card components. It completely ignores the `NLEWorkspace` layout and bypasses all the advanced editing panels, leaving them as dead code. The "Video Preview" area is hardcoded with a disabled state and placeholder text.

## 2. Backend Services Logic Mismatch (Dead Code)
**Issue:** Core AI and media processing services are implemented but never invoked by API routes or background workers.
**Details:**
- The following services in `backend/app/services/` are completely unused and structurally disconnected:
  - `ai_critic.py`
  - `ai_memory.py`
  - `ai_provider.py`
  - `audio_engine.py`
  - `auto_director.py`
  - `dataset_builder.py`
  - `link_extractor.py`
  - `model_training.py`
  - `social_ai.py`
- This indicates a severe structural drift where advanced features (like AI critic, automated dataset building, and social media integrations) were built but never wired into the actual execution paths (FastAPI routers).

## 3. Database Models Drift
**Issue:** Unused database schemas.
**Details:**
- Several database models in `backend/app/models/` are defined but never queried or referenced in the application layer. These include:
  - `billing.py`
  - `collaboration.py`
  - `compositing.py`
  - `image_editing.py`
  - `media_management.py`
  - `multicam.py`
  - `project_management.py`
  - `screenplay.py`
- These models suggest planned features that have not been implemented at the API/Service level or were abandoned, causing schema drift.

## 4. Video Engine Architecture Drift
**Issue:** The `video_engine` module is largely a skeleton, failing to centralize media logic.
**Details:**
- While `video_engine/rendering/` contains actual implementation logic (e.g., `ffmpeg_renderer.py`, `export.py`), other crucial architectural modules like `video_engine/audio/`, `video_engine/ingestion/`, `video_engine/shots/`, and `video_engine/timeline/` contain only empty `__init__.py` files.
- The system heavily relies on `backend/app/services` for logic that should theoretically reside in the `video_engine` package, representing an architectural mismatch.
