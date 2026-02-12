"""
Test configuration and fixtures for task tracker tests.

Provides:
- Test database with SQLite in-memory for speed
- FastAPI test client with database dependency override
- Authentication helpers (JWT token generation)
- Common fixtures for users, teams, projects, and tasks
"""

import os
import sys
import logging
from datetime import timedelta
from typing import Generator, Dict, Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON, Text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, get_db
from main import app
import models
from auth.security import hash_password, create_access_token

# Configure logging for tests
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# SQLite in-memory database for fast testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """
    Create a fresh in-memory SQLite database for each test.

    This ensures test isolation and fast execution.
    """
    logger.debug("Creating test database")

    # Create engine with SQLite in-memory
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Replace PostgreSQL-specific types with SQLite-compatible types
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
            elif isinstance(column.type, TSVECTOR):
                column.type = Text()

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)
        logger.debug("Test database cleaned up")


@pytest.fixture(scope="function")
def client(test_db: Session) -> TestClient:
    """
    Create FastAPI test client with database dependency override.
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(test_db: Session) -> models.User:
    """
    Create an admin user for testing.
    """
    logger.debug("Creating admin user")
    user = models.User(
        name="Admin User",
        email="admin@test.com",
        password_hash=hash_password("admin123"),
        role="admin",
        is_active=True,
        email_verified=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    logger.info(f"Created admin user with ID: {user.id}")
    return user


@pytest.fixture(scope="function")
def regular_user(test_db: Session) -> models.User:
    """
    Create a regular editor user for testing.
    """
    logger.debug("Creating regular user")
    user = models.User(
        name="Regular User",
        email="user@test.com",
        password_hash=hash_password("user123"),
        role="editor",
        is_active=True,
        email_verified=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    logger.info(f"Created regular user with ID: {user.id}")
    return user


@pytest.fixture(scope="function")
def another_user(test_db: Session) -> models.User:
    """
    Create another user for testing multi-user scenarios.
    """
    logger.debug("Creating another user")
    user = models.User(
        name="Another User",
        email="another@test.com",
        password_hash=hash_password("another123"),
        role="editor",
        is_active=True,
        email_verified=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    logger.info(f"Created another user with ID: {user.id}")
    return user


def create_auth_token(user: models.User, expires_delta: timedelta = None) -> str:
    """
    Helper to create JWT access token for a user.

    Args:
        user: User to create token for
        expires_delta: Optional expiration time override

    Returns:
        JWT access token string
    """
    logger.debug(f"Creating auth token for user {user.id}")
    token_data = {
        "sub": str(user.id),
        "role": user.role,
        "email": user.email
    }
    return create_access_token(token_data, expires_delta)


@pytest.fixture(scope="function")
def auth_token(admin_user: models.User) -> str:
    """
    Create auth token for admin user.
    """
    return create_auth_token(admin_user)


@pytest.fixture(scope="function")
def auth_headers(auth_token: str) -> Dict[str, str]:
    """
    Create authorization headers with admin token.
    """
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="function")
def user_auth_headers(regular_user: models.User) -> Dict[str, str]:
    """
    Create authorization headers for regular user.
    """
    token = create_auth_token(regular_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def another_user_auth_headers(another_user: models.User) -> Dict[str, str]:
    """
    Create authorization headers for another user.
    """
    token = create_auth_token(another_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def team(test_db: Session, admin_user: models.User) -> models.Team:
    """
    Create a test team with admin as creator.
    """
    logger.debug("Creating test team")
    team = models.Team(
        name="Test Team",
        description="A team for testing",
        created_by=admin_user.id
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    # Add admin as team admin
    team_member = models.TeamMember(
        team_id=team.id,
        user_id=admin_user.id,
        role="admin"
    )
    test_db.add(team_member)
    test_db.commit()

    logger.info(f"Created test team with ID: {team.id}")
    return team


@pytest.fixture(scope="function")
def another_team(test_db: Session, admin_user: models.User) -> models.Team:
    """
    Create another test team.
    """
    logger.debug("Creating another test team")
    team = models.Team(
        name="Another Team",
        description="Another team for testing",
        created_by=admin_user.id
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    # Add admin as team admin
    team_member = models.TeamMember(
        team_id=team.id,
        user_id=admin_user.id,
        role="admin"
    )
    test_db.add(team_member)
    test_db.commit()

    logger.info(f"Created another test team with ID: {team.id}")
    return team


@pytest.fixture(scope="function")
def personal_project(test_db: Session, admin_user: models.User) -> models.Project:
    """
    Create a personal project (no team).
    """
    logger.debug("Creating personal project")
    project = models.Project(
        name="Personal Project",
        description="A personal project",
        author_id=admin_user.id,
        team_id=None
    )
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)

    # Add creator as owner
    member = models.ProjectMember(
        project_id=project.id,
        user_id=admin_user.id,
        role="owner"
    )
    test_db.add(member)
    test_db.commit()

    logger.info(f"Created personal project with ID: {project.id}")
    return project


@pytest.fixture(scope="function")
def team_project(test_db: Session, admin_user: models.User, team: models.Team) -> models.Project:
    """
    Create a team project.
    """
    logger.debug("Creating team project")
    project = models.Project(
        name="Team Project",
        description="A team project",
        author_id=admin_user.id,
        team_id=team.id
    )
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)

    logger.info(f"Created team project with ID: {project.id}")
    return project
