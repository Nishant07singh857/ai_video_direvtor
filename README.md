# AI Video Director

An autonomous AI video editing platform that understands raw footage, discovers stories, and creates professional edits through natural language interaction.

## Vision

> **User uploads raw footage. The AI understands the footage, discovers the strongest possible story from the footage, selects the best clips, creates a professional editing plan, renders the edit, critiques its own result, improves it, and allows the user to continue editing through natural-language instructions.**

## Architecture Overview

```
ai-video-director/
├── frontend/          # Next.js + React + TypeScript + Tailwind
├── backend/           # FastAPI + Python + PostgreSQL + Redis
├── ai/                # AI/ML components (vision, speech, story, editing, critic)
├── video_engine/      # Video processing (ingestion, shots, timeline, rendering)
├── workers/           # Async job workers (Celery)
├── database/          # SQLAlchemy models, migrations
├── training/          # Training data, models, evaluation
├── docs/              # Documentation
└── docker/            # Docker configuration
```

## Core Principles

1. **No Fabricated Events** - AI only works with uploaded footage
2. **Source-Grounded Editing** - Every output segment traces to source assets
3. **User Control** - AI is autonomous but never prevents user control
4. **Minimal Destructive Editing** - Immutable originals, timeline instructions only
5. **Versioning** - Every major edit creates a new version

## Development Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Foundation (Repo, Docker, Frontend, Backend, DB, Storage, Auth) | ✅ Complete |
| 2 | Media (Upload, Validation, Metadata, Proxy/Thumbnail Generation) | ⏳ Planned |
| 3 | Video Intelligence (Shot Detection, Vision, Speech, Audio, Embeddings) | ⏳ Planned |
| 4 | AI Director (Story Generation, Ranking, Shot Selection, Timeline) | ⏳ Planned |
| 5 | Rendering (Timeline JSON, FFmpeg, Preview, Export) | ⏳ Planned |
| 6 | Conversational Editing (NL Commands, Timeline Patching, Versioning) | ⏳ Planned |
| 7 | Critic (AI Review, Revision, Auto-Improvement) | ⏳ Planned |
| 8 | Learning (Feedback, Preferences, Training Data, Custom Models) | ⏳ Planned |

## Tech Stack

- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.11, PostgreSQL, Redis
- **Video**: FFmpeg, OpenCV
- **Queue**: Celery + Redis
- **Vector Search**: pgvector
- **Deployment**: Docker, Docker Compose

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 22+
- PostgreSQL 16+
- Redis 7+ (optional for local dev)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
# On Windows: .\venv\Scripts\activate
# On Mac/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up Environment
copy .env.example .env (or cp .env.example .env)
# The default .env is configured to use a local SQLite database (ai_video_director.db)

# Start development server
python -m uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend

# Set up Environment
copy .env.example .env.local (or cp .env.example .env.local)

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:3000`
Backend API will be available at `http://localhost:8000`

### Docker Compose (Alternative)

```bash
cd docker
docker-compose up -d
```

This starts:
- PostgreSQL on port 5432
- Redis on port 6379
- Backend on port 8000
- Frontend on port 3000

## Environment Variables

### Backend (.env)

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_video_director
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/ai_video_director

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-change-in-production
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

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## API Endpoints

### Health Checks
- `GET /api/v1/health` - Backend health
- `GET /api/v1/health/db` - Database health
- `GET /api/v1/health/redis` - Redis health

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login (returns JWT)
- `GET /api/v1/auth/me` - Get current user

### Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List projects (paginated)
- `GET /api/v1/projects/{id}` - Get project
- `PATCH /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

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

## Running Tests

### Backend

```bash
cd backend
python -m pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm run type-check
npm run build
npm run lint
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Database](docs/DATABASE.md)
- [AI Pipeline](docs/AI_PIPELINE.md)
- [Editing Engine](docs/EDITING_ENGINE.md)
- [Agent System](docs/AGENT_SYSTEM.md)
- [Training](docs/TRAINING.md)
- [Security](docs/SECURITY.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Testing](docs/TESTING.md)
- [Roadmap](docs/ROADMAP.md)

## License

Proprietary - All rights reserved.