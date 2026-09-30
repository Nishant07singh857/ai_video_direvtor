# AI Video Director ? Deep Project Audit
**Audit date:** 2026-09-29  
**Root:** `D:/ai-video-director`  
**Mode:** read-only deep scan; no source, data, dependency, database, or media files were deleted or modified.
## 1. Executive verdict
The repository is a large prototype/partial platform, not yet a verified enterprise NLE. It has real FastAPI, SQLAlchemy, Next.js, FFmpeg and deterministic analysis/rendering code, but the end-to-end workflow is broken across multiple contracts. The highest-risk problems are: three Python syntax errors, broken analysis/AI imports, rendering API path and timeline-shape mismatches, unauthenticated media/search surfaces, incomplete storage, mock/scaffold features presented as product features, and a 3.22 GB workspace dominated by generated/dependency/data artifacts.
**Deletion decision:** no automatic cleanup was performed because ?unwanted? was not specific enough to safely delete user media, training data, databases, environments, graph artifacts, or historical scripts. A cleanup candidate list is included in Section 9.
## 2. Scan coverage and limits
- Full filesystem inventory: **29,668 files / 3,221,015,281 bytes (~3.22 GB)**.
- Non-generated/source-oriented inventory: **995 files / 2,660,649,581 bytes**.
- Project-owned Python/TS/JS source index below: **207 files**.
- `frontend/node_modules`, `backend/.venv`, `.next`, caches, binaries, videos, databases, uploads, and training datasets were inventoried but not semantically reviewed line-by-line; they are classified by type/size instead. Reviewing every vendor/generated/data byte would not identify project defects and would risk exposing or deleting user data.
## 3. Inventory by top-level area
- `.agents/` ? 282 files; 3,951,243 bytes.
- `.claude/` ? 12 files; 89,365 bytes.
- `.git/` ? 18 files; 27,254 bytes.
- `.pytest_cache/` ? 5 files; 1,237 bytes.
- `__pycache__/` ? 1 files; 412 bytes.
- `ai/` ? 0 files; 0 bytes.
- `backend/` ? 6,988 files; 142,133,969 bytes.
- `data/` ? 0 files; 0 bytes.
- `database/` ? 0 files; 0 bytes.
- `docker/` ? 5 files; 4,355 bytes.
- `docs/` ? 15 files; 143,147 bytes.
- `frontend/` ? 21,986 files; 458,740,642 bytes.
- `graphify-out/` ? 202 files; 6,824,471 bytes.
- `llm_training/` ? 3 files; 9,175 bytes.
- `media/` ? 2 files; 7,301,644 bytes.
- `models/` ? 0 files; 0 bytes.
- `tests/` ? 1 files; 227 bytes.
- `training/` ? 0 files; 0 bytes.
- `training_data/` ? 22 files; 2,431,421,160 bytes.
- `uploads/` ? 8 files; 25,719,322 bytes.
- `video_engine/` ? 61 files; 575,181 bytes.
- `workers/` ? 0 files; 0 bytes.
## 4. Direct verification results
- Python AST scan: **177 Python files inspected; 3 syntax errors; 96 `pass`/ellipsis stubs; 87 broad `except Exception`/bare exception handlers.**
- Runtime import smoke test using the canonical `app.*` package: **111 modules imported; 3 failed** ? `app.services.evaluation` (empty class body), `app.services.safety` (empty class body), `app.services.transcript_editor` (`List` undefined).
- Frontend TypeScript check: **passed** (`tsc --noEmit`; also independently confirmed by the frontend audit).
- Frontend lint: **completed with one warning**: `frontend/src/components/timeline/Clip.tsx:49`, `aria-selected` unsupported for role `button`.
- Backend mypy: **not completed**; the installed mypy executable was blocked by Windows Application Control while importing its mypyc DLL. This is an environment/tooling blocker, not evidence of clean typing.
- Rendering tests: the targeted test run collected four tests, printed `..`, then timed out during the preview path; earlier direct FFmpeg component verification succeeded only with a valid fixture, not the full application workflow.
- Existing historical audit documents were compared with current source. Some are stale: for example, the old frontend audit says timelines are never fetched, but current `projects/[id]/page.tsx` does call `fetchTimelines()`.

## 5. Feature availability matrix

| Capability | Current status | Evidence / reason |
|---|---|---|
| Foundation/auth/project CRUD | PARTIAL | Auth, projects and ownership routes exist; production auth/security defaults are unsafe; inactive-user checks and secure-cookie model are missing. `backend/app/api/projects.py; backend/app/core/config.py` |
| Media ingestion/storage | PARTIAL/BROKEN | Upload/list/read/stream exist; LocalStorage save/delete/get_url are stubs, media delete calls missing delete_file, MIME validation trusts extensions, image/audio/resumable/proxy/relink flows are absent. `backend/app/api/media.py; backend/app/services/storage/__init__.py` |
| Media analysis | BROKEN/UNVERIFIED | Shot, scene, keyframe, audio and speech code exists, but MediaAnalysisService has missing imports/factories and swallowed errors. `backend/app/services/media_analysis.py; backend/app/services/analysis_job.py` |
| AI Director/story/ranking | PARTIAL/BROKEN | Deterministic story/ranking/sequence services exist but several imports are missing; public pipeline invokes swarm path, ignores timeline result and reports success with empty stages. `backend/app/services/ai_director.py; backend/app/services/swarm_orchestrator.py` |
| Knowledge graph/embeddings/search | BROKEN/PARTIAL | Knowledge graph implementation is present but missing imports; semantic search route calls a nonexistent embedding method and lacks auth/project isolation. `backend/app/services/knowledge_graph.py; backend/app/api/search.py` |
| Timeline/NLE editing | PARTIAL/LOCAL-ONLY | Timeline UI and a small set of backend operations exist; drag/edit state is not persisted as operations, AI and UI timeline schemas disagree, professional edit modes are missing. `frontend/src/components/timeline; backend/app/api/editing.py` |
| Rendering/FFmpeg | PARTIAL/BLOCKED | Compiler/renderer/API/tasks exist; presets are empty in the current DB, queue is unavailable, render validation is not strict, cancel/progress/retry are incomplete, and export model fields mismatch. `backend/app/api/rendering.py; video_engine/rendering; backend/app/models/rendering.py` |
| Audio/color/effects/graphics | PARTIAL/UNWIRED | Controls and some FFmpeg filters exist; most panels keep local state or use placeholders and AI timeline output does not inject supported effects/graphics consistently. `frontend/src/components/audio/color/effects/graphics; video_engine/rendering/timeline_to_ffmpeg.py` |
| Transcript editing | ORPHANED/BROKEN | Transcript component/service exist; component is not mounted, service lacks typing imports, no end-to-end transcript-to-timeline flow. `frontend/src/components/transcript; backend/app/services/transcript_editor.py` |
| Multicam/screenplay/interchange | SCAFFOLD | Models/components/routes exist but are not integrated; no verified workflow. `backend/app/models; frontend/src/components/film; frontend/src/components/multicam; frontend/src/components/project/ExportInterchangeModal.tsx` |
| Critic/revision/approval/collaboration | SCAFFOLD/MOCK | Backend service/model scaffolds exist; review/share/comments are local or fake and not connected to approval workflow. `backend/app/services; frontend/src/components/review` |
| Learning/dataset/model training | MOCK/UNWIRED | Endpoints/services exist, but dataset extraction and model training are hard-coded/log-only; no gated production workflow. `backend/app/services/dataset_builder.py; backend/app/services/model_training.py` |
| Deployment/observability/security | INCOMPLETE | Docker/config files exist but production paths are inconsistent, worker container is missing, secrets/debug defaults remain, and rate limiting/audit/signed URLs/privacy controls are absent. `docker; docker-compose.prod.yml; backend/app/core; backend/app/api` |

## 6. High-confidence defects and type/runtime failures
- **P0 ? Python syntax failure.** `backend/app/services/evaluation.py:1` contains only `class AIEvaluator:` with no indented body; `backend/app/services/safety.py:7` has the same empty-class syntax failure; root `script.py` contains NUL bytes. Evidence: These files cannot be imported or used.
- **P0 ? Analysis service missing symbols.** `backend/app/services/media_analysis.py:26-29,37-55,66-72,105-113,161-169,222-263,308-329` uses missing factories/models/enums; `analysis_job.py:34,69-72,83,98,112,131` uses missing `AnalysisStatus`. Evidence: Phase 3 analysis cannot be trusted.
- **P0 ? AI Director stages broken/bypassed.** `knowledge_graph.py:21-29,78-101`, `shot_ranker.py:57-59`, `story_generator.py:62-112,157-169`, `story_ranker.py:47-59`, and `sequence_planner.py:38-40,70-101` reference missing imports. `ai_director.py:78-112` uses the swarm path, ignores the generated timeline result, returns empty stages and success. Evidence: The advertised analysis?story?timeline path is not verified.
- **P0 ? Rendering contract mismatch.** `frontend/src/lib/api.ts:156-181` calls `/api/v1/projects` and `/api/v1/render-presets`; backend mounts rendering under `/api/v1/rendering` at `backend/app/main.py:47`. Evidence: Frontend render requests hit wrong routes.
- **P0 ? Timeline schema mismatch.** `video_engine/timeline/builder.py:51-83` emits `tracks[].clips[]`; project UI reads `timeline_json.clips[]` at `frontend/src/app/projects/[id]/page.tsx:200-220`; current DB timelines contain top-level mock clips with no source keys. Evidence: AI timelines cannot reliably display or render.
- **P0 ? Storage and media deletion broken.** `backend/app/services/storage/__init__.py:81-86` leaves LocalStorage methods as ellipses; `backend/app/api/media.py:323-332` calls missing `delete_file`. Evidence: File lifecycle is incomplete.
- **P0 ? Security: unauthenticated media/search.** `backend/app/api/media.py:279-311` allows streaming without ownership enforcement; `backend/app/api/search.py:31-75` has no auth/project isolation. Evidence: Cross-user data exposure is possible.
- **P1 ? Export model mismatch.** `backend/app/services/export_service.py:187-196` reads preset fields absent from `backend/app/models/rendering.py:85-106`. Evidence: Export execution will fail once that branch is reached.
- **P1 ? Worker/runtime defects.** `backend/app/workers/render_tasks.py:225-233` uses `select` outside its local import; retry count is not tracked. Cancellation only changes DB state and does not stop FFmpeg. Evidence: Queue reliability is not production-ready.
- **P1 ? Search service missing method.** `backend/app/api/search.py:41-49` calls `embed_text_query()`, but `backend/app/services/video_intelligence.py` defines no such method. Evidence: Semantic search route is broken.
- **P1 ? Transcript editor import failure.** `backend/app/services/transcript_editor.py:14-18` annotates `List`, `Dict`, `Optional` without importing them; import smoke test confirms `NameError`. Evidence: Transcript editing cannot import.
- **P1 ? Docker topology mismatch.** `docker-compose.prod.yml:4-24` references missing `backend/Dockerfile` and `workers/Dockerfile`; root `workers/` is empty. `docker/Dockerfile.backend:16-19` copies only backend although services import root `video_engine`. Evidence: Production container workflow is not reproducible.
- **P1 ? Database/migration drift.** Migrations cover only selected phases; models in `backend/app/models/__init__.py:7-24` require many additional tables. Alembic uses sync PostgreSQL but `psycopg2` is not installed. Evidence: Fresh database setup is not reliable.
- **P2 ? Frontend persistence gaps.** Timeline drag operations mutate local state at `frontend/src/components/timeline/Timeline.tsx:53-77`; project page supplies no persistence callback at `:545-551`. Evidence: Edits disappear after refresh and do not become structured operations.
- **P2 ? Mocks/placeholders.** Examples: `TemplateLibrary.tsx:10-15`, `HistoryPanel.tsx:10-18`, `CommentPanel.tsx:17-26`, `ShareModal.tsx:27-35`, backend model training `backend/app/services/model_training.py:11-30`, dataset builder `:14-20`. Evidence: These are not completed product features.

## 7. Dead, orphaned, or unwired code
### Frontend orphan components
- `frontend/src/components/film/ScreenplayPanel.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/media/ImageProperties.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/media/ProjectBin.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/multicam/AngleViewer.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/project/ExportInterchangeModal.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/project/HistoryPanel.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/rendering/ExportModal.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/rendering/RenderJobList.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/rendering/RenderPanel.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/rendering/VideoPreview.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/review/CommentPanel.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/review/ShareModal.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/styles/StyleClonerModal.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/templates/TemplateLibrary.tsx` ? declared but not imported/rendered by the current application.
- `frontend/src/components/transcript/TranscriptPanel.tsx` ? declared but not imported/rendered by the current application.
### Backend/service orphan or scaffold areas
- `backend/app/services/evaluation.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/safety.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/billing_service.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/collaboration_service.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/compositing_service.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/image_editing_service.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/media_management_service.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/multicam_service.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/project_management_service.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/screenplay_service.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/model_training.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/dataset_builder.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/social_ai.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
- `backend/app/services/video_intelligence.py` ? present but empty/scaffolded, mock-only, or not connected to a verified user workflow.
### Render/effects code that is currently stranded
- `video_engine/rendering/timeline_to_ffmpeg.py` contains filters for blur, sharpen, speed, chroma key, blend modes, text and audio ducking, but current swarm output does not consistently emit the required structured fields.
- `backend/app/services/ai_director.py` and `backend/app/services/swarm_orchestrator.py` represent overlapping orchestration paths; the public route uses the path that produces the incompatible top-level clip shape.
- `frontend/scan.js` is a source-mutating ad-hoc fixer and should not be treated as a normal application module.

## 8. Missing product capabilities
- Production-safe auth: HTTP-only cookies, inactive-user enforcement, rate limiting, audit logs, signed URLs, malware scanning, secret rotation and privacy/data deletion controls.
- Reliable ingestion: audio/images, multi-file/resumable uploads, real MIME probing, proxies, offline detection, relinking, object storage and cleanup.
- Verified media intelligence: working shot/scene/keyframe/audio/speech pipeline with persisted job state and no swallowed errors.
- Canonical timeline contract shared by AI, API, UI, edit operations and renderer.
- Professional NLE: ripple/roll/slip/slide/extend/replace/insert/overwrite/lift/extract, snapping, track lock/mute/solo, source/program monitor, J/K/L playback, undo/redo and durable version history.
- AI critic and approval-gated revision loop with issue timestamps, severity, confidence and real render/critic iterations.
- Transcript editing, semantic vector search, speaker labels and transcript-to-timeline mapping.
- Pro audio/color/VFX/motion/multicam/interchange workflows wired to durable timeline data.
- Collaboration/review organizations, roles, comments, mentions, approvals, review links and conflict-safe versioning.
- Production dataset/model-training governance with real data extraction, quality filters, benchmark, shadow deployment and rollback.
- CI/CD, frontend tests, backend integration tests, worker tests, render/FFprobe E2E, security/performance tests and reproducible Docker builds.

## 9. Cleanup candidates ? nothing deleted

| Candidate | Size / count | Risk | Recommendation |
|---|---:|---|---|
| `frontend/node_modules` | 335,897,792 bytes / 21,830 files | regenerable dependency tree | delete only if reinstall is acceptable |
| `frontend/.next` | 122,256,399 bytes / 95 files | regenerable build output | safe to regenerate; delete with confirmation |
| `backend/.venv` | 100,154,921 bytes / 6,436 files | regenerable Python environment | delete only if environment can be recreated |
| `backend/.mypy_cache` | 262,373 bytes / 18 files | cache | safe cache candidate |
| `backend/__pycache__` | 28,221 bytes / 2 files | cache | safe cache candidate |
| `backend/.pytest_cache` | 1,918 bytes / 6 files | cache | safe cache candidate |
| `frontend/tsconfig.tsbuildinfo` | 115,293 bytes / 1 files | incremental compiler cache | safe cache candidate |
| `backend/.coverage` | 69,632 bytes / 1 files | coverage output | safe generated artifact |
| `graphify-out` | 6,824,471 bytes / 202 files | generated graph/report artifacts; may be useful | do not delete automatically |
| `training_data` | 2,431,421,160 bytes / 22 files | large project data (2.43 GB) | do not delete without explicit confirmation |
| `backend/media` | 37,890,524 bytes / 128 files | user/project media | do not delete |
| `uploads` | 25,719,322 bytes / 8 files | user/project uploads | do not delete |
| `*.db / *.db-journal` | not measured | runtime/test databases | do not delete without selecting exact files |
| `frontend/scan.js` | 3,079 bytes / 1 files | source-mutating ad-hoc script | review/archive, do not delete automatically |
| `root/backend fix_*/check_*/scan_* scripts` | not measured | historical operational scripts | review individually, do not bulk delete |

**Recommended first cleanup batch (after confirmation):** only regenerable caches/build outputs: `frontend/.next`, `frontend/tsconfig.tsbuildinfo`, `backend/.mypy_cache`, `backend/__pycache__`, `backend/.pytest_cache`, `backend/.coverage`, and optionally `frontend/node_modules`/`backend/.venv` if reinstalling dependencies is acceptable. Do not bulk-delete `training_data`, `uploads`, `backend/media`, databases, test media, or `graphify-out`.

## 10. One-line source index

The following index covers every project-owned Python/TypeScript/JavaScript source file in the scan scope. Vendor/dependency/data files are covered by inventory and cleanup classification above.

### Python
- `audit_script.py` ? 81 lines; symbols: compute_complexity, check_file, main; flags: broad-except, pass; parse: OK.
- `auto_qa.py` ? 84 lines; symbols: fix_imports, monitor; flags: none; parse: OK.
- `backend/alembic/env.py` ? 50 lines; symbols: run_migrations_offline, do_run_migrations, run_migrations_online; flags: none; parse: OK.
- `backend/alembic/versions/033a1cec32b5_add_phase_4_ai_director_models.py` ? 161 lines; symbols: upgrade, downgrade; flags: none; parse: OK.
- `backend/alembic/versions/57d207bfe42c_add_rendering_models.py` ? 184 lines; symbols: upgrade, downgrade; flags: none; parse: OK.
- `backend/alembic/versions/7bb77d957101_add_media_assets_table.py` ? 56 lines; symbols: upgrade, downgrade; flags: none; parse: OK.
- `backend/alembic/versions/8feb8cc1f2a4_initial_migration.py` ? 66 lines; symbols: upgrade, downgrade; flags: none; parse: OK.
- `backend/alembic/versions/b8ecd21e1b00_add_analysis_models.py` ? 152 lines; symbols: upgrade, downgrade; flags: none; parse: OK.
- `backend/app/api/admin.py` ? 14 lines; symbols: get_system_stats; flags: none; parse: OK.
- `backend/app/api/ai_critic.py` ? 18 lines; symbols: TimelineRequest, analyze_timeline; flags: broad-except; parse: OK.
- `backend/app/api/ai_director.py` ? 312 lines; symbols: AIDirectorAnalyzeRequest, run_ai_director, get_ai_director_status, AIPromptEditRequest, edit_with_ai_prompt, get_vision_analysis; flags: broad-except, pass; parse: OK.
- `backend/app/api/ai_memory.py` ? 19 lines; symbols: MemoryFailureRequest, analyze_failure; flags: broad-except; parse: OK.
- `backend/app/api/ai_provider.py` ? 31 lines; symbols: TextPrompt, VisionPrompt, AudioPrompt, generate_text, analyze_vision, process_audio; flags: none; parse: OK.
- `backend/app/api/analysis.py` ? 470 lines; symbols: get_current_user, get_media_asset, start_analysis, get_analysis_status, get_analysis_results, get_shots, get_shot, get_scenes, get_scene, get_keyframes, get_transcript, get_audio_analysis; flags: none; parse: OK.
- `backend/app/api/audio_engine.py` ? 14 lines; symbols: get_config; flags: none; parse: OK.
- `backend/app/api/auto_director.py` ? 9 lines; symbols: get_status; flags: none; parse: OK.
- `backend/app/api/billing.py` ? 11 lines; symbols: get_billing_info; flags: none; parse: OK.
- `backend/app/api/collaboration.py` ? 11 lines; symbols: get_collaboration_info; flags: none; parse: OK.
- `backend/app/api/compositing.py` ? 11 lines; symbols: get_compositing_info; flags: none; parse: OK.
- `backend/app/api/dataset_builder.py` ? 26 lines; symbols: ExportRequest, extract_decisions, export_dataset; flags: broad-except; parse: OK.
- `backend/app/api/editing.py` ? 331 lines; symbols: apply_edit_to_timeline, get_timeline, list_timelines, get_timeline_endpoint, update_timeline, TimelineCreate, create_timeline, apply_edit_operation, list_edit_operations, undo_last_edit; flags: broad-except; parse: OK.
- `backend/app/api/health.py` ? 38 lines; symbols: health_check, db_health_check, redis_health_check; flags: broad-except; parse: OK.
- `backend/app/api/image_editing.py` ? 11 lines; symbols: get_image_editing_info; flags: none; parse: OK.
- `backend/app/api/link_extractor.py` ? 14 lines; symbols: LinkRequest, extract_link; flags: none; parse: OK.
- `backend/app/api/media.py` ? 334 lines; symbols: get_current_user, get_project, validate_media_file, calculate_checksum, upload_media, list_media, get_media, stream_media, delete_media, process_and_run_pipeline; flags: broad-except, ellipsis; parse: OK.
- `backend/app/api/media_management.py` ? 11 lines; symbols: get_media_management_info; flags: none; parse: OK.
- `backend/app/api/model_training.py` ? 16 lines; symbols: run_pipeline; flags: none; parse: OK.
- `backend/app/api/multicam.py` ? 11 lines; symbols: get_multicam_info; flags: none; parse: OK.
- `backend/app/api/project_management.py` ? 11 lines; symbols: get_project_management_info; flags: none; parse: OK.
- `backend/app/api/projects.py` ? 225 lines; symbols: get_current_user, register, login, get_me, create_project, list_projects, get_project, update_project, delete_project; flags: broad-except; parse: OK.
- `backend/app/api/rendering.py` ? 511 lines; symbols: get_current_user, get_project, get_timeline, get_render_job, create_preview_render, create_export_render, list_render_jobs, get_render_job_detail, download_render, cancel_render_job, retry_render_job, delete_render_job; flags: broad-except; parse: OK.
- `backend/app/api/rlhf.py` ? 37 lines; symbols: CorrectionRequest, submit_correction; flags: none; parse: OK.
- `backend/app/api/screenplay.py` ? 11 lines; symbols: get_screenplay_info; flags: none; parse: OK.
- `backend/app/api/search.py` ? 83 lines; symbols: SearchResult, SearchResponse, search_video_segments; flags: broad-except; parse: OK.
- `backend/app/api/social_ai.py` ? 9 lines; symbols: status; flags: none; parse: OK.
- `backend/app/api/styles.py` ? 43 lines; symbols: StyleCloneRequest, clone_video_style, list_available_styles; flags: broad-except; parse: OK.
- `backend/app/api/templates.py` ? 110 lines; symbols: MediaItem, ApplyTemplateRequest, CloneStyleRequest, TemplateResponse, apply_template, clone_style, list_public_templates; flags: none; parse: OK.
- `backend/app/core/backup.py` ? 11 lines; symbols: DatabaseBackupManager, __init__; flags: none; parse: OK.
- `backend/app/core/config.py` ? 57 lines; symbols: Settings, get_settings; flags: none; parse: OK.
- `backend/app/core/database.py` ? 63 lines; symbols: Base, compile_jsonb_sqlite, get_db, init_db, set_sqlite_pragma; flags: ellipsis; parse: OK.
- `backend/app/core/logger.py` ? 44 lines; symbols: StructuredLogger, __init__, _format_log, info, error, debug; flags: broad-except, pass; parse: OK.
- `backend/app/core/monitoring.py` ? 16 lines; symbols: MetricsMock, track_upload_time, __init__; flags: none; parse: OK.
- `backend/app/core/recovery.py` ? 9 lines; symbols: FailureRecoveryManager, __init__; flags: ellipsis; parse: OK.
- `backend/app/core/redis.py` ? 22 lines; symbols: get_redis, close_redis; flags: none; parse: OK.
- `backend/app/core/security.py` ? 40 lines; symbols: get_password_hash, verify_password, create_access_token, decode_access_token, verify_token; flags: none; parse: OK.
- `backend/app/core/testing_utils.py` ? 6 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `backend/app/main.py` ? 89 lines; symbols: root, health_check; flags: none; parse: OK.
- `backend/app/models/__init__.py` ? 97 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `backend/app/models/analysis.py` ? 209 lines; symbols: AnalysisStatus, AnalysisType, CinematicType, AnalysisJob, VideoShot, VideoScene, Keyframe, TranscriptSegment, AudioAnalysis; flags: none; parse: OK.
- `backend/app/models/billing.py` ? 17 lines; symbols: SubscriptionTier, UserSubscription; flags: none; parse: OK.
- `backend/app/models/collaboration.py` ? 58 lines; symbols: ProjectLock, CollaboratorCursor; flags: none; parse: OK.
- `backend/app/models/color.py` ? 86 lines; symbols: ColorAdjustment, ColorAdjustmentBase, ColorAdjustmentCreate, ColorAdjustmentUpdate, ColorAdjustmentResponse; flags: none; parse: OK.
- `backend/app/models/compositing.py` ? 93 lines; symbols: BlendMode, ClipCompositing, ClipCompositingBase, ClipCompositingCreate, ClipCompositingUpdate, ClipCompositingResponse; flags: none; parse: OK.
- `backend/app/models/editing.py` ? 68 lines; symbols: EditOperationType, EditOperation; flags: none; parse: OK.
- `backend/app/models/effects.py` ? 80 lines; symbols: EffectType, Effect; flags: none; parse: OK.
- `backend/app/models/graphics.py` ? 54 lines; symbols: GraphicsLayerType, GraphicsLayer; flags: none; parse: OK.
- `backend/app/models/image_editing.py` ? 72 lines; symbols: ImageOnTimeline; flags: none; parse: OK.
- `backend/app/models/learning.py` ? 114 lines; symbols: ErrorSeverity, ModelStatus, AIErrorEvent, ModelRegistry, PipelineStatus, ErrorToLearningPipeline; flags: none; parse: OK.
- `backend/app/models/media.py` ? 92 lines; symbols: MediaStatus, MediaType, MediaAsset; flags: none; parse: OK.
- `backend/app/models/media_management.py` ? 104 lines; symbols: MediaBin, MediaBinAsset, MediaMarker, MediaTag, MediaAssetTag; flags: none; parse: OK.
- `backend/app/models/memory.py` ? 80 lines; symbols: UserPreference, EditorDecisionPattern; flags: none; parse: OK.
- `backend/app/models/multicam.py` ? 99 lines; symbols: SyncMethod, MulticamAngle, MulticamSequence; flags: none; parse: OK.
- `backend/app/models/notification.py` ? 31 lines; symbols: Notification; flags: none; parse: OK.
- `backend/app/models/phase4.py` ? 274 lines; symbols: StoryStatus, StoryShotRole, TimelineStatus, KnowledgeNodeType, KnowledgeEdgeType, StoryCandidate, StoryShot, Timeline, ShotRanking, KnowledgeNode, KnowledgeEdge; flags: none; parse: OK.
- `backend/app/models/portal.py` ? 34 lines; symbols: ReviewLink; flags: none; parse: OK.
- `backend/app/models/project.py` ? 53 lines; symbols: Project; flags: none; parse: OK.
- `backend/app/models/project_management.py` ? 20 lines; symbols: ProjectSnapshot, TimelineVersion; flags: none; parse: OK.
- `backend/app/models/rendering.py` ? 185 lines; symbols: RenderJobType, RenderJobStatus, RenderPresetPlatform, RenderJob, RenderPreset, ProxyStatus, ProxyMedia, RenderCache; flags: none; parse: OK.
- `backend/app/models/review.py` ? 48 lines; symbols: ReviewStatus, ReviewComment; flags: none; parse: OK.
- `backend/app/models/screenplay.py` ? 158 lines; symbols: Screenplay, Character, Scene, DialogueLine, Take; flags: none; parse: OK.
- `backend/app/models/style.py` ? 50 lines; symbols: StyleClone; flags: none; parse: OK.
- `backend/app/models/template.py` ? 56 lines; symbols: VideoTemplate; flags: none; parse: OK.
- `backend/app/models/user.py` ? 35 lines; symbols: User; flags: none; parse: OK.
- `backend/app/schemas/__init__.py` ? 117 lines; symbols: UserBase, UserCreate, UserUpdate, UserResponse, Token, TokenData, ProjectBase, ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse, MediaAssetBase; flags: ellipsis; parse: OK.
- `backend/app/schemas/styles.py` ? 39 lines; symbols: StyleCloneBase, StyleCloneCreate, StyleCloneExtractRequest, StyleCloneUpdate, StyleCloneResponse, StyleCloneListResponse; flags: none; parse: OK.
- `backend/app/services/__init__.py` ? 50 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `backend/app/services/ai_critic.py` ? 174 lines; symbols: CriticIssue, CriticReport, AICriticService, __init__, analyze, _evaluate_pacing, _evaluate_repetition, _evaluate_continuity, _build_llm_prompt; flags: broad-except, ellipsis, pass; parse: OK.
- `backend/app/services/ai_director.py` ? 389 lines; symbols: AIDirectorStage, StageResult, AIDirectorResult, AIDirectorService, get_ai_director_service, __init__, run_full_pipeline, _stage_validation, _stage_knowledge_graph, _stage_shot_ranking, _stage_story_generation, _stage_story_ranking; flags: broad-except; parse: OK.
- `backend/app/services/ai_memory.py` ? 24 lines; symbols: AIMemoryEngine, __init__, _analyze_failure; flags: none; parse: OK.
- `backend/app/services/ai_provider.py` ? 37 lines; symbols: AIProvider, MockAIProvider, generate_text, analyze_vision, process_audio, generate_text, analyze_vision, process_audio; flags: ellipsis; parse: OK.
- `backend/app/services/analysis_job.py` ? 186 lines; symbols: AnalysisJobService, get_analysis_job_service, __init__, create_job, get_job, get_jobs_for_media, start_job, update_progress, complete_job, fail_job, run_job, retry_job; flags: broad-except; parse: OK.
- `backend/app/services/auto_director.py` ? 25 lines; symbols: InvincibleAutoDirector, __init__; flags: none; parse: OK.
- `backend/app/services/billing_service.py` ? 7 lines; symbols: BillingService, __init__, get_info; flags: pass; parse: OK.
- `backend/app/services/collaboration_service.py` ? 7 lines; symbols: CollaborationService, __init__, get_info; flags: pass; parse: OK.
- `backend/app/services/compositing_service.py` ? 7 lines; symbols: CompositingService, __init__, get_info; flags: pass; parse: OK.
- `backend/app/services/dataset_builder.py` ? 29 lines; symbols: DatasetBuilder, __init__, extract_timeline_decisions, export_to_jsonl; flags: none; parse: OK.
- `backend/app/services/evaluation.py` ? 1 lines; symbols: (no class/function definitions); flags: syntax-error; parse: PARSE_ERROR: IndentationError: expected an indented block after class definition on line 1 (backend/app/services/evaluation.py, line 1).
- `backend/app/services/export_service.py` ? 325 lines; symbols: ExportResult, ExportService, get_export_service, __init__, create_export_job, execute_export_render, _resolve_clips, progress_wrapper; flags: broad-except; parse: OK.
- `backend/app/services/image_editing_service.py` ? 7 lines; symbols: ImageEditingService, __init__, get_info; flags: pass; parse: OK.
- `backend/app/services/knowledge_graph.py` ? 346 lines; symbols: KnowledgeGraphService, get_knowledge_graph_service, __init__, build_graph, _clear_project_graph, _process_media_asset, _add_temporal_edges, _persist_graph, get_graph; flags: none; parse: OK.
- `backend/app/services/media_analysis.py` ? 527 lines; symbols: MediaAnalysisService, get_media_analysis_service, __init__, _register_handlers, _handle_shot_detection, _handle_keyframe_extraction, _handle_scene_detection, _handle_audio_analysis, _handle_speech_transcription, analyze_media, get_analysis_status, get_analysis_results; flags: broad-except, ellipsis; parse: OK.
- `backend/app/services/media_management_service.py` ? 7 lines; symbols: MediaManagementService, __init__, get_info; flags: pass; parse: OK.
- `backend/app/services/media_processing.py` ? 105 lines; symbols: ProcessingTaskType, MediaProcessingService, __init__, process_media, start_worker; flags: broad-except, ellipsis; parse: OK.
- `backend/app/services/model_training.py` ? 31 lines; symbols: ModelTrainer, __init__, clean, label, split, train, validate, benchmark, shadow; flags: none; parse: OK.
- `backend/app/services/multicam_service.py` ? 7 lines; symbols: MulticamService, __init__, get_info; flags: pass; parse: OK.
- `backend/app/services/nlp_editor.py` ? 203 lines; symbols: EditIntent, StructuredEditOperation, NLPEditorService, __init__, extract_intent, generate_edl_operations, process_natural_language_edit; flags: broad-except; parse: OK.
- `backend/app/services/preview_service.py` ? 277 lines; symbols: PreviewResult, PreviewService, get_preview_service, __init__, create_preview_job, execute_preview_render, _resolve_clips, progress_wrapper; flags: broad-except; parse: OK.
- `backend/app/services/privacy.py` ? 13 lines; symbols: PrivacyViolationError, PrivacyManager, __init__; flags: ellipsis; parse: OK.
- `backend/app/services/project_management_service.py` ? 7 lines; symbols: ProjectManagementService, __init__, get_info; flags: pass; parse: OK.
- `backend/app/services/render_job_service.py` ? 343 lines; symbols: RenderJobAction, RenderJobInfo, RenderJobService, get_render_job_service, __init__, create_job, get_job, get_job_by_id, list_jobs, update_job_status, cancel_job, retry_job; flags: broad-except, ellipsis; parse: OK.
- `backend/app/services/rlhf_learning_loop.py` ? 69 lines; symbols: ContinuousLearningEngine, __init__, capture_user_correction, trigger_background_retraining; flags: broad-except, ellipsis; parse: OK.
- `backend/app/services/safety.py` ? 7 lines; symbols: (no class/function definitions); flags: syntax-error; parse: PARSE_ERROR: IndentationError: expected an indented block after class definition on line 7 (backend/app/services/safety.py, line 7).
- `backend/app/services/scene_analyzer.py` ? 247 lines; symbols: SceneBoundary, SceneAnalyzer, TemporalSceneGroupingConfig, TemporalSceneAnalyzer, VisionLanguageSceneAnalyzer, analyze, analyzer_name, supports_semantic_labels, __init__, analyzer_name, supports_semantic_labels, analyze; flags: ellipsis; parse: OK.
- `backend/app/services/screenplay_service.py` ? 7 lines; symbols: ScreenplayService, __init__, get_info; flags: pass; parse: OK.
- `backend/app/services/sequence_planner.py` ? 388 lines; symbols: PlannedSequence, SequencePlannerService, get_sequence_planner_service, __init__, plan_sequence, _plan_chronological, _plan_highlight_reel, _plan_emotional_narrative, _plan_documentary, _plan_educational; flags: ellipsis; parse: OK.
- `backend/app/services/shot_ranker.py` ? 333 lines; symbols: ShotScore, ShotRankerService, get_shot_ranker_service, __init__, rank_shots, _score_shot, _calculate_quality_score, _calculate_relevance_score, _calculate_visual_appeal, _calculate_audio_appeal, _persist_rankings, get_rankings; flags: ellipsis; parse: OK.
- `backend/app/services/social_ai.py` ? 6 lines; symbols: SocialAIEngine, __init__; flags: ellipsis; parse: OK.
- `backend/app/services/storage/__init__.py` ? 122 lines; symbols: StorageService, LocalStorageService, get_storage_service, save, open, delete, exists, save, delete, get_url, get_path, get_url; flags: ellipsis; parse: OK.
- `backend/app/services/storage/gdrive_storage.py` ? 63 lines; symbols: GoogleDriveStorageService, __init__, _authenticate, upload_file, download_file, get_metadata; flags: none; parse: OK.
- `backend/app/services/storage/retention_policy.py` ? 14 lines; symbols: RetentionPolicyService, __init__; flags: none; parse: OK.
- `backend/app/services/storage/s3_storage.py` ? 19 lines; symbols: S3StorageService, __init__; flags: none; parse: OK.
- `backend/app/services/story_generator.py` ? 489 lines; symbols: StoryStructureType, StoryCandidateDraft, StoryGeneratorService, get_story_generator_service, __init__, generate_stories, _generate_chronological, _generate_highlight_reel, _generate_emotional_narrative, _generate_documentary, _generate_educational, _extract_themes_from_transcripts; flags: none; parse: OK.
- `backend/app/services/story_ranker.py` ? 276 lines; symbols: StoryRankingResult, StoryRankerService, get_story_ranker_service, __init__, rank_stories, _score_story, _calculate_coherence, _calculate_engagement, _calculate_completeness, _calculate_footage_coverage, select_best_story; flags: ellipsis; parse: OK.
- `backend/app/services/swarm_orchestrator.py` ? 254 lines; symbols: AgentPipelineMessage, BaseVideoAgent, VisionDirectorAgent, AudioIntelligenceAgent, MasterStoryEditorAgent, PostProductionAgent, ExecutiveProducerAgent, SwarmOrchestrator, __init__, process, call_llm, process; flags: broad-except, ellipsis, pass; parse: OK.
- `backend/app/services/template_engine.py` ? 173 lines; symbols: _TemplateSnapshot, TemplateEngine, get_template_engine, apply_template, _score_media_for_slot, _build_timeline; flags: none; parse: OK.
- `backend/app/services/thumbnail.py` ? 6 lines; symbols: ThumbnailIntelligence, __init__; flags: ellipsis; parse: OK.
- `backend/app/services/timeline_generator.py` ? 188 lines; symbols: TimelineGeneratorService, get_timeline_generator_service, __init__, generate_timeline, _apply_sanity_checks, generate_timeline_from_swarm, get_timeline, list_timelines, regenerate_timeline; flags: none; parse: OK.
- `backend/app/services/transcript_editor.py` ? 55 lines; symbols: TranscriptEditorService, generate_delete_operations; flags: none; parse: OK.
- `backend/app/services/video_cloner.py` ? 220 lines; symbols: VideoStyleCloner, get_video_style_cloner, __init__, analyze_reference_video, generate_template_from_reference, clone_style; flags: broad-except, ellipsis; parse: OK.
- `backend/app/services/video_intelligence.py` ? 33 lines; symbols: CinematicShotType, VideoIntelligenceService, __init__; flags: none; parse: OK.
- `backend/app/workers/__init__.py` ? 52 lines; symbols: init_worker, shutdown_worker; flags: ellipsis; parse: OK.
- `backend/app/workers/render_tasks.py` ? 252 lines; symbols: render_preview_job, _render_preview_job_async, render_export_job, _render_export_job_async, cleanup_old_renders, _cleanup_old_renders_async, retry_failed_renders, _retry_failed_renders_async; flags: broad-except, ellipsis; parse: OK.
- `backend/tests/__init__.py` ? 2 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `backend/tests/conftest.py` ? 90 lines; symbols: compile_jsonb_sqlite, anyio_backend, test_engine, db_session, client, test_user, auth_headers, override_get_db; flags: broad-except, pass; parse: OK.
- `backend/tests/test_api.py` ? 222 lines; symbols: TestHealthEndpoints, TestAuthEndpoints, TestProjectEndpoints, test_health_check, test_db_health_check, test_redis_health_check, test_register, test_register_duplicate_email, test_login, test_login_invalid_credentials, test_create_project, test_create_project_minimal; flags: none; parse: OK.
- `backend/tests/test_rendering.py` ? 120 lines; symbols: sample_project, sample_timeline, test_list_render_presets, test_get_nonexistent_preset, test_preview_render, test_export_render_missing_preset; flags: none; parse: OK.
- `check.py` ? 5 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `deep_scanner.py` ? 83 lines; symbols: analyze_python_file, analyze_ts_file; flags: broad-except, pass; parse: OK.
- `filter.py` ? 6 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `find_fk.py` ? 26 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `fix_browser.py` ? 55 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `fix_llm.py` ? 15 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `fix_lumetri.py` ? 35 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `qa_check.py` ? 68 lines; symbols: check_file; flags: none; parse: OK.
- `run_db_edit.py` ? 44 lines; symbols: run; flags: broad-except; parse: OK.
- `run_edit.py` ? 28 lines; symbols: run; flags: none; parse: OK.
- `scratch_test.py` ? 7 lines; symbols: test_ffmpeg; flags: pass; parse: OK.
- `script.py` ? 23 lines; symbols: (no class/function definitions); flags: syntax-error; parse: PARSE_ERROR: SyntaxError: source code string cannot contain null bytes.
- `test_db.py` ? 13 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `tests/performance/locustfile.py` ? 8 lines; symbols: RenderUser, render_video; flags: none; parse: OK.
- `video_engine/__init__.py` ? 5 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `video_engine/audio/__init__.py` ? 0 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `video_engine/audio/analyzer.py` ? 137 lines; symbols: AudioInfo, AudioAnalyzer, __init__, analyze, _parse_audio_info; flags: broad-except, ellipsis; parse: OK.
- `video_engine/audio/engine.py` ? 17 lines; symbols: AudioEngine, __init__; flags: none; parse: OK.
- `video_engine/audio/speech.py` ? 382 lines; symbols: SpeechRecognitionStatus, TranscriptResult, SpeechAnalyzer, WhisperConfig, WhisperSpeechAnalyzer, WhisperAPISpeechAnalyzer, UnavailableSpeechAnalyzer, transcribe, analyzer_name, is_available, supported_languages, supports_timestamps; flags: broad-except, ellipsis; parse: OK.
- `video_engine/ingestion/__init__.py` ? 0 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `video_engine/ingestion/link_extractor.py` ? 48 lines; symbols: YouTubeStyleExtractor, __init__, extract_data_from_link; flags: ellipsis; parse: OK.
- `video_engine/ingestion/processor.py` ? 183 lines; symbols: MediaMetadata, MediaProcessor, get_media_processor, __init__, extract_metadata, _parse_metadata, generate_thumbnail, generate_proxy; flags: ellipsis; parse: OK.
- `video_engine/rendering/__init__.py` ? 64 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `video_engine/rendering/export.py` ? 238 lines; symbols: ExportPlatform, ExportPreset, get_export_presets, get_preset_by_name, get_presets_by_platform, get_default_preset, create_custom_preset, to_dict; flags: none; parse: OK.
- `video_engine/rendering/ffmpeg_renderer.py` ? 413 lines; symbols: RenderProgress, RenderResult, FFmpegRenderer, create_ffmpeg_renderer, __init__, cancel, _parse_progress_line, render, _probe_output, read_stdout, read_stderr; flags: broad-except, pass; parse: OK.
- `video_engine/rendering/preview.py` ? 65 lines; symbols: PreviewSettings, get_preview_settings, create_preview_settings, to_dict; flags: none; parse: OK.
- `video_engine/rendering/timeline_to_ffmpeg.py` ? 695 lines; symbols: ResolvedClip, FFmpegInputs, CompileResult, TimelineCompiler, create_timeline_compiler, __init__, _get_system_font_dirs, _resolve_font_path, _escape_drawtext, _escape_filter_path, compile, _build_output_options; flags: none; parse: OK.
- `video_engine/shots/__init__.py` ? 0 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `video_engine/shots/detector.py` ? 278 lines; symbols: ShotBoundary, ShotDetector, ShotDetectorOpenCV, get_shot_detector, __init__, detect_shots, _parse_shot_boundaries, __init__, detect_shots; flags: none; parse: OK.
- `video_engine/shots/keyframe_extractor.py` ? 129 lines; symbols: ExtractedKeyframe, KeyframeExtractor, __init__, extract_keyframes_for_shot, _extract_single_keyframe; flags: broad-except; parse: OK.
- `video_engine/timeline/__init__.py` ? 0 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `video_engine/timeline/builder.py` ? 240 lines; symbols: TimelineValidationResult, TimelineBuilder, __init__, get_timeline_schema_version, build_timeline_json, validate_timeline, _validate_video_track; flags: pass; parse: OK.
- `video_engine/vision/__init__.py` ? 5 lines; symbols: (no class/function definitions); flags: none; parse: OK.
- `video_engine/vision/visual_analyzer.py` ? 303 lines; symbols: FaceBBox, ShotVisualData, VisualAnalysisResult, VisualAnalyzer, get_visual_analyzer, to_dict, __init__, _init_detector, analyze_video_sync, analyze_video; flags: broad-except, pass; parse: OK.

### TypeScript/JavaScript
- `frontend/src/app/error.tsx` ? 32 lines; symbols: Error; flags: none.
- `frontend/src/app/layout.tsx` ? 22 lines; symbols: inter, metadata, RootLayout; flags: none.
- `frontend/src/app/loading.tsx` ? 11 lines; symbols: Loading; flags: none.
- `frontend/src/app/login/page.tsx` ? 91 lines; symbols: LoginPage, router, handleSubmit, response, token, meResponse; flags: none.
- `frontend/src/app/page.tsx` ? 203 lines; symbols: HomePage, checkHealth, getStatusBadge, configs, config; flags: none.
- `frontend/src/app/projects/[id]/page.tsx` ? 557 lines; symbols: ProjectDetailPage, params, router, projectId, handleAspectRatioChange, fetchProject, response, fetchTimelines, sorted, fetchMediaAssets, fetchVisionAnalysis, res; flags: none.
- `frontend/src/app/projects/page.tsx` ? 272 lines; symbols: ProjectsPage, router, loadProjects, response, handleCreateProject, handleDeleteProject, CreateProjectModal, modalRef, handleEscape, value, platform; flags: none.
- `frontend/src/app/register/page.tsx` ? 88 lines; symbols: RegisterPage, router, handleSubmit; flags: none.
- `frontend/src/components/Button.tsx` ? 66 lines; symbols: ButtonProps, Button, baseStyles, variants, sizes; flags: none.
- `frontend/src/components/Card.tsx` ? 35 lines; symbols: CardProps, Card, CardHeader, CardContent, CardFooter; flags: none.
- `frontend/src/components/Input.tsx` ? 51 lines; symbols: InputProps, Input, inputId; flags: none.
- `frontend/src/components/MediaUpload.tsx` ? 302 lines; symbols: MediaUploadProps, MediaUpload, fileInputRef, handleFileSelect, selectedFile, const, validExtensions, ext, handleUpload, response, removeFile, formatFileSize; flags: none.
- `frontend/src/components/audio/AudioMixer.tsx` ? 148 lines; symbols: TrackState, INITIAL_TRACKS, AudioMixer, timeout, handleVolumeChange, toggleMute, toggleSolo; flags: none.
- `frontend/src/components/color/ColorWheels.tsx` ? 39 lines; symbols: ColorWheels; flags: none.
- `frontend/src/components/color/LumetriPanel.tsx` ? 120 lines; symbols: LumetriPanelProps, LumetriPanel, timeout; flags: none.
- `frontend/src/components/compositing/TransformPanel.tsx` ? 151 lines; symbols: TransformState, TransformPanelProps, TransformPanel, timeout, handleChange, newState; flags: none.
- `frontend/src/components/effects/EffectsPanel.tsx` ? 388 lines; symbols: EffectsPanelProps, EffectsPanel, timeout, TRANSITIONS; flags: none.
- `frontend/src/components/film/ScreenplayPanel.tsx` ? 75 lines; symbols: DialogueLine, Scene, ScreenplayPanelProps, ScreenplayPanel; flags: none.
- `frontend/src/components/graphics/EssentialGraphicsPanel.tsx` ? 368 lines; symbols: EssentialGraphicsPanelProps, EssentialGraphicsPanel, timeout, TITLE_PRESETS, SUBTITLE_STYLES, handleGenerateCaptions; flags: none.
- `frontend/src/components/layout/NLEWorkspace.tsx` ? 64 lines; symbols: NLEWorkspaceProps, NLEWorkspace; flags: none.
- `frontend/src/components/media/ImageProperties.tsx` ? 94 lines; symbols: PanDirection, KenBurnsState, ImagePropertiesProps, PAN_OPTIONS, ImageProperties, update, next; flags: none.
- `frontend/src/components/media/MediaBrowser.tsx` ? 163 lines; symbols: SearchResult, MOCK_RESULTS, MediaBrowser, handleSearch, response, handleDragStart; flags: mock-data/logic.
- `frontend/src/components/media/ProjectBin.tsx` ? 168 lines; symbols: ColorLabel, MediaItem, Bin, COLORS, ProjectBin, toggleBin, handleToggleBin, updateMedia, renderBinTree, media, isSelected; flags: none.
- `frontend/src/components/multicam/AngleViewer.tsx` ? 64 lines; symbols: Angle, AngleViewerProps, AngleViewer, gridClass, isActive; flags: none.
- `frontend/src/components/project/ExportInterchangeModal.tsx` ? 75 lines; symbols: ExportInterchangeModalProps, ExportInterchangeModal, modalRef, handleEscape; flags: none.
- `frontend/src/components/project/HistoryPanel.tsx` ? 42 lines; symbols: HistoryItem, DUMMY_HISTORY, HistoryPanel, handleRestore; flags: console.log.
- `frontend/src/components/rendering/ExportModal.tsx` ? 176 lines; symbols: ExportModalProps, ExportModal, modalRef, handleEscape, loadPresets, response, defaultPreset, getPlatformLabel, getPlatformColor; flags: none.
- `frontend/src/components/rendering/RenderJobList.tsx` ? 291 lines; symbols: RenderJobListProps, RenderJobList, fetchJobs, params, response, activeJobs, interval, getStatusConfig, getTypeIcon, handleDownload, blob, url; flags: none.
- `frontend/src/components/rendering/RenderPanel.tsx` ? 207 lines; symbols: RenderPanelProps, RenderPanel, loadPresets, response, defaultPreset, handlePreviewRender, handleExportRender, getStatusColor, getStatusIcon; flags: console.log.
- `frontend/src/components/rendering/VideoPreview.tsx` ? 214 lines; symbols: VideoPreviewProps, VideoPreview, videoRef, containerRef, handleLoadedMetadata, handleTimeUpdate, handleError, handleCanPlay, togglePlay, toggleMute, handleVolumeChange, vol; flags: none.
- `frontend/src/components/review/CommentPanel.tsx` ? 65 lines; symbols: Comment, CommentPanel, handleAddComment, comment; flags: mock-data/logic.
- `frontend/src/components/review/ShareModal.tsx` ? 105 lines; symbols: ShareModalProps, ShareModal, modalRef, handleEscape, handleGenerateLink, handleCopy; flags: mock-data/logic.
- `frontend/src/components/styles/StyleClonerModal.tsx` ? 123 lines; symbols: StyleClonerModalProps, StyleClonerModal, modalRef, handleEscape, handleFileUpload, handleClone; flags: none.
- `frontend/src/components/templates/TemplateLibrary.tsx` ? 102 lines; symbols: Template, MOCK_TEMPLATES, TemplateLibrary, handleFileUpload, handleApply; flags: console.log, mock-data/logic.
- `frontend/src/components/timeline/Clip.tsx` ? 65 lines; symbols: ClipData, ClipProps, Clip, isSelected, style, handleKeyDown, handleClick; flags: none.
- `frontend/src/components/timeline/Playhead.tsx` ? 18 lines; symbols: Playhead, playheadRef; flags: none.
- `frontend/src/components/timeline/Timeline.tsx` ? 166 lines; symbols: TimelineProps, TimelineInner, sensors, handleDragStart, clip, handleDragEnd, sourceTrackId, targetTrackId, newTracks, srcTrackIndex, clipIndex, targetTrackIndex; flags: none.
- `frontend/src/components/timeline/TimelineContext.tsx` ? 35 lines; symbols: TimelineState, TimelineContext, TimelineProvider, useTimeline, context; flags: none.
- `frontend/src/components/timeline/TimelineRuler.tsx` ? 47 lines; symbols: TimelineRuler, rulerRef, handleRulerClick, rect, x, time, ticks, tickInterval, formatTime, m, s; flags: none.
- `frontend/src/components/timeline/Track.tsx` ? 48 lines; symbols: TrackData, TrackProps, Track; flags: none.
- `frontend/src/components/timeline/index.ts` ? 6 lines; symbols: (not detected); flags: none.
- `frontend/src/components/transcript/TranscriptPanel.tsx` ? 118 lines; symbols: TranscriptWord, TranscriptPanelProps, TranscriptPanel, handleWordClick, newSelection, handleDeleteSelected, selectedWords, minStart, maxEnd, isSelected; flags: none.
- `frontend/src/lib/api.ts` ? 187 lines; symbols: API_URL, api, token, authApi, formData, projectsApi, mediaApi, progress, healthApi, aiDirectorApi, renderingApi, searchApi; flags: none.
- `frontend/src/lib/store.ts` ? 66 lines; symbols: AuthState, useAuthStore, ProjectState, useProjectStore; flags: none.
- `frontend/src/lib/useFocusTrap.ts` ? 52 lines; symbols: useFocusTrap, ref, handleKeyDown, focusableElements, firstElement, lastElement; flags: none.
- `frontend/src/lib/utils.ts` ? 69 lines; symbols: ClassValue, cn, formatDate, formatDateTime, getPlatformLabel, getStatusColor, formatFileSize, k, sizes, i, formatDuration, hrs; flags: none.
- `frontend/src/types/index.ts` ? 152 lines; symbols: User, Project, ProjectCreate, ProjectUpdate, ProjectListResponse, Token, MediaAsset, MediaAssetListResponse, HealthResponse, RenderJobType, RenderJobStatus, RenderPresetPlatform; flags: none.

## 11. Recommended remediation order
1. Freeze deletion and feature claims; establish a canonical source tree and separate app code from generated/data/vendor trees.
2. Fix syntax/import failures and make the `app.*` package import cleanly.
3. Fix authentication/ownership/security boundaries before exposing more endpoints.
4. Choose and enforce one timeline schema, then connect AI?timeline?renderer?download with a real fixture E2E test.
5. Complete storage, migration seeding, Celery worker topology, cancellation/progress/retry and strict FFprobe validation.
6. Wire frontend components to real API contracts; delete or archive orphan/mock components only after product decisions.
7. Add CI, backend/frontend/security/render tests and only then continue enterprise feature phases.

## 12. Audit honesty notes
- ?Available? means code or UI exists; it does not mean the user workflow is verified.
- ?Dead/orphan? means no current import/route path was found in the scanned application; it may still be intended future work.
- Existing audit documents were used as historical evidence but re-checked where they conflicted with current code.
- No destructive cleanup was performed.


## 13. Cleanup executed after user approval

User selected **Caches + historical artifacts**. Deleted:

- `frontend/.next/` and `frontend/tsconfig.tsbuildinfo`
- Python/pytest/mypy caches and coverage output
- `graphify-out/` generated graph/cache/HTML/manifest artifacts
- Historical pytest/mypy/pip/output/filter/result files listed in Section 9

**Deleted:** 340 files, approximately 129,975,108 bytes.

Preserved: `frontend/node_modules/`, `backend/.venv/`, all source files, databases, media, uploads, and `training_data/`.
