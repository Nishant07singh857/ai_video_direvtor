import os
import secrets
import tempfile
from pathlib import Path

# Set safe process-local configuration BEFORE importing application modules.
# Neither service singletons nor background jobs may connect to a user's DB.
_preferred_temp = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "Temp" / "opencode"
_test_storage = tempfile.TemporaryDirectory(
    prefix="director-pytest-", dir=_preferred_temp if _preferred_temp.is_dir() else None,
)
os.environ.update({
    "ENVIRONMENT": "test", "DEBUG": "false", "SECRET_KEY": secrets.token_urlsafe(48),
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:", "DATABASE_URL_SYNC": "sqlite:///:memory:",
    "MEDIA_STORAGE_ROOT": _test_storage.name, "STORAGE_PROVIDER": "local",
    "CELERY_ENABLED": "false", "RENDER_SYNC_FALLBACK": "true",
    "LLM_ENABLED": "false", "ALLOW_MOCK_AI": "false",
})

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models import User

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(type_, compiler, **kw):
    return 'JSON'

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="function")
async def test_engine(tmp_path, monkeypatch):
    from sqlalchemy import event
    from app.core import database
    from app.services import storage

    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'test.sqlite').as_posix()}", echo=False)
    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
    
    # Patch the global engine and async_session_maker so services use the test db
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "async_session_maker", sessionmaker(engine, class_=AsyncSession, expire_on_commit=False))
    monkeypatch.setattr(storage, "_local_storage", storage.LocalStorageService(str(tmp_path / "media")))
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.fixture
async def client(test_engine):
    from app.core import database
    async def override_get_db():
        async with database.async_session_maker() as session:
            yield session

    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)

@pytest.fixture
async def test_user(db_session):
    from app.core.security import get_password_hash
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def auth_headers(client, test_user):
    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
