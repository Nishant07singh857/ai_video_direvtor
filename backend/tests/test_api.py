import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models import User, Project



class TestHealthEndpoints:
    async def test_health_check(self, client):
        response = await client.get(f"{settings.API_V1_PREFIX}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == settings.APP_NAME

    async def test_db_health_check(self, client):
        response = await client.get(f"{settings.API_V1_PREFIX}/health/db")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    async def test_redis_health_check(self, client):
        response = await client.get(f"{settings.API_V1_PREFIX}/health/redis")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]


class TestAuthEndpoints:
    async def test_register(self, client):
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={"email": "newuser@example.com", "password": "newpassword123", "full_name": "New User"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data

    async def test_register_duplicate_email(self, client, test_user):
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={"email": test_user.email, "password": "password123"},
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    async def test_login(self, client, test_user):
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            data={"username": test_user.email, "password": "testpassword"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, client):
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            data={"username": "wrong@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401


class TestProjectEndpoints:
    async def test_create_project(self, client, auth_headers):
        response = await client.post(
            f"{settings.API_V1_PREFIX}/projects",
            json={"name": "Test Project", "description": "A test project", "platform": "youtube"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "A test project"
        assert data["platform"] == "youtube"
        assert data["status"] == "draft"
        assert "id" in data

    async def test_create_project_minimal(self, client, auth_headers):
        response = await client.post(
            f"{settings.API_V1_PREFIX}/projects",
            json={"name": "Minimal Project"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Project"
        assert data["description"] is None
        assert data["platform"] is None

    async def test_list_projects(self, client, auth_headers, test_user, db_session):
        # Create a few projects
        for i in range(3):
            project = Project(
                user_id=test_user.id,
                name=f"Project {i}",
                platform="youtube",
            )
            db_session.add(project)
        await db_session.commit()

        response = await client.get(
            f"{settings.API_V1_PREFIX}/projects",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["projects"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 20

    async def test_list_projects_pagination(self, client, auth_headers, test_user, db_session):
        for i in range(5):
            project = Project(user_id=test_user.id, name=f"Project {i}")
            db_session.add(project)
        await db_session.commit()

        response = await client.get(
            f"{settings.API_V1_PREFIX}/projects",
            params={"page": 1, "page_size": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["projects"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_get_project(self, client, auth_headers, test_user, db_session):
        project = Project(user_id=test_user.id, name="Test Project", platform="instagram")
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        response = await client.get(
            f"{settings.API_V1_PREFIX}/projects/{project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(project.id)
        assert data["name"] == "Test Project"
        assert data["platform"] == "instagram"

    async def test_get_project_not_found(self, client, auth_headers):
        import uuid
        response = await client.get(
            f"{settings.API_V1_PREFIX}/projects/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_update_project(self, client, auth_headers, test_user, db_session):
        project = Project(user_id=test_user.id, name="Original Name")
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        response = await client.patch(
            f"{settings.API_V1_PREFIX}/projects/{project.id}",
            json={"name": "Updated Name", "platform": "shorts"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["platform"] == "shorts"

    async def test_delete_project(self, client, auth_headers, test_user, db_session):
        project = Project(user_id=test_user.id, name="To Delete")
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        response = await client.delete(
            f"{settings.API_V1_PREFIX}/projects/{project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(
            f"{settings.API_V1_PREFIX}/projects/{project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_user_isolation(self, client, auth_headers, db_session):
        # Create another user
        from app.core.security import get_password_hash
        other_user = User(
            email="other@example.com",
            hashed_password=get_password_hash("password"),
            full_name="Other User",
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        # Other user creates a project
        other_project = Project(user_id=other_user.id, name="Other's Project")
        db_session.add(other_project)
        await db_session.commit()
        await db_session.refresh(other_project)

        # Current user tries to access other's project
        response = await client.get(
            f"{settings.API_V1_PREFIX}/projects/{other_project.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404