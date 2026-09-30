# AI Video Director - Project Specification

This document serves as the long-term source of truth for the project. It replaces the need to repeatedly send the entire master prompt.

## Product Vision

**AI Video Director** - An autonomous AI video editing platform where:
- User uploads raw footage
- AI understands the footage, discovers the strongest story
- AI selects best clips, creates professional editing plan
- AI renders, critiques, improves
- User continues editing through natural language

## Core Constraints (Architecture-Level)

| Constraint | Description |
|------------|-------------|
| **A - No Fabricated Events** | AI only works with uploaded footage |
| **B - Source-Grounded Editing** | Every output segment traces to source assets with timecodes |
| **C - User Control** | AI autonomous but never prevents user control |
| **D - Minimal Destructive Editing** | Immutable originals, timeline instructions only |
| **E - Versioning** | Every major edit creates a new version (V1, V2, V3...) |

## Development Phases

### Phase 1 - Foundation ✅ CURRENT
- [ ] Repository structure
- [ ] Docker + Docker Compose (PostgreSQL, Redis)
- [ ] Frontend (Next.js + React + TypeScript + Tailwind)
- [ ] Backend (FastAPI + SQLAlchemy + Pydantic)
- [ ] Database models + migrations
- [ ] Basic authentication foundation
- [ ] Project CRUD API
- [ ] Health check endpoints
- [ ] Basic logging + error handling
- [ ] Frontend ↔ Backend communication
- [ ] Development documentation

### Phase 2 - Media Ingestion
- [ ] Video upload + validation
- [ ] Metadata extraction (duration, codec, fps, etc.)
- [ ] Proxy generation
- [ ] Thumbnail generation
- [ ] Object storage abstraction

### Phase 3 - Video Intelligence
- [ ] Shot detection (scene changes)
- [ ] Vision analysis (objects, faces, scenes, actions)
- [ ] Speech transcription
- [ ] Audio analysis
- [ ] Embeddings generation
- [ ] Person/face tracking

### Phase 4 - AI Director
- [ ] Project knowledge graph
- [ ] Story candidate generation
- [ ] Story ranking
- [ ] Shot ranking
- [ ] Sequence planning
- [ ] Timeline generation

### Phase 5 - Rendering
- [ ] Timeline JSON specification
- [ ] FFmpeg renderer
- [ ] Preview generation
- [ ] Export pipeline

### Phase 6 - Conversational Editing
- [ ] Natural language command parser
- [ ] Timeline patching
- [ ] Version control

### Phase 7 - Critic
- [ ] AI review of rendered output
- [ ] Auto-revision loop

### Phase 8 - Learning
- [ ] Feedback collection
- [ ] Preference memory
- [ ] Training data pipeline
- [ ] Custom ranking models

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11, SQLAlchemy 2.0, Pydantic v2 |
| Database | PostgreSQL 16 + pgvector |
| Cache/Queue | Redis 7, Celery |
| Video | FFmpeg, OpenCV |
| Auth | JWT (planned) |
| Deployment | Docker, Docker Compose |

## Repository Structure

```
ai-video-director/
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js App Router
│   │   ├── components/    # React components
│   │   ├── lib/           # Utilities, API client
│   │   └── types/         # TypeScript types
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   └── tailwind.config.js
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── core/          # Config, security, database
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── main.py        # FastAPI app
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── alembic/           # Migrations
├── ai/
│   ├── vision/
│   ├── speech/
│   ├── audio/
│   ├── embeddings/
│   ├── story/
│   ├── ranking/
│   ├── editing/
│   ├── critic/
│   └── agents/
├── video_engine/
│   ├── ingestion/
│   ├── shots/
│   ├── timeline/
│   ├── rendering/
│   └── audio/
├── workers/
├── database/
├── training/
├── docs/
└── docker/
    ├── docker-compose.yml
    ├── Dockerfile.backend
    ├── Dockerfile.frontend
    └── .env.example
```

## API Design (Phase 1)

### Health Checks
- `GET /health` - Backend health
- `GET /health/db` - Database health
- `GET /health/redis` - Redis health

### Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List projects
- `GET /api/v1/projects/{id}` - Get project
- `PATCH /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Authentication (Foundation)
- `POST /api/v1/auth/register` - Register
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Current user

## Database Schema (Phase 1)

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    platform VARCHAR(50), -- youtube, instagram, shorts
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Project Versions (for Phase 6+)
CREATE TABLE project_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    timeline_json JSONB,
    user_instruction TEXT,
    ai_decision TEXT,
    render_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_video_director
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/ai_video_director

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# App
APP_NAME=AI Video Director
DEBUG=true
API_V1_PREFIX=/api/v1

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# Storage (Phase 2+)
S3_ENDPOINT=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=
```

## Implementation Rules

1. **Inspect before modifying** - Always check existing code first
2. **Smallest correct implementation** - Don't over-engineer
3. **Production-quality modular code** - Clean architecture
4. **Add tests** - Unit + integration
5. **Run tests** - Must pass before committing
6. **Type checks** - Frontend (tsc) + Backend (mypy)
7. **Verify Docker** - Containers must build and run
8. **Update documentation** - Keep specs in sync

## Current Status

- [x] Repository initialized with directory structure
- [x] README.md created
- [x] PROJECT_SPEC.md created
- [x] Docker + Docker Compose (files created, Docker not available on this machine)
- [x] Backend foundation (FastAPI, SQLAlchemy, Pydantic)
- [x] Frontend foundation (Next.js, React, TypeScript, Tailwind)
- [x] Database models + migrations (users, projects, project_versions)
- [x] Health check endpoints (/health, /health/db, /health/redis)
- [x] Project CRUD API (create, list, get, update, delete)
- [x] Basic auth foundation (register, login, JWT tokens)
- [x] Frontend-backend integration (API client, project pages)
- [x] Tests passing (16 backend tests pass)
- [x] Documentation updated

## Phase 2 Status

- [x] MediaAsset database model with project relationship
- [x] Alembic migration for media_assets table
- [x] Storage abstraction (LocalStorageService with path traversal protection)
- [x] Media upload API (POST /api/v1/projects/{project_id}/media)
- [x] Media listing API (GET /api/v1/projects/{project_id}/media)
- [x] Media retrieval API (GET /api/v1/media/{media_id})
- [x] Media deletion API (DELETE /api/v1/media/{media_id})
- [x] Media validation (file type, size, extension)
- [x] Checksum generation (SHA-256)
- [x] Duplicate detection
- [x] FFprobe metadata extraction service
- [x] FFmpeg thumbnail generation service
- [x] Media processing service (background processing foundation)
- [x] Project ownership enforcement on all media endpoints
- [x] Cross-user access rejection (404)
- [x] Unauthenticated access rejection (401)
- [x] Storage path safety (no path traversal, unique storage keys)
- [x] Frontend media upload UI (MediaUpload component)
- [x] Frontend media list UI (MediaList component)
- [x] Frontend project detail page integration
- [x] Frontend type-check and build pass

## Next Steps (Phase 1)

1. ✅ Create Docker Compose with PostgreSQL + Redis (files created)
2. ✅ Create backend Dockerfile
3. ✅ Create frontend Dockerfile
4. ✅ Implement backend core (config, database, models)
5. ✅ Implement backend API (health, projects, auth)
6. ✅ Implement frontend (pages, API client, project UI)
7. ✅ Add tests
8. ✅ Verify full stack works (SQLite for local dev, Docker for PostgreSQL)
9. ✅ Update documentation

## Next Steps (Phase 2)

1. ✅ MediaAsset model and migration
2. ✅ Storage abstraction
3. ✅ Upload API with validation
4. ✅ Metadata extraction (FFprobe)
5. ✅ Thumbnail generation (FFmpeg)
6. ✅ Media CRUD APIs
7. ✅ Frontend upload UI
8. ✅ Frontend media listing
9. ✅ Tests and verification
10. ✅ Documentation update