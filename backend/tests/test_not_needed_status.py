"""
Tests for not_needed terminal status semantics.

not_needed is treated as a terminal status alongside done in:
- Dependency blocking logic (not_needed blocker = unblocked)
- Completion validation (not_needed subtasks = complete for parent)
- Subtask progress calculation (not_needed counts toward completion %)
- Overdue detection (not_needed tasks are never overdue)
- Actionable tasks (not_needed tasks are excluded)
- Stats completion_rate (not_needed counts toward completion)
"""

import logging
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import models
from tests.conftest import create_auth_token

logger = logging.getLogger(__name__)


# ============== Fixtures ==============


@pytest.fixture
def project(test_db: Session, admin_user: models.User) -> models.Project:
    p = models.Project(name="Test Project", author_id=admin_user.id)
    test_db.add(p)
    test_db.commit()
    test_db.refresh(p)
    test_db.add(models.ProjectMember(project_id=p.id, user_id=admin_user.id, role="owner"))
    test_db.commit()
    return p


def make_task(db: Session, project_id: int, title: str, status: models.TaskStatus, **kwargs) -> models.Task:
    task = models.Task(project_id=project_id, title=title, status=status, **kwargs)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ============== Dependency / Blocking (3 tests) ==============


def test_not_needed_blocker_does_not_block(
    client: TestClient,
    test_db: Session,
    admin_user: models.User,
    project: models.Project
):
    """A task blocked only by a not_needed task should report is_blocked=False."""
    blocker = make_task(test_db, project.id, "Blocker", models.TaskStatus.not_needed)
    blocked = make_task(test_db, project.id, "Blocked", models.TaskStatus.todo)
    test_db.add(models.TaskDependency(blocking_task_id=blocker.id, blocked_task_id=blocked.id))
    test_db.commit()

    token = create_auth_token(admin_user)
    response = client.get(
        f"/api/tasks/{blocked.id}/dependencies",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, response.json()
    assert response.json()["is_blocked"] is False, "Task blocked only by not_needed should not be blocked"
    logger.info("✓ not_needed blocker correctly does not block dependent task")


def test_done_blocker_does_not_block(
    client: TestClient,
    test_db: Session,
    admin_user: models.User,
    project: models.Project
):
    """Sanity check: done blocker also does not block (parity with not_needed)."""
    blocker = make_task(test_db, project.id, "Blocker", models.TaskStatus.done)
    blocked = make_task(test_db, project.id, "Blocked", models.TaskStatus.todo)
    test_db.add(models.TaskDependency(blocking_task_id=blocker.id, blocked_task_id=blocked.id))
    test_db.commit()

    token = create_auth_token(admin_user)
    response = client.get(
        f"/api/tasks/{blocked.id}/dependencies",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, response.json()
    assert response.json()["is_blocked"] is False
    logger.info("✓ done blocker correctly does not block dependent task")


def test_in_progress_blocker_does_block(
    client: TestClient,
    test_db: Session,
    admin_user: models.User,
    project: models.Project
):
    """Sanity check: in_progress blocker still blocks."""
    blocker = make_task(test_db, project.id, "Blocker", models.TaskStatus.in_progress)
    blocked = make_task(test_db, project.id, "Blocked", models.TaskStatus.todo)
    test_db.add(models.TaskDependency(blocking_task_id=blocker.id, blocked_task_id=blocked.id))
    test_db.commit()

    token = create_auth_token(admin_user)
    response = client.get(
        f"/api/tasks/{blocked.id}/dependencies",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, response.json()
    assert response.json()["is_blocked"] is True
    logger.info("✓ in_progress blocker correctly blocks dependent task")


# ============== Completion Validation (3 tests) ==============


def test_parent_can_be_done_when_subtasks_are_not_needed(
    client: TestClient,
    test_db: Session,
    admin_user: models.User,
    project: models.Project
):
    """Parent task can be marked done when all subtasks are not_needed."""
    parent = make_task(test_db, project.id, "Parent", models.TaskStatus.in_progress)
    make_task(test_db, project.id, "Sub 1", models.TaskStatus.not_needed, parent_task_id=parent.id)
    make_task(test_db, project.id, "Sub 2", models.TaskStatus.not_needed, parent_task_id=parent.id)

    token = create_auth_token(admin_user)
    response = client.put(
        f"/api/tasks/{parent.id}",
        json={"status": "done"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    assert response.json()["status"] == "done"
    logger.info("✓ Parent correctly marked done with all not_needed subtasks")


def test_parent_can_be_done_with_mixed_done_and_not_needed_subtasks(
    client: TestClient,
    test_db: Session,
    admin_user: models.User,
    project: models.Project
):
    """Parent can be done when subtasks are a mix of done and not_needed."""
    parent = make_task(test_db, project.id, "Parent", models.TaskStatus.in_progress)
    make_task(test_db, project.id, "Sub done", models.TaskStatus.done, parent_task_id=parent.id)
    make_task(test_db, project.id, "Sub not needed", models.TaskStatus.not_needed, parent_task_id=parent.id)

    token = create_auth_token(admin_user)
    response = client.put(
        f"/api/tasks/{parent.id}",
        json={"status": "done"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    logger.info("✓ Parent correctly marked done with mixed done/not_needed subtasks")


def test_parent_cannot_be_done_with_todo_subtask(
    client: TestClient,
    test_db: Session,
    admin_user: models.User,
    project: models.Project
):
    """Parent cannot be marked done when a subtask is still todo."""
    parent = make_task(test_db, project.id, "Parent", models.TaskStatus.in_progress)
    make_task(test_db, project.id, "Sub not needed", models.TaskStatus.not_needed, parent_task_id=parent.id)
    make_task(test_db, project.id, "Sub todo", models.TaskStatus.todo, parent_task_id=parent.id)

    token = create_auth_token(admin_user)
    response = client.put(
        f"/api/tasks/{parent.id}",
        json={"status": "done"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.json()}"
    logger.info("✓ Parent correctly blocked from done when todo subtask exists alongside not_needed")


# ============== Progress Calculation (2 tests) ==============


def test_progress_counts_not_needed_as_complete(
    client: TestClient,
    test_db: Session,
    admin_user: models.User,
    project: models.Project
):
    """Progress endpoint counts not_needed subtasks as completed."""
    parent = make_task(test_db, project.id, "Parent", models.TaskStatus.in_progress)
    make_task(test_db, project.id, "Sub done", models.TaskStatus.done, parent_task_id=parent.id)
    make_task(test_db, project.id, "Sub not needed", models.TaskStatus.not_needed, parent_task_id=parent.id)
    make_task(test_db, project.id, "Sub todo", models.TaskStatus.todo, parent_task_id=parent.id)

    token = create_auth_token(admin_user)
    response = client.get(
        f"/api/tasks/{parent.id}/progress",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["total_subtasks"] == 3
    assert data["completed_subtasks"] == 2  # done + not_needed
    assert data["completion_percentage"] == pytest.approx(66.7, abs=0.1)
    logger.info("✓ Progress correctly counts not_needed as completed")


def test_progress_all_not_needed_is_100_percent(
    client: TestClient,
    test_db: Session,
    admin_user: models.User,
    project: models.Project
):
    """All not_needed subtasks = 100% completion."""
    parent = make_task(test_db, project.id, "Parent", models.TaskStatus.in_progress)
    make_task(test_db, project.id, "Sub 1", models.TaskStatus.not_needed, parent_task_id=parent.id)
    make_task(test_db, project.id, "Sub 2", models.TaskStatus.not_needed, parent_task_id=parent.id)

    token = create_auth_token(admin_user)
    response = client.get(
        f"/api/tasks/{parent.id}/progress",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["completed_subtasks"] == 2
    assert data["completion_percentage"] == 100.0
    logger.info("✓ All not_needed subtasks correctly reports 100% completion")


# ============== Overdue Detection (2 tests) ==============


def test_not_needed_task_excluded_from_overdue(
    client: TestClient,
    test_db: Session,
    admin_user: models.User,
    project: models.Project
):
    """not_needed tasks with past due dates are not included in overdue list."""
    past = datetime.now(timezone.utc) - timedelta(days=3)
    make_task(test_db, project.id, "Overdue not_needed", models.TaskStatus.not_needed, due_date=past)

    token = create_auth_token(admin_user)
    response = client.get(
        f"/api/tasks/overdue?project_id={project.id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, response.json()
    titles = [t["title"] for t in response.json()]
    assert "Overdue not_needed" not in titles, "not_needed task should not appear in overdue list"
    logger.info("✓ not_needed task correctly excluded from overdue list")


def test_todo_task_with_past_due_date_is_overdue(
    client: TestClient,
    test_db: Session,
    admin_user: models.User,
    project: models.Project
):
    """Sanity check: todo task with past due date IS overdue."""
    past = datetime.now(timezone.utc) - timedelta(days=3)
    make_task(test_db, project.id, "Overdue todo", models.TaskStatus.todo, due_date=past)

    token = create_auth_token(admin_user)
    response = client.get(
        f"/api/tasks/overdue?project_id={project.id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, response.json()
    titles = [t["title"] for t in response.json()]
    assert "Overdue todo" in titles
    logger.info("✓ todo task with past due date correctly appears in overdue list")


# ============== Stats completion_rate (2 tests) ==============


def test_stats_completion_rate_includes_not_needed(
    client: TestClient,
    test_db: Session,
    admin_user: models.User,
    project: models.Project
):
    """Stats completion_rate counts both done and not_needed tasks."""
    make_task(test_db, project.id, "Task done", models.TaskStatus.done)
    make_task(test_db, project.id, "Task not needed", models.TaskStatus.not_needed)
    make_task(test_db, project.id, "Task todo", models.TaskStatus.todo)
    make_task(test_db, project.id, "Task todo 2", models.TaskStatus.todo)

    token = create_auth_token(admin_user)
    response = client.get("/api/stats", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200, response.json()
    data = response.json()
    # 2 terminal (done + not_needed) out of 4 total = 50%
    assert data["completion_rate"] == pytest.approx(50.0, abs=0.1)
    assert data["not_needed_tasks"] == 1
    logger.info("✓ Stats completion_rate correctly includes not_needed tasks")


def test_stats_not_needed_key_present_with_no_projects(
    client: TestClient,
    admin_user: models.User
):
    """Stats endpoint returns not_needed_tasks=0 even when user has no projects."""
    token = create_auth_token(admin_user)
    response = client.get("/api/stats", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200, response.json()
    data = response.json()
    assert "not_needed_tasks" in data, "not_needed_tasks key must be present in zero-project response"
    assert data["not_needed_tasks"] == 0
    logger.info("✓ Stats zero-project response contains not_needed_tasks key")
