from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from collections import deque
import logging

from database import get_db, engine, Base
import models
import schemas

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create tables (only for development, init.sql handles this in production)
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Task Tracker API",
    description="A task tracking system with projects, tasks, and comments",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Note: Backend now runs on port 6001 (mapped from internal port 8000)


# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ============== Authors ==============

@app.get("/api/authors", response_model=List[schemas.Author])
def list_authors(db: Session = Depends(get_db)):
    return db.query(models.Author).all()


@app.post("/api/authors", response_model=schemas.Author)
def create_author(author: schemas.AuthorCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing = db.query(models.Author).filter(models.Author.email == author.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_author = models.Author(**author.model_dump())
    db.add(db_author)
    db.commit()
    db.refresh(db_author)
    return db_author


@app.get("/api/authors/{author_id}", response_model=schemas.Author)
def get_author(author_id: int, db: Session = Depends(get_db)):
    author = db.query(models.Author).filter(models.Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return author


@app.put("/api/authors/{author_id}", response_model=schemas.Author)
def update_author(author_id: int, author_update: schemas.AuthorUpdate, db: Session = Depends(get_db)):
    author = db.query(models.Author).filter(models.Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    update_data = author_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(author, key, value)

    db.commit()
    db.refresh(author)
    return author


@app.delete("/api/authors/{author_id}")
def delete_author(author_id: int, db: Session = Depends(get_db)):
    author = db.query(models.Author).filter(models.Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    db.delete(author)
    db.commit()
    return {"message": "Author deleted"}


# ============== Projects ==============

@app.get("/api/projects", response_model=List[schemas.Project])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).options(joinedload(models.Project.author)).all()
    return projects


@app.post("/api/projects", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@app.get("/api/projects/{project_id}", response_model=schemas.ProjectWithTasks)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project)\
        .options(
            joinedload(models.Project.author),
            joinedload(models.Project.tasks).joinedload(models.Task.author),
            joinedload(models.Project.tasks).joinedload(models.Task.owner),
            joinedload(models.Project.tasks).joinedload(models.Task.comments)
        )\
        .filter(models.Project.id == project_id)\
        .first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Bulk calculate is_blocked for all tasks to avoid N+1 queries
    task_ids = [task.id for task in project.tasks]
    is_blocked_map = bulk_calculate_is_blocked(db, task_ids)

    # Add comment count and is_blocked to each task
    project_dict = {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "author_id": project.author_id,
        "author": project.author,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "tasks": [
            {
                **{k: v for k, v in task.__dict__.items() if not k.startswith('_')},
                "comment_count": len(task.comments),
                "is_blocked": is_blocked_map.get(task.id, False)
            }
            for task in project.tasks
        ]
    }

    return project_dict


@app.get("/api/projects/{project_id}/stats", response_model=schemas.ProjectStats)
def get_project_stats(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = db.query(models.Task).filter(models.Task.project_id == project_id).all()

    return schemas.ProjectStats(
        id=project.id,
        name=project.name,
        total_tasks=len(tasks),
        pending_tasks=sum(1 for t in tasks if t.status == models.TaskStatus.pending),
        completed_tasks=sum(1 for t in tasks if t.status == models.TaskStatus.completed),
        p0_tasks=sum(1 for t in tasks if t.priority == models.TaskPriority.P0),
        p1_tasks=sum(1 for t in tasks if t.priority == models.TaskPriority.P1),
        bug_count=sum(1 for t in tasks if t.tag == models.TaskTag.bug),
        feature_count=sum(1 for t in tasks if t.tag == models.TaskTag.feature),
        idea_count=sum(1 for t in tasks if t.tag == models.TaskTag.idea)
    )


@app.put("/api/projects/{project_id}", response_model=schemas.Project)
def update_project(project_id: int, project_update: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


# ============== Helper Functions ==============

def has_circular_subtask(db: Session, task_id: int, parent_task_id: int) -> bool:
    """
    Check if creating a subtask relationship would create a cycle.
    Uses BFS to traverse the subtask tree of task_id to check if parent_task_id
    appears in any of its descendants.

    Returns True if parent_task_id is found in the subtask tree (would create cycle).
    """
    logger.debug(f"Checking circular subtask: task_id={task_id}, parent_task_id={parent_task_id}")

    if task_id == parent_task_id:
        logger.info(f"Self-reference detected: task {task_id} cannot be its own parent")
        return True  # Self-reference

    visited = set()
    queue = deque([task_id])

    while queue:
        current_id = queue.popleft()

        if current_id in visited:
            continue
        visited.add(current_id)

        # If we found the parent_task_id in the subtask tree, we have a cycle
        if current_id == parent_task_id:
            logger.info(f"Circular subtask detected: task {parent_task_id} is a descendant of task {task_id}")
            return True

        # Get all subtasks of the current task
        subtasks = db.query(models.Task).filter(models.Task.parent_task_id == current_id).all()
        logger.debug(f"Task {current_id} has {len(subtasks)} subtask(s)")

        for subtask in subtasks:
            queue.append(subtask.id)

    logger.debug(f"No circular subtask detected for task {task_id} with parent {parent_task_id}")
    return False


def has_circular_dependency(db: Session, blocking_task_id: int, blocked_task_id: int) -> bool:
    """
    Check if adding a dependency would create a circular dependency.
    Uses BFS to traverse the dependency graph.

    Returns True if adding blocking_task_id -> blocked_task_id would create a cycle.
    """
    logger.debug(f"Checking circular dependency: blocking_task_id={blocking_task_id}, blocked_task_id={blocked_task_id}")

    # If a task blocks itself, that's a circular dependency
    if blocking_task_id == blocked_task_id:
        logger.info(f"Self-blocking detected: task {blocking_task_id} cannot block itself")
        return True

    # Use BFS to check if blocked_task_id already blocks blocking_task_id (directly or indirectly)
    # If it does, adding blocking_task_id -> blocked_task_id would create a cycle
    visited = set()
    queue = deque([blocked_task_id])

    while queue:
        current_task_id = queue.popleft()

        if current_task_id in visited:
            continue
        visited.add(current_task_id)

        logger.debug(f"Checking dependencies for task {current_task_id}")

        # Get all tasks that current_task blocks
        dependencies = db.query(models.TaskDependency)\
            .filter(models.TaskDependency.blocking_task_id == current_task_id)\
            .all()

        logger.debug(f"Task {current_task_id} blocks {len(dependencies)} task(s)")

        for dep in dependencies:
            # If we find that blocked_task_id eventually blocks blocking_task_id,
            # then adding blocking_task_id -> blocked_task_id would create a cycle
            if dep.blocked_task_id == blocking_task_id:
                logger.info(f"Circular dependency detected: task {blocked_task_id} already blocks task {blocking_task_id} indirectly")
                return True
            queue.append(dep.blocked_task_id)

    logger.debug(f"No circular dependency detected for blocking_task_id={blocking_task_id}, blocked_task_id={blocked_task_id}")
    return False


def calculate_is_blocked(db: Session, task_id: int) -> bool:
    """
    Calculate if a task is blocked by checking if it has any blocking dependencies
    with status=pending.

    Returns True if task has any pending blocking dependencies, False otherwise.
    """
    logger.debug(f"Calculating is_blocked for task {task_id}")

    # Get blocking dependencies for this task
    blocking_deps = db.query(models.TaskDependency)\
        .filter(models.TaskDependency.blocked_task_id == task_id)\
        .all()

    if not blocking_deps:
        logger.debug(f"Task {task_id} has no blocking dependencies")
        return False

    # Get the blocking tasks
    blocking_task_ids = [dep.blocking_task_id for dep in blocking_deps]
    blocking_tasks = db.query(models.Task)\
        .filter(models.Task.id.in_(blocking_task_ids))\
        .all()

    # Check if any blocking task is pending
    is_blocked = any(bt.status == models.TaskStatus.pending for bt in blocking_tasks)
    logger.debug(f"Task {task_id} is_blocked={is_blocked} ({len([bt for bt in blocking_tasks if bt.status == models.TaskStatus.pending])} pending blockers)")

    return is_blocked


def is_ancestor_in_subtask_tree(db: Session, potential_ancestor_id: int, task_id: int) -> bool:
    """
    Check if potential_ancestor_id is an ancestor of task_id in the subtask hierarchy.
    Traverses up the parent chain from task_id to see if we reach potential_ancestor_id.

    Returns True if potential_ancestor_id is an ancestor (parent, grandparent, etc.) of task_id.
    """
    logger.debug(f"Checking if task {potential_ancestor_id} is ancestor of task {task_id}")

    current_id = task_id
    visited = set()  # Prevent infinite loops in case of data corruption

    while current_id is not None:
        if current_id in visited:
            logger.warning(f"Circular parent chain detected involving task {current_id}")
            break
        visited.add(current_id)

        # Get current task
        current_task = db.query(models.Task).filter(models.Task.id == current_id).first()
        if not current_task:
            break

        # Check if we've reached the potential ancestor
        if current_task.parent_task_id == potential_ancestor_id:
            logger.info(f"Task {potential_ancestor_id} is an ancestor of task {task_id}")
            return True

        # Move up to parent
        current_id = current_task.parent_task_id

    logger.debug(f"Task {potential_ancestor_id} is not an ancestor of task {task_id}")
    return False


def bulk_calculate_is_blocked(db: Session, task_ids: list[int]) -> dict[int, bool]:
    """
    Calculate is_blocked for multiple tasks in bulk to avoid N+1 queries.
    Returns a dict mapping task_id -> is_blocked.

    This function:
    1. Fetches all dependencies for the given tasks in one query
    2. Fetches all blocking task statuses in one query
    3. Computes is_blocked in memory
    """
    if not task_ids:
        return {}

    logger.debug(f"Bulk calculating is_blocked for {len(task_ids)} tasks")

    # Get all blocking dependencies for these tasks
    dependencies = db.query(models.TaskDependency)\
        .filter(models.TaskDependency.blocked_task_id.in_(task_ids))\
        .all()

    if not dependencies:
        # No dependencies means no tasks are blocked
        return {task_id: False for task_id in task_ids}

    # Get all blocking task IDs and their statuses
    blocking_task_ids = list(set(dep.blocking_task_id for dep in dependencies))
    blocking_tasks = db.query(models.Task)\
        .filter(models.Task.id.in_(blocking_task_ids))\
        .all()

    # Create a map of blocking_task_id -> status
    blocking_status_map = {task.id: task.status for task in blocking_tasks}

    # Build a map of blocked_task_id -> list of blocking task statuses
    blocked_by_map = {}
    for dep in dependencies:
        blocked_task_id = dep.blocked_task_id
        blocking_task_id = dep.blocking_task_id
        blocking_status = blocking_status_map.get(blocking_task_id)

        if blocked_task_id not in blocked_by_map:
            blocked_by_map[blocked_task_id] = []
        blocked_by_map[blocked_task_id].append(blocking_status)

    # Calculate is_blocked for each task
    result = {}
    for task_id in task_ids:
        if task_id in blocked_by_map:
            # Task is blocked if any of its blocking tasks are pending
            result[task_id] = any(
                status == models.TaskStatus.pending
                for status in blocked_by_map[task_id]
            )
        else:
            # No blocking dependencies
            result[task_id] = False

    logger.debug(f"Bulk calculation complete: {sum(result.values())} of {len(task_ids)} tasks are blocked")
    return result


# ============== Tasks ==============

@app.get("/api/tasks", response_model=List[schemas.TaskSummary])
def list_tasks(
    project_id: Optional[int] = Query(None),
    status: Optional[schemas.TaskStatus] = Query(None),
    priority: Optional[schemas.TaskPriority] = Query(None),
    tag: Optional[schemas.TaskTag] = Query(None),
    owner_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(models.Task).options(
        joinedload(models.Task.author),
        joinedload(models.Task.owner),
        joinedload(models.Task.comments)
    )

    if project_id:
        query = query.filter(models.Task.project_id == project_id)
    if status:
        query = query.filter(models.Task.status == status)
    if priority:
        query = query.filter(models.Task.priority == priority)
    if tag:
        query = query.filter(models.Task.tag == tag)
    if owner_id is not None:
        query = query.filter(models.Task.owner_id == owner_id)

    tasks = query.all()

    # Bulk calculate is_blocked for all tasks to avoid N+1 queries
    task_ids = [task.id for task in tasks]
    is_blocked_map = bulk_calculate_is_blocked(db, task_ids)

    # Add comment count and is_blocked
    result = []
    for task in tasks:
        task_dict = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "tag": task.tag,
            "priority": task.priority,
            "status": task.status,
            "project_id": task.project_id,
            "author_id": task.author_id,
            "author": task.author,
            "owner_id": task.owner_id,
            "owner": task.owner,
            "parent_task_id": task.parent_task_id,
            "comment_count": len(task.comments),
            "is_blocked": is_blocked_map.get(task.id, False),
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        result.append(task_dict)

    return result


@app.post("/api/tasks", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating task: {task.title} in project {task.project_id}")

    # Verify project exists
    project = db.query(models.Project).filter(models.Project.id == task.project_id).first()
    if not project:
        logger.critical(f"Project {task.project_id} not found")
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate parent_task_id if provided
    if task.parent_task_id is not None:
        logger.debug(f"Validating parent task {task.parent_task_id}")

        # Reject invalid IDs (0 or negative)
        if task.parent_task_id <= 0:
            logger.info(f"Invalid parent task ID: {task.parent_task_id}")
            raise HTTPException(status_code=400, detail="Invalid parent task ID")

        parent_task = db.query(models.Task).filter(models.Task.id == task.parent_task_id).first()
        if not parent_task:
            logger.critical(f"Parent task {task.parent_task_id} not found")
            raise HTTPException(status_code=404, detail="Parent task not found")

        # Ensure parent task is in the same project
        if parent_task.project_id != task.project_id:
            logger.info(f"Parent task {task.parent_task_id} is in different project: {parent_task.project_id} vs {task.project_id}")
            raise HTTPException(
                status_code=400,
                detail="Parent task must be in the same project"
            )
        logger.debug(f"Parent task validation successful")

    db_task = models.Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    logger.info(f"Task created successfully: id={db_task.id}")
    return db_task


@app.get("/api/tasks/actionable", response_model=List[schemas.TaskSummary])
def get_actionable_tasks(
    project_id: Optional[int] = Query(None),
    owner_id: Optional[int] = Query(None),
    priority: Optional[schemas.TaskPriority] = Query(None),
    tag: Optional[schemas.TaskTag] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Query unblocked, pending tasks.
    Returns tasks with status=pending that have no blocking dependencies
    or all blocking tasks are completed.
    """
    logger.debug(f"Getting actionable tasks with filters: project_id={project_id}, owner_id={owner_id}, priority={priority}, tag={tag}")

    # Start with pending tasks
    query = db.query(models.Task)\
        .options(
            joinedload(models.Task.author),
            joinedload(models.Task.owner),
            joinedload(models.Task.comments)
        )\
        .filter(models.Task.status == models.TaskStatus.pending)

    # Apply optional filters
    if project_id:
        query = query.filter(models.Task.project_id == project_id)
    if owner_id is not None:
        query = query.filter(models.Task.owner_id == owner_id)
    if priority:
        query = query.filter(models.Task.priority == priority)
    if tag:
        query = query.filter(models.Task.tag == tag)

    tasks = query.all()
    logger.debug(f"Found {len(tasks)} pending tasks before filtering blocked tasks")

    # Filter out blocked tasks
    actionable_tasks = []
    for task in tasks:
        logger.debug(f"Checking if task {task.id} is actionable")

        # Get blocking dependencies
        blocking_deps = db.query(models.TaskDependency)\
            .filter(models.TaskDependency.blocked_task_id == task.id)\
            .all()

        if not blocking_deps:
            # No blocking dependencies, task is actionable
            logger.debug(f"Task {task.id} has no blocking dependencies, is actionable")
            actionable_tasks.append(task)
        else:
            # Check if all blocking tasks are completed
            blocking_task_ids = [dep.blocking_task_id for dep in blocking_deps]
            blocking_tasks = db.query(models.Task)\
                .filter(models.Task.id.in_(blocking_task_ids))\
                .all()

            logger.debug(f"Task {task.id} has {len(blocking_tasks)} blocking task(s)")

            # Task is actionable if all blocking tasks are completed
            if all(bt.status == models.TaskStatus.completed for bt in blocking_tasks):
                logger.debug(f"Task {task.id} is actionable, all blocking tasks completed")
                actionable_tasks.append(task)
            else:
                logger.debug(f"Task {task.id} is blocked by {sum(1 for bt in blocking_tasks if bt.status == models.TaskStatus.pending)} pending task(s)")

    logger.info(f"Found {len(actionable_tasks)} actionable tasks")

    # Convert to summary format with comment_count
    result = []
    for task in actionable_tasks:
        task_dict = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "tag": task.tag,
            "priority": task.priority,
            "status": task.status,
            "project_id": task.project_id,
            "author_id": task.author_id,
            "author": task.author,
            "owner_id": task.owner_id,
            "owner": task.owner,
            "parent_task_id": task.parent_task_id,
            "comment_count": len(task.comments),
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        result.append(task_dict)

    logger.critical(f"Successfully retrieved {len(result)} actionable tasks")
    return result


@app.get("/api/tasks/{task_id}", response_model=schemas.Task)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task)\
        .options(
            joinedload(models.Task.author),
            joinedload(models.Task.owner),
            joinedload(models.Task.comments).joinedload(models.Comment.author)
        )\
        .filter(models.Task.id == task_id)\
        .first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Calculate is_blocked field
    is_blocked = calculate_is_blocked(db, task_id)

    # Build response with is_blocked
    task_dict = {
        **{k: v for k, v in task.__dict__.items() if not k.startswith('_')},
        "is_blocked": is_blocked
    }

    return task_dict


@app.get("/api/tasks/{task_id}/subtasks", response_model=List[schemas.TaskSummary])
def get_task_subtasks(task_id: int, db: Session = Depends(get_db)):
    """Get all subtasks of a task."""
    logger.info(f"Fetching subtasks for task {task_id}")

    # Verify parent task exists
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        logger.critical(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")

    # Get all subtasks
    subtasks = db.query(models.Task)\
        .options(
            joinedload(models.Task.author),
            joinedload(models.Task.owner),
            joinedload(models.Task.comments)
        )\
        .filter(models.Task.parent_task_id == task_id)\
        .all()

    logger.debug(f"Found {len(subtasks)} subtask(s) for task {task_id}")

    # Add comment count and compute is_blocked
    result = []
    for subtask in subtasks:
        # Calculate is_blocked for each subtask
        is_blocked = calculate_is_blocked(db, subtask.id)

        task_dict = {
            "id": subtask.id,
            "title": subtask.title,
            "description": subtask.description,
            "tag": subtask.tag,
            "priority": subtask.priority,
            "status": subtask.status,
            "project_id": subtask.project_id,
            "author_id": subtask.author_id,
            "author": subtask.author,
            "owner_id": subtask.owner_id,
            "owner": subtask.owner,
            "parent_task_id": subtask.parent_task_id,
            "comment_count": len(subtask.comments),
            "is_blocked": is_blocked,
            "created_at": subtask.created_at,
            "updated_at": subtask.updated_at
        }
        result.append(task_dict)

    return result


@app.get("/api/tasks/{task_id}/progress", response_model=schemas.TaskProgress)
def get_task_progress(task_id: int, db: Session = Depends(get_db)):
    """Get completion percentage based on subtasks."""
    logger.info(f"Calculating progress for task {task_id}")

    # Verify task exists
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        logger.critical(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")

    # Get all subtasks
    subtasks = db.query(models.Task).filter(models.Task.parent_task_id == task_id).all()

    total_subtasks = len(subtasks)
    completed_subtasks = sum(1 for s in subtasks if s.status == models.TaskStatus.completed)

    completion_percentage = (completed_subtasks / total_subtasks * 100) if total_subtasks > 0 else 0.0

    logger.debug(f"Task {task_id} progress: {completed_subtasks}/{total_subtasks} subtasks completed ({completion_percentage}%)")

    return schemas.TaskProgress(
        task_id=task_id,
        total_subtasks=total_subtasks,
        completed_subtasks=completed_subtasks,
        completion_percentage=round(completion_percentage, 1)
    )


@app.put("/api/tasks/{task_id}", response_model=schemas.Task)
def update_task(task_id: int, task_update: schemas.TaskUpdate, db: Session = Depends(get_db)):
    logger.info(f"Updating task {task_id}")
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        logger.critical(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_update.model_dump(exclude_unset=True)

    # Validate status change to completed
    if 'status' in update_data and update_data['status'] == models.TaskStatus.completed:
        logger.debug(f"Validating completion of task {task_id}")

        # Check if task has pending subtasks
        pending_subtasks = db.query(models.Task).filter(
            models.Task.parent_task_id == task_id,
            models.Task.status == models.TaskStatus.pending
        ).count()

        if pending_subtasks > 0:
            logger.info(f"Task {task_id} cannot be completed: has {pending_subtasks} pending subtask(s)")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot complete task with {pending_subtasks} pending subtask(s)"
            )

        # Check if task is blocked by other tasks
        is_blocked = calculate_is_blocked(db, task_id)
        if is_blocked:
            logger.info(f"Task {task_id} cannot be completed: is blocked by pending dependencies")
            raise HTTPException(
                status_code=400,
                detail="Cannot complete task while it is blocked by pending dependencies"
            )

        logger.debug(f"Task {task_id} can be completed")

    # Validate parent_task_id change
    if 'parent_task_id' in update_data and update_data['parent_task_id'] is not None:
        parent_task_id = update_data['parent_task_id']
        logger.debug(f"Validating parent task change for task {task_id} to parent {parent_task_id}")

        # Verify parent task exists
        parent_task = db.query(models.Task).filter(models.Task.id == parent_task_id).first()
        if not parent_task:
            logger.critical(f"Parent task {parent_task_id} not found")
            raise HTTPException(status_code=404, detail="Parent task not found")

        # Ensure parent task is in the same project
        if parent_task.project_id != task.project_id:
            logger.info(f"Parent task {parent_task_id} is in different project: {parent_task.project_id} vs {task.project_id}")
            raise HTTPException(
                status_code=400,
                detail="Parent task must be in the same project"
            )

        # Check for circular subtask relationship
        if has_circular_subtask(db, task_id, parent_task_id):
            logger.info(f"Circular subtask relationship detected for task {task_id} with parent {parent_task_id}")
            raise HTTPException(
                status_code=400,
                detail="Cannot create circular subtask relationship"
            )
        logger.debug(f"Parent task validation successful")

    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)

    # Calculate is_blocked field (task state may have changed)
    is_blocked = calculate_is_blocked(db, task_id)

    # Build response with computed is_blocked
    task_dict = {
        **{k: v for k, v in task.__dict__.items() if not k.startswith('_')},
        "is_blocked": is_blocked
    }

    logger.info(f"Task {task_id} updated successfully")
    return task_dict


@app.post("/api/tasks/{task_id}/take-ownership", response_model=schemas.Task)
def take_ownership(task_id: int, ownership: schemas.TakeOwnership, db: Session = Depends(get_db)):
    # Get the task
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify author exists
    author = db.query(models.Author).filter(models.Author.id == ownership.author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    # Check if task already has an owner
    if task.owner_id is not None and not ownership.force:
        raise HTTPException(
            status_code=400,
            detail=f"Task already owned by author ID {task.owner_id}. Use force=true to reassign."
        )

    # Assign ownership
    task.owner_id = ownership.author_id
    db.commit()

    # Refresh and load relationships
    db.refresh(task)
    task = db.query(models.Task)\
        .options(
            joinedload(models.Task.author),
            joinedload(models.Task.owner),
            joinedload(models.Task.comments).joinedload(models.Comment.author)
        )\
        .filter(models.Task.id == task_id)\
        .first()

    return task


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}


# ============== Comments ==============

@app.get("/api/tasks/{task_id}/comments", response_model=List[schemas.Comment])
def list_comments(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    comments = db.query(models.Comment)\
        .options(joinedload(models.Comment.author))\
        .filter(models.Comment.task_id == task_id)\
        .order_by(models.Comment.created_at.desc())\
        .all()

    return comments


@app.post("/api/tasks/{task_id}/comments", response_model=schemas.Comment)
def create_comment(task_id: int, comment: schemas.CommentCreate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db_comment = models.Comment(
        content=comment.content,
        task_id=task_id,
        author_id=comment.author_id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    # Load author relationship
    db_comment = db.query(models.Comment)\
        .options(joinedload(models.Comment.author))\
        .filter(models.Comment.id == db_comment.id)\
        .first()

    return db_comment


@app.put("/api/comments/{comment_id}", response_model=schemas.Comment)
def update_comment(comment_id: int, comment_update: schemas.CommentUpdate, db: Session = Depends(get_db)):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    update_data = comment_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(comment, key, value)

    db.commit()
    db.refresh(comment)
    return comment


@app.delete("/api/comments/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted"}


# ============== Dashboard Stats ==============

@app.get("/api/stats")
def get_overall_stats(db: Session = Depends(get_db)):
    total_projects = db.query(models.Project).count()
    total_tasks = db.query(models.Task).count()
    pending_tasks = db.query(models.Task).filter(models.Task.status == models.TaskStatus.pending).count()
    completed_tasks = db.query(models.Task).filter(models.Task.status == models.TaskStatus.completed).count()

    p0_pending = db.query(models.Task).filter(
        models.Task.status == models.TaskStatus.pending,
        models.Task.priority == models.TaskPriority.P0
    ).count()

    return {
        "total_projects": total_projects,
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "completed_tasks": completed_tasks,
        "p0_pending": p0_pending,
        "completion_rate": round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
    }


# ============== Task Dependencies ==============

@app.get("/api/tasks/{task_id}/dependencies", response_model=schemas.TaskWithDependencies)
def get_task_dependencies(task_id: int, db: Session = Depends(get_db)):
    """Get task with all dependency information."""
    logger.debug(f"Getting task dependencies for task_id={task_id}")

    task = db.query(models.Task)\
        .options(
            joinedload(models.Task.author),
            joinedload(models.Task.owner),
            joinedload(models.Task.comments).joinedload(models.Comment.author),
            joinedload(models.Task.subtasks),
            joinedload(models.Task.blocking_dependencies),
            joinedload(models.Task.blocked_dependencies)
        )\
        .filter(models.Task.id == task_id)\
        .first()

    if not task:
        logger.info(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")

    logger.debug(f"Task {task_id} found with {len(task.blocked_dependencies)} blocking dependencies and {len(task.blocking_dependencies)} blocked dependencies")

    # Get subtasks
    subtasks = db.query(models.Task)\
        .options(
            joinedload(models.Task.author),
            joinedload(models.Task.owner),
            joinedload(models.Task.comments)
        )\
        .filter(models.Task.parent_task_id == task_id)\
        .all()

    logger.debug(f"Task {task_id} has {len(subtasks)} subtask(s)")

    # Get blocking tasks (tasks that block this one)
    blocking_task_ids = [dep.blocking_task_id for dep in task.blocked_dependencies]
    blocking_tasks = []
    if blocking_task_ids:
        blocking_tasks = db.query(models.Task)\
            .options(
                joinedload(models.Task.author),
                joinedload(models.Task.owner),
                joinedload(models.Task.comments)
            )\
            .filter(models.Task.id.in_(blocking_task_ids))\
            .all()

    logger.debug(f"Found {len(blocking_tasks)} blocking task(s)")

    # Get blocked tasks (tasks that this one blocks)
    blocked_task_ids = [dep.blocked_task_id for dep in task.blocking_dependencies]
    blocked_tasks = []
    if blocked_task_ids:
        blocked_tasks = db.query(models.Task)\
            .options(
                joinedload(models.Task.author),
                joinedload(models.Task.owner),
                joinedload(models.Task.comments)
            )\
            .filter(models.Task.id.in_(blocked_task_ids))\
            .all()

    logger.debug(f"Found {len(blocked_tasks)} blocked task(s)")

    # Calculate is_blocked: task is blocked if it has any blocking dependencies with status=pending
    is_blocked = any(bt.status == models.TaskStatus.pending for bt in blocking_tasks)
    logger.info(f"Task {task_id} is_blocked={is_blocked}")

    # Convert to summary format with comment_count and is_blocked
    subtasks_summary = [
        {
            **{k: v for k, v in subtask.__dict__.items() if not k.startswith('_')},
            "comment_count": len(subtask.comments),
            "is_blocked": calculate_is_blocked(db, subtask.id)
        }
        for subtask in subtasks
    ]

    blocking_tasks_summary = [
        {
            **{k: v for k, v in bt.__dict__.items() if not k.startswith('_')},
            "comment_count": len(bt.comments),
            "is_blocked": calculate_is_blocked(db, bt.id)
        }
        for bt in blocking_tasks
    ]

    blocked_tasks_summary = [
        {
            **{k: v for k, v in bt.__dict__.items() if not k.startswith('_')},
            "comment_count": len(bt.comments),
            "is_blocked": calculate_is_blocked(db, bt.id)
        }
        for bt in blocked_tasks
    ]

    # Build response
    response = {
        **{k: v for k, v in task.__dict__.items() if not k.startswith('_')},
        "subtasks": subtasks_summary,
        "blocking_tasks": blocking_tasks_summary,
        "blocked_tasks": blocked_tasks_summary,
        "is_blocked": is_blocked
    }

    logger.critical(f"Successfully retrieved task dependencies for task {task_id}")
    return response


@app.post("/api/tasks/{task_id}/dependencies", response_model=schemas.TaskDependency)
def add_task_dependency(task_id: int, dependency: schemas.TaskDependencyCreate, db: Session = Depends(get_db)):
    """Add a blocking relationship between tasks."""
    logger.debug(f"Adding dependency: blocking_task_id={dependency.blocking_task_id}, blocked_task_id={task_id}")

    # Get the blocked task (the one being blocked)
    blocked_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not blocked_task:
        logger.info(f"Blocked task {task_id} not found")
        raise HTTPException(status_code=404, detail="Blocked task not found")

    # Get the blocking task
    blocking_task = db.query(models.Task).filter(models.Task.id == dependency.blocking_task_id).first()
    if not blocking_task:
        logger.info(f"Blocking task {dependency.blocking_task_id} not found")
        raise HTTPException(status_code=404, detail="Blocking task not found")

    logger.debug(f"Both tasks found: blocked={blocked_task.id} (project {blocked_task.project_id}), blocking={blocking_task.id} (project {blocking_task.project_id})")

    # Validate: both tasks must be in the same project
    if blocked_task.project_id != blocking_task.project_id:
        logger.info(f"Tasks in different projects: {blocked_task.project_id} vs {blocking_task.project_id}")
        raise HTTPException(
            status_code=400,
            detail="Tasks must be in the same project to create a dependency"
        )

    # Check if dependency already exists
    existing = db.query(models.TaskDependency)\
        .filter(
            models.TaskDependency.blocking_task_id == dependency.blocking_task_id,
            models.TaskDependency.blocked_task_id == task_id
        )\
        .first()

    if existing:
        logger.info(f"Dependency already exists: {dependency.blocking_task_id} -> {task_id}")
        raise HTTPException(status_code=400, detail="Dependency already exists")

    # Check for circular dependencies
    if has_circular_dependency(db, dependency.blocking_task_id, task_id):
        logger.info(f"Circular dependency detected when trying to add {dependency.blocking_task_id} -> {task_id}")
        raise HTTPException(
            status_code=400,
            detail="Cannot create dependency: would create a circular dependency"
        )

    # Check for parent-subtask deadlock
    # Prevent a parent task from blocking its own subtask (creates impossible completion state)
    if is_ancestor_in_subtask_tree(db, dependency.blocking_task_id, task_id):
        logger.info(f"Parent-subtask deadlock detected: task {dependency.blocking_task_id} is an ancestor of task {task_id}")
        raise HTTPException(
            status_code=400,
            detail="Cannot create dependency: a parent task cannot block its own subtask (would create deadlock)"
        )

    # Create the dependency
    db_dependency = models.TaskDependency(
        blocking_task_id=dependency.blocking_task_id,
        blocked_task_id=task_id
    )
    db.add(db_dependency)
    db.commit()
    db.refresh(db_dependency)

    logger.critical(f"Successfully created dependency: task {dependency.blocking_task_id} blocks task {task_id}")
    return db_dependency


@app.delete("/api/tasks/{task_id}/dependencies/{blocking_id}")
def remove_task_dependency(task_id: int, blocking_id: int, db: Session = Depends(get_db)):
    """Remove a blocking relationship."""
    logger.debug(f"Removing dependency: blocking_task_id={blocking_id}, blocked_task_id={task_id}")

    # Find the dependency
    dependency = db.query(models.TaskDependency)\
        .filter(
            models.TaskDependency.blocking_task_id == blocking_id,
            models.TaskDependency.blocked_task_id == task_id
        )\
        .first()

    if not dependency:
        logger.info(f"Dependency not found: {blocking_id} -> {task_id}")
        raise HTTPException(status_code=404, detail="Dependency not found")

    db.delete(dependency)
    db.commit()

    logger.critical(f"Successfully removed dependency: task {blocking_id} no longer blocks task {task_id}")
    return {"message": "Dependency removed"}


