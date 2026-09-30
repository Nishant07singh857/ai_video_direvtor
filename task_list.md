# AI Video Director Project Task List

## 1. Frontend UI vs Application State Drift
- [x] Update `frontend/src/app/projects/[id]/page.tsx` to use the `NLEWorkspace` layout.
- [x] Connect editing panels (`AudioMixer`, `LumetriPanel`, etc.) to the application state.

## 2. Backend Services Logic Mismatch
- [x] Wire `backend/app/services/ai_critic.py` to API routes.
- [x] Wire `backend/app/services/ai_memory.py` to API routes.
- [x] Wire `backend/app/services/ai_provider.py` to API routes.
- [x] Wire `backend/app/services/audio_engine.py` to API routes.
- [x] Wire `backend/app/services/auto_director.py` to API routes.
- [x] Wire `backend/app/services/dataset_builder.py` to API routes.
- [x] Wire `backend/app/services/link_extractor.py` to API routes.
- [x] Wire `backend/app/services/model_training.py` to API routes.
- [x] Wire `backend/app/services/social_ai.py` to API routes.

## 3. Database Models Drift
- [x] Integrate unused models into API routes and services (`billing`, `collaboration`, `compositing`, `image_editing`, `media_management`, `multicam`, `project_management`, `screenplay`).

## 4. Video Engine Architecture Drift
- [x] Populate `video_engine/audio/` with audio logic.
- [x] Populate `video_engine/ingestion/` with ingestion logic.
- [x] Populate `video_engine/shots/` with shots logic.
- [x] Populate `video_engine/timeline/` with timeline logic.
- [x] Refactor logic from `backend/app/services` into `video_engine` where appropriate.
