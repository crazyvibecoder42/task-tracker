"""
Tests for assignable users endpoint (GET /api/projects/{id}/assignable-users).

Tests cover:
- Authorization (401, 403, 200 for admin)
- Team project assignable users (returns all team members)
- Personal project assignable users (returns only project members)
- Edge cases (404, correct user schema)
"""

import logging
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import models
from tests.conftest import create_auth_token

logger = logging.getLogger(__name__)


# ============== Authorization Tests (3 tests) ==============


def test_assignable_users_without_authentication(
    client: TestClient,
    personal_project: models.Project
):
    """Test that listing assignable users fails without authentication (401)."""
    logger.debug("Testing assignable users without authentication")

    response = client.get(f"/api/projects/{personal_project.id}/assignable-users")

    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.json()}"
    logger.info("✓ Assignable users correctly rejected without authentication")


def test_assignable_users_without_permission(
    client: TestClient,
    personal_project: models.Project,
    regular_user: models.User,
    test_db: Session
):
    """Test that listing assignable users fails without viewer permission (404 to avoid information leakage)."""
    logger.debug("Testing assignable users without permission")

    # regular_user is NOT a member of personal_project (only admin_user is)
    # Try to list assignable users as regular_user
    token = create_auth_token(regular_user)
    response = client.get(
        f"/api/projects/{personal_project.id}/assignable-users",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Returns 404 (not 403) to avoid revealing project existence to non-members
    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.json()}"
    assert "project not found" in response.json()["detail"].lower()
    logger.info("✓ Assignable users correctly rejected without permission")


def test_assignable_users_as_global_admin(
    client: TestClient,
    team_project: models.Project,
    admin_user: models.User,
    auth_headers: dict
):
    """Test that global admin can list assignable users for any project (200)."""
    logger.debug("Testing assignable users as global admin")

    response = client.get(
        f"/api/projects/{team_project.id}/assignable-users",
        headers=auth_headers
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert isinstance(data, list), "Response should be a list"
    logger.info("✓ Global admin can list assignable users")


# ============== Team Project Tests (4 tests) ==============


def test_team_project_returns_all_team_members(
    client: TestClient,
    team_project: models.Project,
    team: models.Team,
    admin_user: models.User,
    regular_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that team project returns all team members as assignable users."""
    logger.debug("Testing team project returns all team members")

    # Add regular_user to team
    team_member = models.TeamMember(
        team_id=team.id,
        user_id=regular_user.id,
        role="member"
    )
    test_db.add(team_member)
    test_db.commit()

    # List assignable users
    response = client.get(
        f"/api/projects/{team_project.id}/assignable-users",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Should have 2 team members (admin_user + regular_user)
    assert len(data) == 2, f"Expected 2 assignable users, found {len(data)}"

    user_ids = [user["id"] for user in data]
    assert admin_user.id in user_ids, "admin_user should be assignable"
    assert regular_user.id in user_ids, "regular_user should be assignable"
    logger.info("✓ Team project correctly returns all team members")


def test_team_project_orders_by_name(
    client: TestClient,
    team_project: models.Project,
    team: models.Team,
    admin_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that team project returns users ordered alphabetically by name."""
    logger.debug("Testing team project orders users by name")

    # Add users with specific names
    user_zebra = models.User(
        name="Zebra User",
        email="zebra@test.com",
        password_hash="hash",
        role="editor"
    )
    user_alpha = models.User(
        name="Alpha User",
        email="alpha@test.com",
        password_hash="hash",
        role="editor"
    )
    test_db.add_all([user_zebra, user_alpha])
    test_db.commit()
    test_db.refresh(user_zebra)
    test_db.refresh(user_alpha)

    # Add both to team
    for user in [user_zebra, user_alpha]:
        team_member = models.TeamMember(
            team_id=team.id,
            user_id=user.id,
            role="member"
        )
        test_db.add(team_member)
    test_db.commit()

    # List assignable users
    response = client.get(
        f"/api/projects/{team_project.id}/assignable-users",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Verify alphabetical order
    names = [user["name"] for user in data]
    assert names == sorted(names), f"Users should be ordered alphabetically, got: {names}"
    logger.info("✓ Team project correctly orders users by name")


def test_team_project_empty_when_no_members(
    client: TestClient,
    admin_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that team project with no members returns empty list."""
    logger.debug("Testing team project with no members")

    # Create team with no members
    team = models.Team(
        name="Empty Team",
        description="Team with no members",
        created_by=admin_user.id
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    # Create team project
    project = models.Project(
        name="Team Project",
        author_id=admin_user.id,
        team_id=team.id
    )
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)

    # List assignable users (global admin can access)
    response = client.get(
        f"/api/projects/{project.id}/assignable-users",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0, f"Expected empty list, found {len(data)} users"
    logger.info("✓ Team project with no members returns empty list")


def test_team_project_returns_multiple_members(
    client: TestClient,
    team_project: models.Project,
    team: models.Team,
    admin_user: models.User,
    regular_user: models.User,
    another_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that team project returns all multiple team members."""
    logger.debug("Testing team project returns multiple members")

    # Add both regular_user and another_user to team
    for user in [regular_user, another_user]:
        team_member = models.TeamMember(
            team_id=team.id,
            user_id=user.id,
            role="member"
        )
        test_db.add(team_member)
    test_db.commit()

    # List assignable users
    response = client.get(
        f"/api/projects/{team_project.id}/assignable-users",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Should have 3 team members (admin_user + regular_user + another_user)
    assert len(data) == 3, f"Expected 3 assignable users, found {len(data)}"

    user_ids = [user["id"] for user in data]
    assert admin_user.id in user_ids
    assert regular_user.id in user_ids
    assert another_user.id in user_ids
    logger.info("✓ Team project correctly returns multiple members")


# ============== Personal Project Tests (3 tests) ==============


def test_personal_project_returns_only_project_members(
    client: TestClient,
    personal_project: models.Project,
    admin_user: models.User,
    regular_user: models.User,
    another_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that personal project returns only project members."""
    logger.debug("Testing personal project returns only project members")

    # Add regular_user as project member
    member = models.ProjectMember(
        project_id=personal_project.id,
        user_id=regular_user.id,
        role="editor"
    )
    test_db.add(member)
    test_db.commit()

    # another_user is NOT a project member

    # List assignable users
    response = client.get(
        f"/api/projects/{personal_project.id}/assignable-users",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Should have 2 project members (admin_user + regular_user)
    assert len(data) == 2, f"Expected 2 assignable users, found {len(data)}"

    user_ids = [user["id"] for user in data]
    assert admin_user.id in user_ids, "admin_user should be assignable"
    assert regular_user.id in user_ids, "regular_user should be assignable"
    assert another_user.id not in user_ids, "another_user should NOT be assignable"
    logger.info("✓ Personal project correctly returns only project members")


def test_personal_project_excludes_non_members(
    client: TestClient,
    personal_project: models.Project,
    admin_user: models.User,
    regular_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that personal project excludes non-members."""
    logger.debug("Testing personal project excludes non-members")

    # regular_user is NOT a project member
    # Only admin_user is a member (created in fixture)

    # List assignable users
    response = client.get(
        f"/api/projects/{personal_project.id}/assignable-users",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Should only have admin_user
    assert len(data) == 1, f"Expected 1 assignable user, found {len(data)}"
    assert data[0]["id"] == admin_user.id, "Only admin_user should be assignable"
    logger.info("✓ Personal project correctly excludes non-members")


def test_personal_project_orders_by_name(
    client: TestClient,
    personal_project: models.Project,
    admin_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that personal project returns users ordered alphabetically by name."""
    logger.debug("Testing personal project orders users by name")

    # Add users with specific names
    user_zebra = models.User(
        name="Zebra User",
        email="zebra2@test.com",
        password_hash="hash",
        role="editor"
    )
    user_alpha = models.User(
        name="Alpha User",
        email="alpha2@test.com",
        password_hash="hash",
        role="editor"
    )
    test_db.add_all([user_zebra, user_alpha])
    test_db.commit()
    test_db.refresh(user_zebra)
    test_db.refresh(user_alpha)

    # Add both as project members
    for user in [user_zebra, user_alpha]:
        member = models.ProjectMember(
            project_id=personal_project.id,
            user_id=user.id,
            role="editor"
        )
        test_db.add(member)
    test_db.commit()

    # List assignable users
    response = client.get(
        f"/api/projects/{personal_project.id}/assignable-users",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Verify alphabetical order
    names = [user["name"] for user in data]
    assert names == sorted(names), f"Users should be ordered alphabetically, got: {names}"
    logger.info("✓ Personal project correctly orders users by name")


# ============== Edge Cases (2 tests) ==============


def test_assignable_users_project_not_found(
    client: TestClient,
    auth_headers: dict
):
    """Test that assignable users fails for non-existent project (404)."""
    logger.debug("Testing assignable users for non-existent project")

    response = client.get(
        "/api/projects/99999/assignable-users",
        headers=auth_headers
    )

    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.json()}"
    assert "Project not found" in response.json()["detail"]
    logger.info("✓ Assignable users correctly fails for non-existent project")


def test_assignable_users_returns_correct_schema(
    client: TestClient,
    personal_project: models.Project,
    admin_user: models.User,
    auth_headers: dict
):
    """Test that assignable users returns correct user schema (id, name, email)."""
    logger.debug("Testing assignable users returns correct schema")

    response = client.get(
        f"/api/projects/{personal_project.id}/assignable-users",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) > 0, "Should have at least one user"

    # Verify schema of first user
    user = data[0]
    assert "id" in user, "User should have 'id' field"
    assert "name" in user, "User should have 'name' field"
    assert "email" in user, "User should have 'email' field"

    # Verify types
    assert isinstance(user["id"], int), "id should be integer"
    assert isinstance(user["name"], str), "name should be string"
    assert isinstance(user["email"], str), "email should be string"

    # Verify values match admin_user
    assert user["id"] == admin_user.id
    assert user["name"] == admin_user.name
    assert user["email"] == admin_user.email

    logger.info("✓ Assignable users correctly returns user schema")
