"""
Tests for project team transfer endpoint (PUT /api/projects/{id}/transfer).

Tests cover:
- Authorization (401, 403, 200 for admin)
- Validation (404s, 400s)
- Team → Personal migration
- Personal → Team migration
- Team → Team migration
- Edge cases
"""

import logging
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import models
from tests.conftest import create_auth_token

logger = logging.getLogger(__name__)


# ============== Authorization Tests (4 tests) ==============


def test_transfer_without_authentication(client: TestClient, personal_project: models.Project):
    """Test that transfer fails without authentication (401)."""
    logger.debug("Testing transfer without authentication")

    response = client.put(
        f"/api/projects/{personal_project.id}/transfer",
        json={"team_id": None}
    )

    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.json()}"
    logger.info("✓ Transfer correctly rejected without authentication")


def test_transfer_not_project_owner(
    client: TestClient,
    personal_project: models.Project,
    regular_user: models.User,
    test_db: Session
):
    """Test that transfer fails if user is not project owner (403)."""
    logger.debug("Testing transfer by non-owner")

    # Add regular_user as editor (not owner)
    member = models.ProjectMember(
        project_id=personal_project.id,
        user_id=regular_user.id,
        role="editor"
    )
    test_db.add(member)
    test_db.commit()

    # Try to transfer as editor
    token = create_auth_token(regular_user)
    response = client.put(
        f"/api/projects/{personal_project.id}/transfer",
        json={"team_id": None},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.json()}"
    logger.info("✓ Transfer correctly rejected for non-owner")


def test_transfer_not_team_admin(
    client: TestClient,
    admin_user: models.User,
    regular_user: models.User,
    another_user: models.User,
    test_db: Session
):
    """Test that transfer to team fails if user is not team member (404 to avoid information leakage)."""
    logger.debug("Testing transfer to team without admin role")

    # Create a personal project owned by regular_user
    project = models.Project(
        name="Regular User Project",
        description="A personal project",
        author_id=regular_user.id,
        team_id=None
    )
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)

    # Add regular_user as owner
    member = models.ProjectMember(
        project_id=project.id,
        user_id=regular_user.id,
        role="owner"
    )
    test_db.add(member)
    test_db.commit()

    # Create a team with another_user as admin (regular_user is NOT a team member)
    team = models.Team(
        name="Team Without Admin",
        description="Test team",
        created_by=another_user.id
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    # Add another_user as team admin
    team_member = models.TeamMember(
        team_id=team.id,
        user_id=another_user.id,
        role="admin"
    )
    test_db.add(team_member)
    test_db.commit()

    # Try to transfer project as regular_user (project owner but NOT team member)
    token = create_auth_token(regular_user)
    response = client.put(
        f"/api/projects/{project.id}/transfer",
        json={"team_id": team.id},
        headers={"Authorization": f"Bearer {token}"}
    )

    # Returns 404 (not 403) to avoid revealing team existence to non-members
    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.json()}"
    assert "team not found" in response.json()["detail"].lower()
    logger.info("✓ Transfer correctly rejected when user is not team member")


def test_transfer_as_global_admin(
    client: TestClient,
    team_project: models.Project,
    admin_user: models.User,
    auth_headers: dict
):
    """Test that global admin can transfer any project (200)."""
    logger.debug("Testing transfer as global admin")

    # Transfer to personal (global admin bypasses project owner check)
    response = client.put(
        f"/api/projects/{team_project.id}/transfer",
        json={"team_id": None},
        headers=auth_headers
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["team_id"] is None
    logger.info("✓ Global admin can transfer projects")


# ============== Validation Tests (5 tests) ==============


def test_transfer_nonexistent_project(client: TestClient, auth_headers: dict):
    """Test that transfer fails for non-existent project (404)."""
    logger.debug("Testing transfer of non-existent project")

    response = client.put(
        "/api/projects/99999/transfer",
        json={"team_id": None},
        headers=auth_headers
    )

    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.json()}"
    logger.info("✓ Transfer correctly fails for non-existent project")


def test_transfer_to_nonexistent_team(
    client: TestClient,
    personal_project: models.Project,
    auth_headers: dict
):
    """Test that transfer fails for non-existent team (404)."""
    logger.debug("Testing transfer to non-existent team")

    response = client.put(
        f"/api/projects/{personal_project.id}/transfer",
        json={"team_id": 99999},
        headers=auth_headers
    )

    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.json()}"
    assert "team not found" in response.json()["detail"].lower()
    logger.info("✓ Transfer correctly fails for non-existent team")


def test_transfer_to_same_team(
    client: TestClient,
    team_project: models.Project,
    team: models.Team,
    auth_headers: dict
):
    """Test that transfer to same team is rejected (400)."""
    logger.debug("Testing transfer to same team")

    response = client.put(
        f"/api/projects/{team_project.id}/transfer",
        json={"team_id": team.id},
        headers=auth_headers
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.json()}"
    assert "already in this team" in response.json()["detail"]
    logger.info("✓ Transfer to same team correctly rejected")


def test_transfer_with_invalid_team_id(
    client: TestClient,
    personal_project: models.Project,
    auth_headers: dict
):
    """Test that transfer with invalid team_id is rejected (400)."""
    logger.debug("Testing transfer with invalid team_id")

    response = client.put(
        f"/api/projects/{personal_project.id}/transfer",
        json={"team_id": 0},
        headers=auth_headers
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.json()}"
    assert "Invalid team ID" in response.json()["detail"]
    logger.info("✓ Transfer with invalid team_id correctly rejected")


def test_transfer_with_task_owners_not_in_team(
    client: TestClient,
    personal_project: models.Project,
    team: models.Team,
    admin_user: models.User,
    regular_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that transfer auto-unassigns tasks with owners not in target team."""
    logger.debug("Testing transfer auto-unassigns task owners not in team")

    # Create task owned by regular_user (who is NOT in team)
    task = models.Task(
        title="Test Task",
        description="Task owned by non-team member",
        project_id=personal_project.id,
        author_id=admin_user.id,
        owner_id=regular_user.id,
        status=models.TaskStatus.todo
    )
    test_db.add(task)
    test_db.commit()
    task_id = task.id

    # Transfer project to team (should auto-unassign task)
    response = client.put(
        f"/api/projects/{personal_project.id}/transfer",
        json={"team_id": team.id},
        headers=auth_headers
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    # Verify task was auto-unassigned
    test_db.expire_all()
    task = test_db.query(models.Task).filter(models.Task.id == task_id).first()
    assert task.owner_id is None, f"Expected task to be unassigned, got owner_id={task.owner_id}"

    # Verify TaskEvent was created
    event = test_db.query(models.TaskEvent).filter(
        models.TaskEvent.task_id == task_id,
        models.TaskEvent.event_type == "ownership_change"
    ).order_by(models.TaskEvent.created_at.desc()).first()

    assert event is not None, "Expected ownership_change event to be created"
    assert event.old_value == str(regular_user.id), f"Expected old_value={str(regular_user.id)} (user ID as string for consistency)"
    assert event.new_value is None, "Expected new_value=None for unassignment"
    assert event.event_metadata["reason"] == "project_team_transfer"
    assert event.event_metadata["target_team_id"] == team.id
    assert event.event_metadata["original_owner_id"] == regular_user.id

    logger.info("✓ Transfer correctly auto-unassigns tasks with owners not in team")


# ============== Migration Tests - Team → Personal (4 tests) ==============


def test_team_to_personal_creates_project_member(
    client: TestClient,
    team_project: models.Project,
    admin_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that Team → Personal migration creates ProjectMember entry."""
    logger.debug("Testing Team → Personal: ProjectMember creation")

    # Verify no ProjectMember entries before transfer
    members_before = test_db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == team_project.id
    ).count()
    assert members_before == 0, "Expected no ProjectMembers for team project"

    # Transfer to personal
    response = client.put(
        f"/api/projects/{team_project.id}/transfer",
        json={"team_id": None},
        headers=auth_headers
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    # Verify ProjectMember created for admin_user
    test_db.expire_all()
    members_after = test_db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == team_project.id
    ).all()

    assert len(members_after) == 1, f"Expected 1 ProjectMember, found {len(members_after)}"
    assert members_after[0].user_id == admin_user.id
    logger.info("✓ Team → Personal correctly creates ProjectMember")


def test_team_to_personal_owner_role_mapping(
    client: TestClient,
    team_project: models.Project,
    admin_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that Team → Personal maps team admin to project owner role."""
    logger.debug("Testing Team → Personal: admin → owner role mapping")

    # Transfer to personal
    response = client.put(
        f"/api/projects/{team_project.id}/transfer",
        json={"team_id": None},
        headers=auth_headers
    )

    assert response.status_code == 200

    # Verify admin_user is now project owner
    test_db.expire_all()
    member = test_db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == team_project.id,
        models.ProjectMember.user_id == admin_user.id
    ).first()

    assert member is not None, "ProjectMember not found"
    assert member.role == "owner", f"Expected 'owner' role, got '{member.role}'"
    logger.info("✓ Team → Personal correctly maps admin → owner")


def test_team_to_personal_member_role_mapping(
    client: TestClient,
    team_project: models.Project,
    team: models.Team,
    admin_user: models.User,
    regular_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that Team → Personal maps team member to project editor role."""
    logger.debug("Testing Team → Personal: member → editor role mapping")

    # Add regular_user as team member
    team_member = models.TeamMember(
        team_id=team.id,
        user_id=regular_user.id,
        role="member"
    )
    test_db.add(team_member)
    test_db.commit()

    # Transfer to personal
    response = client.put(
        f"/api/projects/{team_project.id}/transfer",
        json={"team_id": None},
        headers=auth_headers
    )

    assert response.status_code == 200

    # Verify regular_user is now project editor
    test_db.expire_all()
    member = test_db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == team_project.id,
        models.ProjectMember.user_id == regular_user.id
    ).first()

    assert member is not None, "ProjectMember for regular_user not found"
    assert member.role == "editor", f"Expected 'editor' role, got '{member.role}'"
    logger.info("✓ Team → Personal correctly maps member → editor")


def test_team_to_personal_clears_team_id(
    client: TestClient,
    team_project: models.Project,
    test_db: Session,
    auth_headers: dict
):
    """Test that Team → Personal sets project.team_id to NULL."""
    logger.debug("Testing Team → Personal: team_id cleared")

    # Verify team_id is set before
    assert team_project.team_id is not None, "team_id should be set"

    # Transfer to personal
    response = client.put(
        f"/api/projects/{team_project.id}/transfer",
        json={"team_id": None},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["team_id"] is None, f"Expected team_id=None, got {data['team_id']}"

    # Verify in database
    test_db.expire_all()
    project = test_db.query(models.Project).filter(models.Project.id == team_project.id).first()
    assert project.team_id is None, "team_id should be NULL in database"
    logger.info("✓ Team → Personal correctly clears team_id")


# ============== Migration Tests - Personal → Team (3 tests) ==============


def test_personal_to_team_deletes_project_members(
    client: TestClient,
    personal_project: models.Project,
    team: models.Team,
    admin_user: models.User,
    regular_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that Personal → Team deletes all ProjectMember entries."""
    logger.debug("Testing Personal → Team: ProjectMember deletion")

    # Add regular_user as project member
    member = models.ProjectMember(
        project_id=personal_project.id,
        user_id=regular_user.id,
        role="editor"
    )
    test_db.add(member)
    test_db.commit()

    # Verify 2 ProjectMembers exist (admin_user + regular_user)
    members_before = test_db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == personal_project.id
    ).count()
    assert members_before == 2, f"Expected 2 ProjectMembers, found {members_before}"

    # Transfer to team
    response = client.put(
        f"/api/projects/{personal_project.id}/transfer",
        json={"team_id": team.id},
        headers=auth_headers
    )

    assert response.status_code == 200

    # Verify all ProjectMembers deleted
    test_db.expire_all()
    members_after = test_db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == personal_project.id
    ).count()
    assert members_after == 0, f"Expected 0 ProjectMembers, found {members_after}"
    logger.info("✓ Personal → Team correctly deletes all ProjectMembers")


def test_personal_to_team_sets_team_id(
    client: TestClient,
    personal_project: models.Project,
    team: models.Team,
    test_db: Session,
    auth_headers: dict
):
    """Test that Personal → Team sets project.team_id."""
    logger.debug("Testing Personal → Team: team_id set")

    # Verify team_id is NULL before
    assert personal_project.team_id is None, "team_id should be NULL"

    # Transfer to team
    response = client.put(
        f"/api/projects/{personal_project.id}/transfer",
        json={"team_id": team.id},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["team_id"] == team.id, f"Expected team_id={team.id}, got {data['team_id']}"

    # Verify in database
    test_db.expire_all()
    project = test_db.query(models.Project).filter(models.Project.id == personal_project.id).first()
    assert project.team_id == team.id, f"Expected team_id={team.id} in database"
    logger.info("✓ Personal → Team correctly sets team_id")


def test_personal_to_team_auto_unassigns_invalid_owners(
    client: TestClient,
    personal_project: models.Project,
    team: models.Team,
    admin_user: models.User,
    regular_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that Personal → Team auto-unassigns tasks with owners not in target team."""
    logger.debug("Testing Personal → Team: auto-unassign invalid owners")

    # Create task owned by regular_user (who is NOT in team)
    task = models.Task(
        title="Test Task",
        description="Task owned by non-team member",
        project_id=personal_project.id,
        author_id=admin_user.id,
        owner_id=regular_user.id,
        status=models.TaskStatus.todo
    )
    test_db.add(task)
    test_db.commit()
    task_id = task.id

    # Transfer to team (should auto-unassign)
    response = client.put(
        f"/api/projects/{personal_project.id}/transfer",
        json={"team_id": team.id},
        headers=auth_headers
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    # Verify task was auto-unassigned
    test_db.expire_all()
    task = test_db.query(models.Task).filter(models.Task.id == task_id).first()
    assert task.owner_id is None, f"Expected task to be unassigned, got owner_id={task.owner_id}"

    # Verify TaskEvent created with correct payload
    event = test_db.query(models.TaskEvent).filter(
        models.TaskEvent.task_id == task_id,
        models.TaskEvent.event_type == "ownership_change"
    ).first()

    assert event is not None, "Expected ownership_change event"
    assert event.new_value is None, "Expected new_value=None for unassignment"
    assert event.event_metadata["reason"] == "project_team_transfer"

    logger.info("✓ Personal → Team correctly auto-unassigns invalid owners")


# ============== Migration Tests - Team → Team (3 tests) ==============


def test_team_to_team_no_project_member_changes(
    client: TestClient,
    team_project: models.Project,
    another_team: models.Team,
    admin_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that Team → Team does not change ProjectMember entries."""
    logger.debug("Testing Team → Team: no ProjectMember changes")

    # Verify no ProjectMembers before (team projects don't use ProjectMember)
    members_before = test_db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == team_project.id
    ).count()
    assert members_before == 0, "Team projects should have no ProjectMembers"

    # Transfer to another team
    response = client.put(
        f"/api/projects/{team_project.id}/transfer",
        json={"team_id": another_team.id},
        headers=auth_headers
    )

    assert response.status_code == 200

    # Verify still no ProjectMembers
    test_db.expire_all()
    members_after = test_db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == team_project.id
    ).count()
    assert members_after == 0, "Team → Team should not create ProjectMembers"
    logger.info("✓ Team → Team correctly preserves no ProjectMembers")


def test_team_to_team_updates_team_id(
    client: TestClient,
    team_project: models.Project,
    team: models.Team,
    another_team: models.Team,
    test_db: Session,
    auth_headers: dict
):
    """Test that Team → Team updates project.team_id."""
    logger.debug("Testing Team → Team: team_id updated")

    # Verify initial team_id
    assert team_project.team_id == team.id, f"Expected team_id={team.id}"

    # Transfer to another team
    response = client.put(
        f"/api/projects/{team_project.id}/transfer",
        json={"team_id": another_team.id},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["team_id"] == another_team.id, f"Expected team_id={another_team.id}, got {data['team_id']}"

    # Verify in database
    test_db.expire_all()
    project = test_db.query(models.Project).filter(models.Project.id == team_project.id).first()
    assert project.team_id == another_team.id, f"Expected team_id={another_team.id} in database"
    logger.info("✓ Team → Team correctly updates team_id")


def test_team_to_team_auto_unassigns_invalid_owners(
    client: TestClient,
    team_project: models.Project,
    another_team: models.Team,
    admin_user: models.User,
    regular_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that Team → Team auto-unassigns tasks with owners not in new team."""
    logger.debug("Testing Team → Team: auto-unassigns invalid owners")

    # Create task owned by regular_user (who is NOT in another_team)
    task = models.Task(
        title="Test Task",
        description="Task owned by non-team member",
        project_id=team_project.id,
        author_id=admin_user.id,
        owner_id=regular_user.id,
        status=models.TaskStatus.todo
    )
    test_db.add(task)
    test_db.commit()
    task_id = task.id

    # Transfer to another_team (should auto-unassign)
    response = client.put(
        f"/api/projects/{team_project.id}/transfer",
        json={"team_id": another_team.id},
        headers=auth_headers
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    # Verify task was auto-unassigned
    test_db.expire_all()
    task = test_db.query(models.Task).filter(models.Task.id == task_id).first()
    assert task.owner_id is None, f"Expected task to be unassigned, got owner_id={task.owner_id}"

    logger.info("✓ Team → Team correctly auto-unassigns invalid owners")


# ============== Edge Cases (3 tests) ==============


def test_transfer_auto_unassigns_all_invalid_owners(
    client: TestClient,
    personal_project: models.Project,
    team: models.Team,
    admin_user: models.User,
    regular_user: models.User,
    another_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that transfer auto-unassigns ALL tasks with invalid owners."""
    logger.debug("Testing transfer auto-unassigns all invalid owners")

    # Create tasks owned by different users (not in team)
    task1 = models.Task(
        title="Task 1",
        project_id=personal_project.id,
        author_id=admin_user.id,
        owner_id=regular_user.id,
        status=models.TaskStatus.todo
    )
    task2 = models.Task(
        title="Task 2",
        project_id=personal_project.id,
        author_id=admin_user.id,
        owner_id=another_user.id,
        status=models.TaskStatus.todo
    )
    test_db.add_all([task1, task2])
    test_db.commit()
    task1_id = task1.id
    task2_id = task2.id

    # Transfer to team (should auto-unassign both tasks)
    response = client.put(
        f"/api/projects/{personal_project.id}/transfer",
        json={"team_id": team.id},
        headers=auth_headers
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    # Verify both tasks were auto-unassigned
    test_db.expire_all()
    task1 = test_db.query(models.Task).filter(models.Task.id == task1_id).first()
    task2 = test_db.query(models.Task).filter(models.Task.id == task2_id).first()

    assert task1.owner_id is None, f"Expected task1 to be unassigned, got owner_id={task1.owner_id}"
    assert task2.owner_id is None, f"Expected task2 to be unassigned, got owner_id={task2.owner_id}"

    # Verify TaskEvents created for both
    events = test_db.query(models.TaskEvent).filter(
        models.TaskEvent.task_id.in_([task1_id, task2_id]),
        models.TaskEvent.event_type == "ownership_change"
    ).all()

    assert len(events) == 2, f"Expected 2 ownership_change events, got {len(events)}"
    for event in events:
        assert event.new_value is None, "Expected new_value=None for unassignment"
        assert event.event_metadata["reason"] == "project_team_transfer"

    logger.info("✓ Transfer correctly auto-unassigns all invalid owners")


def test_transfer_keeps_valid_owners_assigned(
    client: TestClient,
    personal_project: models.Project,
    team: models.Team,
    admin_user: models.User,
    regular_user: models.User,
    test_db: Session,
    auth_headers: dict
):
    """Test that transfer keeps tasks assigned when owners ARE in target team."""
    logger.debug("Testing transfer keeps valid owners assigned")

    # Add regular_user to team
    team_member = models.TeamMember(
        team_id=team.id,
        user_id=regular_user.id,
        role="member"
    )
    test_db.add(team_member)

    # Create tasks with mixed ownership
    task_valid = models.Task(
        title="Valid Owner Task",
        project_id=personal_project.id,
        author_id=admin_user.id,
        owner_id=admin_user.id,  # admin IS in team
        status=models.TaskStatus.todo
    )
    task_also_valid = models.Task(
        title="Also Valid Owner Task",
        project_id=personal_project.id,
        author_id=admin_user.id,
        owner_id=regular_user.id,  # regular_user now in team
        status=models.TaskStatus.todo
    )
    test_db.add_all([task_valid, task_also_valid])
    test_db.commit()
    task_valid_id = task_valid.id
    task_also_valid_id = task_also_valid.id

    # Transfer to team
    response = client.put(
        f"/api/projects/{personal_project.id}/transfer",
        json={"team_id": team.id},
        headers=auth_headers
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    # Verify tasks still have their owners (NOT unassigned)
    test_db.expire_all()
    task_valid = test_db.query(models.Task).filter(models.Task.id == task_valid_id).first()
    task_also_valid = test_db.query(models.Task).filter(models.Task.id == task_also_valid_id).first()

    assert task_valid.owner_id == admin_user.id, "Task owned by team member should stay assigned"
    assert task_also_valid.owner_id == regular_user.id, "Task owned by team member should stay assigned"

    # Verify NO ownership_change events created for these tasks
    events = test_db.query(models.TaskEvent).filter(
        models.TaskEvent.task_id.in_([task_valid_id, task_also_valid_id]),
        models.TaskEvent.event_type == "ownership_change"
    ).count()

    assert events == 0, "No ownership_change events should be created for valid owners"

    logger.info("✓ Transfer correctly keeps valid owners assigned")


def test_transfer_works_with_no_tasks(
    client: TestClient,
    personal_project: models.Project,
    team: models.Team,
    test_db: Session,
    auth_headers: dict
):
    """Test that transfer works when project has no tasks."""
    logger.debug("Testing transfer with no tasks")

    # Verify no tasks
    tasks_count = test_db.query(models.Task).filter(
        models.Task.project_id == personal_project.id
    ).count()
    assert tasks_count == 0, "Project should have no tasks"

    # Transfer to team should succeed
    response = client.put(
        f"/api/projects/{personal_project.id}/transfer",
        json={"team_id": team.id},
        headers=auth_headers
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["team_id"] == team.id
    logger.info("✓ Transfer works with no tasks")


def test_transfer_preserves_project_data(
    client: TestClient,
    personal_project: models.Project,
    team: models.Team,
    test_db: Session,
    auth_headers: dict
):
    """Test that transfer preserves project name, description, and other data."""
    logger.debug("Testing transfer preserves project data")

    original_name = personal_project.name
    original_description = personal_project.description
    original_author_id = personal_project.author_id

    # Transfer to team
    response = client.put(
        f"/api/projects/{personal_project.id}/transfer",
        json={"team_id": team.id},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Verify data preserved
    assert data["name"] == original_name, "Project name should be preserved"
    assert data["description"] == original_description, "Project description should be preserved"
    assert data["author_id"] == original_author_id, "Project author_id should be preserved"
    logger.info("✓ Transfer correctly preserves project data")
