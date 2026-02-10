from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, desc, asc, text
from sqlalchemy.sql import func as sql_func
from typing import List, Optional, Literal
from collections import deque
from datetime import datetime, timedelta, timezone
import logging
import os
import uuid
from pathlib import Path

from database import get_db, engine, Base
import models
import schemas
from time_utils import utc_now

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

# ============== File Upload Configuration ==============

# File upload constants
UPLOAD_DIR = Path("/app/uploads")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {
    ".pdf", ".txt", ".md", ".doc", ".docx",  # Documents
    ".png", ".jpg", ".jpeg", ".gif", ".webp",  # Images (removed .svg for XSS security)
    ".json", ".xml", ".csv", ".xlsx",  # Data files
    ".zip", ".tar", ".gz"  # Archives
}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain", "text/markdown",
    "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png", "image/jpeg", "image/gif", "image/webp",  # Removed image/svg+xml for XSS security
    "application/json", "application/xml", "text/xml", "text/csv",  # text/xml for browser compatibility
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip", "application/x-tar", "application/gzip"
}

# Ensure upload directory exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files for serving uploads
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


def validate_file_upload(file: UploadFile) -> None:
    """Validate file extension and MIME type."""
    # Check file extension first (primary validation)
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check MIME type (allow application/octet-stream for valid extensions)
    # Many clients send octet-stream for binary files, so we trust the extension
    if file.content_type not in ALLOWED_MIME_TYPES and file.content_type != "application/octet-stream":
        raise HTTPException(
            status_code=400,
            detail=f"MIME type not allowed: {file.content_type}. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )


def validate_external_url(url: str) -> None:
    """
    Validate external link URL to prevent XSS via javascript: or data: protocols.

    Allows only safe protocols: http, https, mailto.
    Raises HTTPException(400) for invalid or dangerous URLs.
    """
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    url = url.strip()

    # Check for safe protocols (case-insensitive)
    allowed_protocols = ['http://', 'https://', 'mailto:']
    url_lower = url.lower()

    # Must start with an allowed protocol
    if not any(url_lower.startswith(proto) for proto in allowed_protocols):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL protocol. Allowed protocols: http://, https://, mailto:"
        )

    # Reject dangerous protocols explicitly (defense in depth)
    dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:', 'about:']
    if any(url_lower.startswith(proto) for proto in dangerous_protocols):
        raise HTTPException(
            status_code=400,
            detail=f"Dangerous URL protocol detected: {url_lower.split(':')[0]}"
        )


async def save_upload_file(task_id: int, file: UploadFile) -> tuple[str, str, int]:
    """
    Save uploaded file using chunked streaming to prevent memory DoS.

    Reads file in 1MB chunks, validating size incrementally. Aborts immediately
    if size limit exceeded. Max memory footprint: 1MB (chunk size).

    Returns:
        tuple: (filename, filepath, file_size)
    """
    # Create task-specific directory
    task_dir = UPLOAD_DIR / str(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    filepath = task_dir / unique_filename

    # Stream file in chunks, validate size incrementally
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks (max memory footprint)
    total_size = 0

    try:
        with open(filepath, "wb") as f:
            while True:
                chunk = await file.read(CHUNK_SIZE)  # Read 1MB at a time
                if not chunk:
                    break

                total_size += len(chunk)

                # Fail fast if size exceeded
                if total_size > MAX_FILE_SIZE:
                    f.close()
                    if filepath.exists():
                        filepath.unlink()
                    raise HTTPException(
                        status_code=413,  # Payload Too Large
                        detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.0f}MB"
                    )

                f.write(chunk)

    except HTTPException:
        raise
    except Exception as e:
        if filepath.exists():
            filepath.unlink()
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Return relative path for storage
    relative_path = f"/uploads/{task_id}/{unique_filename}"
    return unique_filename, relative_path, total_size


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
        backlog_tasks=sum(1 for t in tasks if t.status == models.TaskStatus.backlog),
        todo_tasks=sum(1 for t in tasks if t.status == models.TaskStatus.todo),
        in_progress_tasks=sum(1 for t in tasks if t.status == models.TaskStatus.in_progress),
        blocked_tasks=sum(1 for t in tasks if t.status == models.TaskStatus.blocked),
        review_tasks=sum(1 for t in tasks if t.status == models.TaskStatus.review),
        done_tasks=sum(1 for t in tasks if t.status == models.TaskStatus.done),
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

def create_task_event(
    db: Session,
    task_id: int,
    event_type: models.TaskEventType,
    actor_id: Optional[int] = None,
    field_name: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    metadata: Optional[dict] = None,
    commit: bool = True
) -> models.TaskEvent:
    """
    Create a task event for audit trail and timeline feature.

    Args:
        db: Database session
        task_id: ID of the task
        event_type: Type of event (from TaskEventType enum)
        actor_id: ID of the user who triggered the event (optional)
        field_name: Name of the field that changed (for field_update and status_change)
        old_value: Previous value (optional)
        new_value: New value (optional)
        metadata: Additional context as JSONB (optional)
        commit: Whether to commit the event immediately (default: True, set False for bulk operations)

    Returns:
        Created TaskEvent instance
    """
    logger.debug(f"Creating event: type={event_type}, task_id={task_id}, actor_id={actor_id}, field={field_name}")

    event = models.TaskEvent(
        task_id=task_id,
        event_type=event_type,
        actor_id=actor_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        event_metadata=metadata
    )

    db.add(event)
    db.flush()  # Flush to get ID without committing

    if commit:
        db.commit()
        db.refresh(event)

    logger.debug(f"Event created: id={event.id}, type={event_type}")
    return event


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
    with status != done.

    Returns True if task has any incomplete blocking dependencies, False otherwise.
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

    # Check if any blocking task is not done
    is_blocked = any(bt.status != models.TaskStatus.done for bt in blocking_tasks)
    logger.debug(f"Task {task_id} is_blocked={is_blocked} ({len([bt for bt in blocking_tasks if bt.status != models.TaskStatus.done])} incomplete blockers)")

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


def bulk_calculate_is_blocked(db: Session, task_ids: list[int], batch_done_task_ids: set[int] = None) -> dict[int, bool]:
    """
    Calculate is_blocked for multiple tasks in bulk to avoid N+1 queries.
    Returns a dict mapping task_id -> is_blocked.

    This function:
    1. Fetches all dependencies for the given tasks in one query
    2. Fetches all blocking task statuses in one query
    3. Computes is_blocked in memory

    Args:
        db: Database session
        task_ids: List of task IDs to check
        batch_done_task_ids: Optional set of task IDs to treat as "done" during validation
                             (used for batch update validation where multiple tasks are
                             being marked as done together)
    """
    if not task_ids:
        return {}

    if batch_done_task_ids is None:
        batch_done_task_ids = set()

    logger.debug(f"Bulk calculating is_blocked for {len(task_ids)} tasks (batch override: {len(batch_done_task_ids)} tasks)")

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
    # Override status to "done" for tasks in batch_done_task_ids
    blocking_status_map = {}
    for task in blocking_tasks:
        if task.id in batch_done_task_ids:
            blocking_status_map[task.id] = models.TaskStatus.done
        else:
            blocking_status_map[task.id] = task.status

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
            # Task is blocked if any of its blocking tasks are not done
            result[task_id] = any(
                status != models.TaskStatus.done
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
    due_before: Optional[datetime] = Query(None, description="Filter tasks due before this date"),
    due_after: Optional[datetime] = Query(None, description="Filter tasks due after this date"),
    overdue: Optional[bool] = Query(None, description="Filter overdue tasks (due_date < now, excludes done and backlog)"),
    q: Optional[str] = Query(None, description="Full-text search query"),
    sort_by: Optional[str] = Query(None, description="Sort field(s): created_at, updated_at, priority, status, rank (comma-separated, prefix with - for desc)"),
    limit: Optional[int] = Query(None, le=500, description="Optional limit for pagination (max 500)"),
    offset: int = Query(0, ge=0, description="Offset for pagination (only used with limit)"),
    db: Session = Depends(get_db)
):
    logger.debug(f"list_tasks called with q={q}, sort_by={sort_by}, filters: project={project_id}, status={status}, priority={priority}, tag={tag}, owner={owner_id}, due_before={due_before}, due_after={due_after}, overdue={overdue}")

    # Base query with eager loading
    query = db.query(models.Task).options(
        joinedload(models.Task.author),
        joinedload(models.Task.owner),
        joinedload(models.Task.comments)
    )

    # Apply filters
    if project_id:
        query = query.filter(models.Task.project_id == project_id)
    if status:
        query = query.filter(models.Task.status == status)
    if priority:
        query = query.filter(models.Task.priority == priority)
    if tag:
        query = query.filter(models.Task.tag == tag)
    if owner_id is not None:
        # Map owner_id=0 to NULL (unassigned tasks) to match MCP documentation
        if owner_id == 0:
            query = query.filter(models.Task.owner_id.is_(None))
        else:
            query = query.filter(models.Task.owner_id == owner_id)

    # Time tracking filters
    if due_before:
        query = query.filter(models.Task.due_date < due_before)
    if due_after:
        query = query.filter(models.Task.due_date >= due_after)
    if overdue is True:
        now = utc_now()
        query = query.filter(
            models.Task.due_date < now,
            models.Task.status.notin_([models.TaskStatus.done, models.TaskStatus.backlog])
        )

    # Full-text search if query provided
    if q:
        # Validate query is not empty or whitespace only
        if not q.strip():
            logger.info("Empty or whitespace-only search query provided")
            raise HTTPException(status_code=400, detail="Search query cannot be empty or whitespace only")

        logger.debug(f"Applying full-text search with query: {q}")
        # Use plainto_tsquery for natural language queries (handles special characters automatically)
        search_query = func.plainto_tsquery('english', q)
        query = query.filter(models.Task.search_vector.op('@@')(search_query))
        logger.info(f"Full-text search applied for query: {q}")

    # Apply sorting
    if sort_by:
        logger.debug(f"Applying custom sort: {sort_by}")
        order_clauses = []
        for field in sort_by.split(','):
            field = field.strip()
            if field.startswith('-'):
                # Descending order
                field_name = field[1:]
                if field_name == 'rank' and q:
                    # Relevance ranking only available when searching
                    search_query = func.plainto_tsquery('english', q)
                    order_clauses.append(desc(func.ts_rank(models.Task.search_vector, search_query)))
                elif field_name == 'created_at':
                    order_clauses.append(desc(models.Task.created_at))
                elif field_name == 'updated_at':
                    order_clauses.append(desc(models.Task.updated_at))
                elif field_name == 'priority':
                    order_clauses.append(desc(models.Task.priority))
                elif field_name == 'status':
                    order_clauses.append(desc(models.Task.status))
            else:
                # Ascending order
                if field == 'rank' and q:
                    search_query = func.plainto_tsquery('english', q)
                    order_clauses.append(asc(func.ts_rank(models.Task.search_vector, search_query)))
                elif field == 'created_at':
                    order_clauses.append(asc(models.Task.created_at))
                elif field == 'updated_at':
                    order_clauses.append(asc(models.Task.updated_at))
                elif field == 'priority':
                    order_clauses.append(asc(models.Task.priority))
                elif field == 'status':
                    order_clauses.append(asc(models.Task.status))

        if order_clauses:
            # Add task.id as tiebreaker for deterministic pagination
            order_clauses.append(asc(models.Task.id))
            query = query.order_by(*order_clauses)
        else:
            # Fallback to default ordering
            query = query.order_by(models.Task.id)
    elif q:
        # If searching but no sort specified, sort by relevance (rank) descending
        logger.debug("Sorting by relevance (rank desc) for search query")
        search_query = func.plainto_tsquery('english', q)
        query = query.order_by(desc(func.ts_rank(models.Task.search_vector, search_query)), models.Task.id)
    else:
        # Default deterministic ordering for reliable pagination
        query = query.order_by(models.Task.id)

    # Apply pagination only if limit is explicitly provided (opt-in)
    if limit is not None:
        query = query.offset(offset).limit(limit)

    tasks = query.all()
    logger.debug(f"Retrieved {len(tasks)} tasks")

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
            "due_date": task.due_date,
            "estimated_hours": float(task.estimated_hours) if task.estimated_hours is not None else None,
            "actual_hours": float(task.actual_hours) if task.actual_hours is not None else None,
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

    logger.info(f"list_tasks completed successfully: returned {len(result)} tasks")
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

    # Create task_created event
    create_task_event(
        db=db,
        task_id=db_task.id,
        event_type=models.TaskEventType.task_created,
        actor_id=task.author_id,
        metadata={
            "title": db_task.title,
            "status": db_task.status.value,
            "priority": db_task.priority.value,
            "tag": db_task.tag.value
        }
    )

    logger.info(f"Task created successfully: id={db_task.id}")
    return db_task


@app.get("/api/tasks/actionable", response_model=List[schemas.TaskSummary])
def get_actionable_tasks(
    project_id: Optional[int] = Query(None),
    owner_id: Optional[int] = Query(None),
    priority: Optional[schemas.TaskPriority] = Query(None),
    tag: Optional[schemas.TaskTag] = Query(None),
    limit: Optional[int] = Query(None, le=500, description="Optional limit for pagination (max 500)"),
    offset: int = Query(0, ge=0, description="Offset for pagination (only used with limit)"),
    db: Session = Depends(get_db)
):
    """
    Query unblocked, actionable tasks.
    Returns tasks that are not in backlog, blocked, or done status and have no blocking dependencies
    or all blocking tasks are completed.
    """
    logger.debug(f"Getting actionable tasks with filters: project_id={project_id}, owner_id={owner_id}, priority={priority}, tag={tag}")

    # Start with tasks excluding backlog, blocked, and done
    query = db.query(models.Task)\
        .options(
            joinedload(models.Task.author),
            joinedload(models.Task.owner),
            joinedload(models.Task.comments)
        )\
        .filter(models.Task.status.notin_([
            models.TaskStatus.backlog,
            models.TaskStatus.blocked,
            models.TaskStatus.done
        ]))

    # Apply optional filters
    if project_id:
        query = query.filter(models.Task.project_id == project_id)
    if owner_id is not None:
        # Map owner_id=0 to NULL (unassigned tasks) to match MCP documentation
        if owner_id == 0:
            query = query.filter(models.Task.owner_id.is_(None))
        else:
            query = query.filter(models.Task.owner_id == owner_id)
    if priority:
        query = query.filter(models.Task.priority == priority)
    if tag:
        query = query.filter(models.Task.tag == tag)

    # Add deterministic ordering for reliable pagination
    # Note: We fetch ALL matching tasks first, then apply pagination AFTER
    # filtering blocked tasks to ensure consistent pagination results
    tasks = query.order_by(models.Task.id).all()
    logger.debug(f"Found {len(tasks)} candidate tasks before filtering blocked tasks")

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
            # Check if all blocking tasks are done
            blocking_task_ids = [dep.blocking_task_id for dep in blocking_deps]
            blocking_tasks = db.query(models.Task)\
                .filter(models.Task.id.in_(blocking_task_ids))\
                .all()

            logger.debug(f"Task {task.id} has {len(blocking_tasks)} blocking task(s)")

            # Task is actionable if all blocking tasks are done
            if all(bt.status == models.TaskStatus.done for bt in blocking_tasks):
                logger.debug(f"Task {task.id} is actionable, all blocking tasks completed")
                actionable_tasks.append(task)
            else:
                logger.debug(f"Task {task.id} is blocked by {sum(1 for bt in blocking_tasks if bt.status != models.TaskStatus.done)} incomplete task(s)")

    logger.info(f"Found {len(actionable_tasks)} actionable tasks")

    # Apply pagination AFTER filtering blocked tasks (opt-in - only if limit provided)
    if limit is not None:
        paginated_tasks = actionable_tasks[offset:offset+limit]
        logger.info(f"Returning {len(paginated_tasks)} actionable tasks after pagination (offset={offset}, limit={limit})")
    else:
        paginated_tasks = actionable_tasks
        logger.info(f"Returning all {len(paginated_tasks)} actionable tasks (no pagination)")

    # Convert to summary format with comment_count
    result = []
    for task in paginated_tasks:
        task_dict = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "tag": task.tag,
            "priority": task.priority,
            "status": task.status,
            "due_date": task.due_date,
            "estimated_hours": float(task.estimated_hours) if task.estimated_hours is not None else None,
            "actual_hours": float(task.actual_hours) if task.actual_hours is not None else None,
            "project_id": task.project_id,
            "author_id": task.author_id,
            "author": task.author,
            "owner_id": task.owner_id,
            "owner": task.owner,
            "parent_task_id": task.parent_task_id,
            "comment_count": len(task.comments),
            "is_blocked": False,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        result.append(task_dict)

    logger.critical(f"Successfully retrieved {len(result)} actionable tasks")
    return result


@app.get("/api/tasks/overdue", response_model=List[schemas.TaskSummary])
def get_overdue_tasks(
    project_id: Optional[int] = Query(None),
    limit: int = Query(10, le=500, description="Limit for pagination (max 500, default 10)"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Query overdue tasks (due_date < now, excludes done and backlog).
    Returns actionable tasks that are past their due date.
    Backlog tasks are excluded as they are not yet actionable.
    """
    logger.debug(f"Getting overdue tasks with filters: project_id={project_id}, limit={limit}, offset={offset}")

    # Calculate current time using timezone-aware datetime (consistent with upcoming endpoint)
    now = utc_now()

    # Query overdue tasks
    query = db.query(models.Task)\
        .options(
            joinedload(models.Task.author),
            joinedload(models.Task.owner),
            joinedload(models.Task.comments)
        )\
        .filter(
            models.Task.due_date < now,
            models.Task.status.notin_([models.TaskStatus.done, models.TaskStatus.backlog])
        )

    # Apply project filter if provided
    if project_id:
        query = query.filter(models.Task.project_id == project_id)

    # Get total count before pagination
    total_count = query.count()
    logger.debug(f"Found {total_count} overdue tasks before pagination")

    # Apply pagination
    query = query.order_by(models.Task.due_date).offset(offset).limit(limit)
    tasks = query.all()

    # Bulk calculate is_blocked for all tasks to avoid N+1 queries
    task_ids = [task.id for task in tasks]
    is_blocked_map = bulk_calculate_is_blocked(db, task_ids)

    # Convert to summary format with comment_count
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
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "due_date": task.due_date,
            "estimated_hours": float(task.estimated_hours) if task.estimated_hours is not None else None,
            "actual_hours": float(task.actual_hours) if task.actual_hours is not None else None,
            "is_blocked": is_blocked_map.get(task.id, False)
        }
        result.append(task_dict)

    logger.info(f"Returning {len(result)} overdue tasks out of {total_count} total")
    return result


@app.get("/api/tasks/upcoming", response_model=List[schemas.TaskSummary])
def get_upcoming_tasks(
    days: int = Query(7, ge=1, le=365, description="Number of days ahead to look for upcoming tasks (default 7)"),
    project_id: Optional[int] = Query(None),
    limit: int = Query(10, le=500, description="Limit for pagination (max 500, default 10)"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Query upcoming tasks (due_date between now and now + days, excludes done and backlog).
    Returns actionable tasks that are due within the specified number of days.
    Backlog tasks are excluded as they are not yet actionable.
    """
    logger.debug(f"Getting upcoming tasks with filters: days={days}, project_id={project_id}, limit={limit}, offset={offset}")

    # Calculate date range using timezone-aware datetime (single time source)
    now = utc_now()
    future_date = now + timedelta(days=days)

    # Query upcoming tasks
    query = db.query(models.Task)\
        .options(
            joinedload(models.Task.author),
            joinedload(models.Task.owner),
            joinedload(models.Task.comments)
        )\
        .filter(
            models.Task.due_date >= now,
            models.Task.due_date <= future_date,
            models.Task.status.notin_([models.TaskStatus.done, models.TaskStatus.backlog])
        )

    # Apply project filter if provided
    if project_id:
        query = query.filter(models.Task.project_id == project_id)

    # Get total count before pagination
    total_count = query.count()
    logger.debug(f"Found {total_count} upcoming tasks before pagination")

    # Apply pagination
    query = query.order_by(models.Task.due_date).offset(offset).limit(limit)
    tasks = query.all()

    # Bulk calculate is_blocked for all tasks to avoid N+1 queries
    task_ids = [task.id for task in tasks]
    is_blocked_map = bulk_calculate_is_blocked(db, task_ids)

    # Convert to summary format with comment_count
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
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "due_date": task.due_date,
            "estimated_hours": float(task.estimated_hours) if task.estimated_hours is not None else None,
            "actual_hours": float(task.actual_hours) if task.actual_hours is not None else None,
            "is_blocked": is_blocked_map.get(task.id, False)
        }
        result.append(task_dict)

    logger.info(f"Returning {len(result)} upcoming tasks out of {total_count} total (next {days} days)")
    return result


@app.get("/api/tasks/{task_id}", response_model=schemas.Task)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task)\
        .options(
            joinedload(models.Task.author),
            joinedload(models.Task.owner),
            joinedload(models.Task.comments).joinedload(models.Comment.author),
            joinedload(models.Task.attachments).joinedload(models.TaskAttachment.uploader)
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
            "updated_at": subtask.updated_at,
            "due_date": subtask.due_date,
            "estimated_hours": subtask.estimated_hours,
            "actual_hours": subtask.actual_hours
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
    completed_subtasks = sum(1 for s in subtasks if s.status == models.TaskStatus.done)

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

    # Validate status change to done
    if 'status' in update_data and update_data['status'] == models.TaskStatus.done:
        logger.debug(f"Validating completion of task {task_id}")

        # Check if task has incomplete subtasks
        incomplete_subtasks = db.query(models.Task).filter(
            models.Task.parent_task_id == task_id,
            models.Task.status != models.TaskStatus.done
        ).count()

        if incomplete_subtasks > 0:
            logger.info(f"Task {task_id} cannot be marked as done: has {incomplete_subtasks} incomplete subtask(s)")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot mark task as done with {incomplete_subtasks} incomplete subtask(s)"
            )

        # Check if task is blocked by other tasks
        is_blocked = calculate_is_blocked(db, task_id)
        if is_blocked:
            logger.info(f"Task {task_id} cannot be marked as done: is blocked by incomplete dependencies")
            raise HTTPException(
                status_code=400,
                detail="Cannot mark task as done while it is blocked by incomplete dependencies"
            )

        logger.debug(f"Task {task_id} can be marked as done")

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

    # Track old values for event tracking
    old_values = {key: getattr(task, key) for key in update_data.keys()}

    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)

    # Create events for each changed field
    for field_name, new_value in update_data.items():
        old_value = old_values[field_name]

        # Convert enum values to strings for comparison and storage
        old_str = old_value.value if hasattr(old_value, 'value') else str(old_value) if old_value is not None else None
        new_str = new_value.value if hasattr(new_value, 'value') else str(new_value) if new_value is not None else None

        # Only create event if value actually changed
        if old_str != new_str:
            if field_name == 'status':
                # Status change gets its own event type
                create_task_event(
                    db=db,
                    task_id=task_id,
                    event_type=models.TaskEventType.status_change,
                    actor_id=None,  # Could be extracted from request context if available
                    field_name='status',
                    old_value=old_str,
                    new_value=new_str
                )
            else:
                # Other field changes use field_update event type
                create_task_event(
                    db=db,
                    task_id=task_id,
                    event_type=models.TaskEventType.field_update,
                    actor_id=None,  # Could be extracted from request context if available
                    field_name=field_name,
                    old_value=old_str,
                    new_value=new_str
                )
            logger.debug(f"Event created for field '{field_name}': {old_str} -> {new_str}")

    # Reload task with relationships
    task = db.query(models.Task)\
        .options(
            joinedload(models.Task.author),
            joinedload(models.Task.owner),
            joinedload(models.Task.comments).joinedload(models.Comment.author)
        )\
        .filter(models.Task.id == task_id)\
        .first()

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

    # Track old owner for event
    old_owner_id = task.owner_id

    # Assign ownership
    task.owner_id = ownership.author_id
    db.commit()

    # Create ownership_change event
    create_task_event(
        db=db,
        task_id=task_id,
        event_type=models.TaskEventType.ownership_change,
        actor_id=ownership.author_id,
        old_value=str(old_owner_id) if old_owner_id is not None else None,
        new_value=str(ownership.author_id),
        metadata={"force": ownership.force}
    )

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

    # Create comment_added event
    create_task_event(
        db=db,
        task_id=task_id,
        event_type=models.TaskEventType.comment_added,
        actor_id=comment.author_id,
        metadata={"comment_id": db_comment.id, "comment_preview": comment.content[:100]}
    )

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
    backlog_tasks = db.query(models.Task).filter(models.Task.status == models.TaskStatus.backlog).count()
    todo_tasks = db.query(models.Task).filter(models.Task.status == models.TaskStatus.todo).count()
    in_progress_tasks = db.query(models.Task).filter(models.Task.status == models.TaskStatus.in_progress).count()
    blocked_tasks = db.query(models.Task).filter(models.Task.status == models.TaskStatus.blocked).count()
    review_tasks = db.query(models.Task).filter(models.Task.status == models.TaskStatus.review).count()
    done_tasks = db.query(models.Task).filter(models.Task.status == models.TaskStatus.done).count()

    p0_incomplete = db.query(models.Task).filter(
        models.Task.status != models.TaskStatus.done,
        models.Task.priority == models.TaskPriority.P0
    ).count()

    return {
        "total_projects": total_projects,
        "total_tasks": total_tasks,
        "backlog_tasks": backlog_tasks,
        "todo_tasks": todo_tasks,
        "in_progress_tasks": in_progress_tasks,
        "blocked_tasks": blocked_tasks,
        "review_tasks": review_tasks,
        "done_tasks": done_tasks,
        "p0_incomplete": p0_incomplete,
        "completion_rate": round((done_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
    }


# ============== Full-Text Search ==============

@app.get("/api/search", response_model=schemas.SearchResults)
def global_search(
    q: str = Query(..., description="Search query (required)"),
    project_id: Optional[int] = Query(None, description="Filter to specific project"),
    search_in: Optional[str] = Query(None, description="Comma-separated entity types (tasks,projects,comments)"),
    status: Optional[schemas.TaskStatus] = Query(None, description="Filter tasks by status"),
    priority: Optional[schemas.TaskPriority] = Query(None, description="Filter tasks by priority"),
    tag: Optional[schemas.TaskTag] = Query(None, description="Filter tasks by tag"),
    owner_id: Optional[int] = Query(None, description="Filter tasks by owner (use 0 for unassigned)"),
    limit: int = Query(10, le=100, description="Maximum results per category (max 100)"),
    db: Session = Depends(get_db)
):
    """
    Perform full-text search across tasks, projects, and comments.
    Returns relevance-ranked results from all entities.
    Supports filtering by project, status, priority, tag, and owner.
    """
    logger.debug(f"global_search called with query: {q}, project_id: {project_id}, search_in: {search_in}, "
                 f"status: {status}, priority: {priority}, tag: {tag}, owner_id: {owner_id}, limit: {limit}")

    if not q or not q.strip():
        logger.info("Empty search query provided")
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    # Parse search_in parameter to determine which entities to search
    entities_to_search = {"tasks", "projects", "comments"}  # Default: search all
    if search_in:
        entities_to_search = {e.strip() for e in search_in.split(',') if e.strip()}
        valid_entities = {"tasks", "projects", "comments"}
        if not entities_to_search.issubset(valid_entities):
            raise HTTPException(status_code=400, detail=f"Invalid search_in values. Must be comma-separated list from: {valid_entities}")

    # Use plainto_tsquery for natural language queries
    search_query = func.plainto_tsquery('english', q)

    # Search tasks (if requested)
    tasks = []
    if "tasks" in entities_to_search:
        logger.debug("Searching tasks...")
        task_query = db.query(
            models.Task.id,
            models.Task.title,
            models.Task.description,
            models.Task.tag,
            models.Task.priority,
            models.Task.status,
            models.Task.project_id,
            models.Task.parent_task_id,
            models.Task.created_at,
            models.Task.updated_at,
            func.ts_rank(models.Task.search_vector, search_query).label('rank')
        ).filter(
            models.Task.search_vector.op('@@')(search_query)
        )

        # Apply task filters
        if project_id is not None:
            task_query = task_query.filter(models.Task.project_id == project_id)
        if status is not None:
            task_query = task_query.filter(models.Task.status == status)
        if priority is not None:
            task_query = task_query.filter(models.Task.priority == priority)
        if tag is not None:
            task_query = task_query.filter(models.Task.tag == tag)
        if owner_id is not None:
            if owner_id == 0:
                task_query = task_query.filter(models.Task.owner_id.is_(None))
            else:
                task_query = task_query.filter(models.Task.owner_id == owner_id)

        task_query = task_query.order_by(
            desc(func.ts_rank(models.Task.search_vector, search_query))
        ).limit(limit)

        task_results = task_query.all()

        tasks = [
            schemas.SearchResultTask(
                id=row.id,
                title=row.title,
                description=row.description,
                tag=row.tag,
                priority=row.priority,
                status=row.status,
                project_id=row.project_id,
                parent_task_id=row.parent_task_id,
                rank=row.rank,
                created_at=row.created_at,
                updated_at=row.updated_at
            )
            for row in task_results
        ]
        logger.debug(f"Found {len(tasks)} matching tasks")

    # Search projects (if requested)
    projects = []
    if "projects" in entities_to_search:
        logger.debug("Searching projects...")
        project_query = db.query(
            models.Project.id,
            models.Project.name,
            models.Project.description,
            models.Project.created_at,
            models.Project.updated_at,
            func.ts_rank(models.Project.search_vector, search_query).label('rank')
        ).filter(
            models.Project.search_vector.op('@@')(search_query)
        )

        # Apply project filter if specified
        if project_id is not None:
            project_query = project_query.filter(models.Project.id == project_id)

        project_query = project_query.order_by(
            desc(func.ts_rank(models.Project.search_vector, search_query))
        ).limit(limit)

        project_results = project_query.all()

        projects = [
            schemas.SearchResultProject(
                id=row.id,
                name=row.name,
                description=row.description,
                rank=row.rank,
                created_at=row.created_at,
                updated_at=row.updated_at
            )
            for row in project_results
        ]
        logger.debug(f"Found {len(projects)} matching projects")

    # Search comments (if requested, with task title for context)
    comments = []
    if "comments" in entities_to_search:
        logger.debug("Searching comments...")
        comment_query = db.query(
            models.Comment.id,
            models.Comment.content,
            models.Comment.task_id,
            models.Task.title.label('task_title'),
            models.Comment.created_at,
            models.Comment.updated_at,
            func.ts_rank(models.Comment.search_vector, search_query).label('rank')
        ).join(
            models.Task, models.Comment.task_id == models.Task.id
        ).filter(
            models.Comment.search_vector.op('@@')(search_query)
        )

        # Apply project filter via task join if specified
        if project_id is not None:
            comment_query = comment_query.filter(models.Task.project_id == project_id)

        comment_query = comment_query.order_by(
            desc(func.ts_rank(models.Comment.search_vector, search_query))
        ).limit(limit)

        comment_results = comment_query.all()

        comments = [
            schemas.SearchResultComment(
                id=row.id,
                content=row.content,
                task_id=row.task_id,
                task_title=row.task_title,
                rank=row.rank,
                created_at=row.created_at,
                updated_at=row.updated_at
            )
            for row in comment_results
        ]
        logger.debug(f"Found {len(comments)} matching comments")

    total_results = len(tasks) + len(projects) + len(comments)
    logger.info(f"global_search completed: query='{q}', total_results={total_results}")

    return schemas.SearchResults(
        tasks=tasks,
        projects=projects,
        comments=comments,
        total_results=total_results
    )


# ============== Task Events ==============

@app.get("/api/tasks/{task_id}/events", response_model=schemas.TaskEventsList)
def get_task_events(
    task_id: int,
    event_type: Optional[schemas.TaskEventType] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get event history for a specific task.

    Query parameters:
    - event_type: Filter by event type (optional)
    - limit: Maximum number of events to return (default: 100, max: 500)
    - offset: Number of events to skip for pagination (default: 0)
    """
    logger.debug(f"Getting events for task {task_id}: event_type={event_type}, limit={limit}, offset={offset}")

    # Verify task exists
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        logger.info(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")

    # Build query
    query = db.query(models.TaskEvent)\
        .options(joinedload(models.TaskEvent.actor))\
        .filter(models.TaskEvent.task_id == task_id)

    # Apply event_type filter if provided
    if event_type:
        query = query.filter(models.TaskEvent.event_type == event_type)

    # Get total count for pagination
    total = query.count()

    # Apply pagination and ordering
    events = query.order_by(models.TaskEvent.created_at.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()

    logger.info(f"Found {len(events)} events for task {task_id} (total: {total})")

    return schemas.TaskEventsList(events=events, total_count=total)


@app.get("/api/projects/{project_id}/events", response_model=schemas.TaskEventsList)
def get_project_events(
    project_id: int,
    event_type: Optional[schemas.TaskEventType] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get event history for all tasks in a project.

    Query parameters:
    - event_type: Filter by event type (optional)
    - limit: Maximum number of events to return (default: 100, max: 500)
    - offset: Number of events to skip for pagination (default: 0)
    """
    logger.debug(f"Getting events for project {project_id}: event_type={event_type}, limit={limit}, offset={offset}")

    # Verify project exists
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        logger.info(f"Project {project_id} not found")
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all task IDs in the project
    task_ids = db.query(models.Task.id).filter(models.Task.project_id == project_id).all()
    task_id_list = [task_id[0] for task_id in task_ids]

    if not task_id_list:
        logger.info(f"No tasks found in project {project_id}")
        return schemas.TaskEventsList(events=[], total=0)

    # Build query
    query = db.query(models.TaskEvent)\
        .options(joinedload(models.TaskEvent.actor))\
        .filter(models.TaskEvent.task_id.in_(task_id_list))

    # Apply event_type filter if provided
    if event_type:
        query = query.filter(models.TaskEvent.event_type == event_type)

    # Get total count for pagination
    total = query.count()

    # Apply pagination and ordering
    events = query.order_by(models.TaskEvent.created_at.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()

    logger.info(f"Found {len(events)} events for project {project_id} (total: {total})")

    return schemas.TaskEventsList(events=events, total_count=total)


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

    # Calculate is_blocked: task is blocked if it has any blocking dependencies with status != done
    is_blocked = any(bt.status != models.TaskStatus.done for bt in blocking_tasks)
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

    # Create dependency_added event on the blocked task
    create_task_event(
        db=db,
        task_id=task_id,
        event_type=models.TaskEventType.dependency_added,
        actor_id=None,
        metadata={
            "blocking_task_id": dependency.blocking_task_id,
            "blocking_task_title": blocking_task.title
        }
    )

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

    # Get blocking task title for event metadata
    blocking_task = db.query(models.Task).filter(models.Task.id == blocking_id).first()

    db.delete(dependency)
    db.commit()

    # Create dependency_removed event on the blocked task
    create_task_event(
        db=db,
        task_id=task_id,
        event_type=models.TaskEventType.dependency_removed,
        actor_id=None,
        metadata={
            "blocking_task_id": blocking_id,
            "blocking_task_title": blocking_task.title if blocking_task else None
        }
    )

    logger.critical(f"Successfully removed dependency: task {blocking_id} no longer blocks task {task_id}")
    return {"message": "Dependency removed"}


# ============== Rich Context & Attachments ==============

@app.post("/api/tasks/{task_id}/attachments", response_model=schemas.Attachment)
async def upload_attachment(
    task_id: int,
    request: Request,
    file: UploadFile = File(...),
    uploaded_by: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Upload a file attachment to a task."""
    logger.debug(f"Uploading attachment to task {task_id}: {file.filename}")

    # Make Content-Length REQUIRED (fail fast before reading data)
    content_length = request.headers.get("content-length")
    if not content_length:
        raise HTTPException(
            status_code=411,  # Length Required
            detail="Content-Length header is required for file uploads"
        )

    try:
        content_length_int = int(content_length)
        if content_length_int > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,  # Payload Too Large
                detail=f"Request too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Content-Length header: {content_length}"
        )

    # Verify task exists
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Validate uploaded_by author exists (if provided)
    if uploaded_by is not None:
        author = db.query(models.Author).filter(models.Author.id == uploaded_by).first()
        if not author:
            raise HTTPException(status_code=400, detail=f"Author with id {uploaded_by} not found")

    # Validate file
    validate_file_upload(file)

    # Save file
    filename, filepath, file_size = await save_upload_file(task_id, file)

    # Create attachment record with DB rollback on failure
    try:
        attachment = models.TaskAttachment(
            task_id=task_id,
            filename=filename,
            original_filename=file.filename,
            filepath=filepath,
            mime_type=file.content_type,
            file_size=file_size,
            uploaded_by=uploaded_by
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
    except Exception as e:
        # Rollback DB transaction
        db.rollback()
        # Clean up saved file
        file_path = UPLOAD_DIR / str(task_id) / filename
        if file_path.exists():
            file_path.unlink()
            logger.error(f"Cleaned up orphaned file after DB error: {file_path}")
        logger.error(f"Failed to create attachment record: {e}")
        raise HTTPException(status_code=500, detail="Failed to save attachment")

    # Create event
    create_task_event(
        db=db,
        task_id=task_id,
        event_type=models.TaskEventType.attachment_added,
        actor_id=uploaded_by,
        metadata={
            "attachment_id": attachment.id,
            "filename": file.filename,
            "file_size": file_size
        }
    )

    logger.critical(f"Successfully uploaded attachment {attachment.id} to task {task_id}")

    # Load uploader relationship
    db.refresh(attachment)
    return attachment


@app.get("/api/tasks/{task_id}/attachments", response_model=List[schemas.Attachment])
def list_attachments(task_id: int, db: Session = Depends(get_db)):
    """List all attachments for a task."""
    # Verify task exists
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    attachments = db.query(models.TaskAttachment)\
        .filter(models.TaskAttachment.task_id == task_id)\
        .options(joinedload(models.TaskAttachment.uploader))\
        .all()

    return attachments


@app.delete("/api/tasks/{task_id}/attachments/{attachment_id}")
def delete_attachment(
    task_id: int,
    attachment_id: int,
    actor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Delete a file attachment."""
    logger.debug(f"Deleting attachment {attachment_id} from task {task_id}")

    # Find attachment
    attachment = db.query(models.TaskAttachment)\
        .filter(
            models.TaskAttachment.id == attachment_id,
            models.TaskAttachment.task_id == task_id
        )\
        .first()

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Delete file from disk
    try:
        file_path = Path(attachment.filepath.replace("/uploads/", str(UPLOAD_DIR) + "/"))
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Deleted file from disk: {file_path}")
    except Exception as e:
        logger.error(f"Failed to delete file from disk: {e}")
        # Continue anyway - we still want to delete the DB record

    # Save metadata for event
    original_filename = attachment.original_filename

    # Delete database record
    db.delete(attachment)
    db.commit()

    # Create event
    create_task_event(
        db=db,
        task_id=task_id,
        event_type=models.TaskEventType.attachment_deleted,
        actor_id=actor_id,
        metadata={
            "attachment_id": attachment_id,
            "filename": original_filename
        }
    )

    logger.critical(f"Successfully deleted attachment {attachment_id} from task {task_id}")
    return {"message": "Attachment deleted"}


@app.post("/api/tasks/{task_id}/links")
def add_external_link(
    task_id: int,
    link: schemas.ExternalLinkCreate,
    actor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Add an external link to a task."""
    logger.debug(f"Adding external link to task {task_id}: {link.url}")

    # Verify task exists
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Validate URL to prevent XSS
    validate_external_url(link.url)

    # Initialize external_links if None
    if task.external_links is None:
        task.external_links = []

    # Create link object
    link_obj = {
        "url": link.url,
        "label": link.label,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    # Add to JSONB array
    task.external_links = task.external_links + [link_obj]
    db.commit()

    # Create event
    create_task_event(
        db=db,
        task_id=task_id,
        event_type=models.TaskEventType.link_added,
        actor_id=actor_id,
        metadata={"link": link_obj}
    )

    logger.critical(f"Successfully added external link to task {task_id}")
    return {"message": "Link added", "link": link_obj}


@app.delete("/api/tasks/{task_id}/links")
def remove_external_link(
    task_id: int,
    url: str = Query(...),
    actor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Remove an external link from a task."""
    logger.debug(f"Removing external link from task {task_id}: {url}")

    # Verify task exists
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Find and remove link
    if task.external_links:
        original_links = task.external_links
        task.external_links = [link for link in task.external_links if link.get("url") != url]

        if len(task.external_links) == len(original_links):
            raise HTTPException(status_code=404, detail="Link not found")

        # Find removed link for event
        removed_link = next((link for link in original_links if link.get("url") == url), None)

        db.commit()

        # Create event
        create_task_event(
            db=db,
            task_id=task_id,
            event_type=models.TaskEventType.link_removed,
            actor_id=actor_id,
            metadata={"link": removed_link}
        )

        logger.critical(f"Successfully removed external link from task {task_id}")
        return {"message": "Link removed"}
    else:
        raise HTTPException(status_code=404, detail="Link not found")


@app.put("/api/tasks/{task_id}/metadata")
def update_metadata(
    task_id: int,
    metadata_update: schemas.MetadataUpdate,
    actor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Add or update a custom metadata key-value pair."""
    logger.debug(f"Updating metadata for task {task_id}: {metadata_update.key}={metadata_update.value}")

    # Verify task exists
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Validate metadata key (prevent forward slashes for URL compatibility)
    if '/' in metadata_update.key:
        raise HTTPException(
            status_code=400,
            detail="Metadata keys cannot contain forward slashes (/). Use underscores or hyphens instead."
        )

    # Initialize custom_metadata if None
    if task.custom_metadata is None:
        task.custom_metadata = {}

    # Store old value for event
    old_value = task.custom_metadata.get(metadata_update.key)

    # Update metadata
    task.custom_metadata = {**task.custom_metadata, metadata_update.key: metadata_update.value}
    db.commit()

    # Create event
    create_task_event(
        db=db,
        task_id=task_id,
        event_type=models.TaskEventType.metadata_updated,
        actor_id=actor_id,
        field_name=metadata_update.key,
        old_value=str(old_value) if old_value is not None else None,
        new_value=metadata_update.value,
        metadata={"key": metadata_update.key, "value": metadata_update.value}
    )

    logger.critical(f"Successfully updated metadata for task {task_id}: {metadata_update.key}")
    return {"message": "Metadata updated", "key": metadata_update.key, "value": metadata_update.value}


@app.delete("/api/tasks/{task_id}/metadata/{key}")
def delete_metadata(
    task_id: int,
    key: str,
    actor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Remove a custom metadata key."""
    logger.debug(f"Deleting metadata key from task {task_id}: {key}")

    # Verify task exists
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if key exists
    if not task.custom_metadata or key not in task.custom_metadata:
        raise HTTPException(status_code=404, detail="Metadata key not found")

    # Store old value for event
    old_value = task.custom_metadata.get(key)

    # Remove key
    new_metadata = {k: v for k, v in task.custom_metadata.items() if k != key}
    task.custom_metadata = new_metadata
    db.commit()

    # Create event
    create_task_event(
        db=db,
        task_id=task_id,
        event_type=models.TaskEventType.metadata_updated,
        actor_id=actor_id,
        field_name=key,
        old_value=str(old_value),
        new_value=None,
        metadata={"key": key, "deleted": True}
    )

    logger.critical(f"Successfully deleted metadata key from task {task_id}: {key}")
    return {"message": "Metadata key deleted"}


# ============== Bulk Operations ==============

@app.post("/api/tasks/bulk-update", response_model=schemas.BulkOperationResult)
def bulk_update_tasks(bulk_update: schemas.BulkTaskUpdate, db: Session = Depends(get_db)):
    """
    Update multiple tasks in a single transaction with all-or-nothing semantics.

    Validates all tasks before applying any updates. If any validation fails,
    returns errors without making any database changes.
    """
    logger.info(f"Bulk updating {len(bulk_update.task_ids)} tasks")
    logger.debug(f"Task IDs: {bulk_update.task_ids}, Updates: {bulk_update.updates.model_dump(exclude_unset=True)}")

    if not bulk_update.task_ids:
        logger.info("No task IDs provided for bulk update")
        return schemas.BulkOperationResult(success=True, processed_count=0, task_ids=[])

    # De-duplicate task IDs (preserves order)
    bulk_update.task_ids = list(dict.fromkeys(bulk_update.task_ids))
    logger.debug(f"De-duplicated to {len(bulk_update.task_ids)} unique task IDs")

    # Limit batch size
    if len(bulk_update.task_ids) > 500:
        logger.info(f"Batch size {len(bulk_update.task_ids)} exceeds limit of 500")
        raise HTTPException(status_code=400, detail="Maximum 500 tasks per bulk operation")

    errors = []
    update_data = bulk_update.updates.model_dump(exclude_unset=True)

    if not update_data:
        logger.info("No updates provided in bulk update request")
        return schemas.BulkOperationResult(success=True, processed_count=0, task_ids=[])

    # Phase 1: Pre-validate ALL tasks
    logger.debug("Phase 1: Pre-validating all tasks")

    # Fetch all tasks in a single query
    tasks_dict = {}
    tasks = db.query(models.Task).filter(models.Task.id.in_(bulk_update.task_ids)).all()
    for task in tasks:
        tasks_dict[task.id] = task

    # Check for non-existent tasks
    for task_id in bulk_update.task_ids:
        if task_id not in tasks_dict:
            logger.debug(f"Task {task_id} not found")
            errors.append(schemas.BulkOperationError(
                task_id=task_id,
                error="Task not found",
                error_code="NOT_FOUND"
            ))

    # If we have missing tasks, return early
    if errors:
        logger.info(f"Pre-validation failed: {len(errors)} task(s) not found")
        return schemas.BulkOperationResult(
            success=False,
            processed_count=0,
            task_ids=[],
            errors=errors
        )

    # Validate status change to done
    if 'status' in update_data and update_data['status'] == models.TaskStatus.done:
        logger.debug("Validating status change to done for all tasks")

        # Check for incomplete subtasks (bulk query)
        # Exclude subtasks that are also being marked as done in this batch
        task_ids_with_subtasks = db.query(models.Task.parent_task_id)\
            .filter(
                models.Task.parent_task_id.in_(bulk_update.task_ids),
                models.Task.status != models.TaskStatus.done,
                ~models.Task.id.in_(bulk_update.task_ids)  # Exclude tasks in the batch
            )\
            .distinct()\
            .all()

        task_ids_with_incomplete_subtasks = {row[0] for row in task_ids_with_subtasks}

        for task_id in task_ids_with_incomplete_subtasks:
            logger.debug(f"Task {task_id} has incomplete subtasks")
            errors.append(schemas.BulkOperationError(
                task_id=task_id,
                error="Cannot mark task as done with incomplete subtasks",
                error_code="INCOMPLETE_SUBTASKS"
            ))

        # Check for blocked tasks (bulk query)
        # Pass batch task IDs to treat them as "done" during validation
        is_blocked_map = bulk_calculate_is_blocked(db, bulk_update.task_ids, batch_done_task_ids=set(bulk_update.task_ids))

        for task_id, is_blocked in is_blocked_map.items():
            if is_blocked:
                logger.debug(f"Task {task_id} is blocked by incomplete dependencies")
                errors.append(schemas.BulkOperationError(
                    task_id=task_id,
                    error="Cannot mark task as done while blocked by incomplete dependencies",
                    error_code="BLOCKED"
                ))

    # Validate parent_task_id change
    if 'parent_task_id' in update_data and update_data['parent_task_id'] is not None:
        parent_task_id = update_data['parent_task_id']
        logger.debug(f"Validating parent task change to {parent_task_id} for all tasks")

        # Verify parent task exists
        parent_task = db.query(models.Task).filter(models.Task.id == parent_task_id).first()
        if not parent_task:
            logger.info(f"Parent task {parent_task_id} not found")
            # All tasks fail if parent doesn't exist
            for task_id in bulk_update.task_ids:
                errors.append(schemas.BulkOperationError(
                    task_id=task_id,
                    error="Parent task not found",
                    error_code="NOT_FOUND"
                ))
        else:
            # Check same project and circular subtasks for each task
            for task_id in bulk_update.task_ids:
                task = tasks_dict[task_id]

                # Ensure parent task is in the same project
                if parent_task.project_id != task.project_id:
                    logger.debug(f"Task {task_id}: parent task in different project")
                    errors.append(schemas.BulkOperationError(
                        task_id=task_id,
                        error="Parent task must be in the same project",
                        error_code="DIFFERENT_PROJECT"
                    ))

                # Check for circular subtask relationship against DB
                # This catches cycles involving existing ancestor chains outside the batch
                # (e.g., if parent has ancestors that include this task)
                if has_circular_subtask(db, task_id, parent_task_id):
                    logger.debug(f"Task {task_id}: circular subtask relationship with existing ancestors")
                    errors.append(schemas.BulkOperationError(
                        task_id=task_id,
                        error="Cannot create circular subtask relationship",
                        error_code="CIRCULAR_SUBTASK"
                    ))

            # ALSO check for cycles introduced within the batch itself
            # (e.g., A parent=B, B parent=A in same batch, where neither has existing ancestors)
            # This requires in-memory simulation since DB doesn't have the batch updates yet
            logger.debug("Checking for cycles introduced within batch")
            parent_map = {}

            # Load current parent relationships for tasks in batch
            existing_parents = db.query(models.Task.id, models.Task.parent_task_id)\
                .filter(models.Task.id.in_(bulk_update.task_ids))\
                .all()

            for tid, pid in existing_parents:
                if pid is not None:
                    parent_map[tid] = pid

            # Apply batch updates to parent map (all tasks get same parent)
            for task_id in bulk_update.task_ids:
                parent_map[task_id] = parent_task_id

            # Check if any task in batch appears in another's ancestor chain after batch update
            for task_id in bulk_update.task_ids:
                visited = set()
                current = task_id

                while current is not None and current in parent_map:
                    if current in visited:
                        # Found a cycle within batch
                        logger.debug(f"Task {task_id}: circular subtask within batch (cycle involves task {current})")
                        errors.append(schemas.BulkOperationError(
                            task_id=task_id,
                            error="Cannot create circular subtask relationship (detected within batch)",
                            error_code="CIRCULAR_SUBTASK"
                        ))
                        break

                    visited.add(current)
                    current = parent_map.get(current)

    # If validation failed, return errors
    if errors:
        logger.info(f"Pre-validation failed: {len(errors)} error(s) found")
        return schemas.BulkOperationResult(
            success=False,
            processed_count=0,
            task_ids=[],
            errors=errors
        )

    # Phase 2: Apply updates in transaction
    logger.debug("Phase 2: Applying updates in transaction")

    try:
        # Track old values for event tracking
        old_values_map = {}
        for task_id in bulk_update.task_ids:
            task = tasks_dict[task_id]
            old_values_map[task_id] = {key: getattr(task, key) for key in update_data.keys()}

        # Update all tasks
        for task_id in bulk_update.task_ids:
            task = tasks_dict[task_id]
            for key, value in update_data.items():
                setattr(task, key, value)

        # Phase 3: Create events for all changes (within same transaction)
        logger.debug("Phase 3: Creating events for all changes")
        for task_id in bulk_update.task_ids:
            old_values = old_values_map[task_id]

            for field_name, new_value in update_data.items():
                old_value = old_values[field_name]

                # Convert enum values to strings
                old_str = old_value.value if hasattr(old_value, 'value') else str(old_value) if old_value is not None else None
                new_str = new_value.value if hasattr(new_value, 'value') else str(new_value) if new_value is not None else None

                # Only create event if value actually changed
                if old_str != new_str:
                    if field_name == 'status':
                        create_task_event(
                            db=db,
                            task_id=task_id,
                            event_type=models.TaskEventType.status_change,
                            actor_id=bulk_update.actor_id,
                            field_name='status',
                            old_value=old_str,
                            new_value=new_str,
                            commit=False  # Commit once at end
                        )
                    else:
                        create_task_event(
                            db=db,
                            task_id=task_id,
                            event_type=models.TaskEventType.field_update,
                            actor_id=bulk_update.actor_id,
                            field_name=field_name,
                            old_value=old_str,
                            new_value=new_str,
                            commit=False  # Commit once at end
                        )

        # Commit all changes (tasks + events) in single transaction
        db.commit()

        logger.critical(f"Successfully bulk updated {len(bulk_update.task_ids)} tasks")
        return schemas.BulkOperationResult(
            success=True,
            processed_count=len(bulk_update.task_ids),
            task_ids=bulk_update.task_ids,
            errors=[]
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Transaction failed during bulk update: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bulk update failed: {str(e)}")


@app.post("/api/tasks/bulk-take-ownership", response_model=schemas.BulkOperationResult)
def bulk_take_ownership(bulk_ownership: schemas.BulkTakeOwnership, db: Session = Depends(get_db)):
    """
    Take ownership of multiple tasks in a single transaction.

    Validates all tasks before assigning ownership. If force=False and any task
    is already owned, returns error without making any changes.
    """
    logger.info(f"Bulk taking ownership of {len(bulk_ownership.task_ids)} tasks for author {bulk_ownership.author_id}")
    logger.debug(f"Task IDs: {bulk_ownership.task_ids}, Force: {bulk_ownership.force}")

    if not bulk_ownership.task_ids:
        logger.info("No task IDs provided for bulk take ownership")
        return schemas.BulkOperationResult(success=True, processed_count=0, task_ids=[])

    # De-duplicate task IDs (preserves order)
    bulk_ownership.task_ids = list(dict.fromkeys(bulk_ownership.task_ids))
    logger.debug(f"De-duplicated to {len(bulk_ownership.task_ids)} unique task IDs")

    # Limit batch size
    if len(bulk_ownership.task_ids) > 500:
        logger.info(f"Batch size {len(bulk_ownership.task_ids)} exceeds limit of 500")
        raise HTTPException(status_code=400, detail="Maximum 500 tasks per bulk operation")

    errors = []

    # Phase 1: Pre-validate ALL tasks and author
    logger.debug("Phase 1: Pre-validating all tasks and author")

    # Verify author exists
    author = db.query(models.Author).filter(models.Author.id == bulk_ownership.author_id).first()
    if not author:
        logger.info(f"Author {bulk_ownership.author_id} not found")
        raise HTTPException(status_code=404, detail="Author not found")

    # Fetch all tasks in a single query
    tasks_dict = {}
    tasks = db.query(models.Task).filter(models.Task.id.in_(bulk_ownership.task_ids)).all()
    for task in tasks:
        tasks_dict[task.id] = task

    # Check for non-existent tasks
    for task_id in bulk_ownership.task_ids:
        if task_id not in tasks_dict:
            logger.debug(f"Task {task_id} not found")
            errors.append(schemas.BulkOperationError(
                task_id=task_id,
                error="Task not found",
                error_code="NOT_FOUND"
            ))

    # If we have missing tasks, return early
    if errors:
        logger.info(f"Pre-validation failed: {len(errors)} task(s) not found")
        return schemas.BulkOperationResult(
            success=False,
            processed_count=0,
            task_ids=[],
            errors=errors
        )

    # Check ownership conflicts if force=False
    if not bulk_ownership.force:
        logger.debug("Checking for ownership conflicts")
        for task_id in bulk_ownership.task_ids:
            task = tasks_dict[task_id]
            if task.owner_id is not None:
                logger.debug(f"Task {task_id} already owned by author {task.owner_id}")
                errors.append(schemas.BulkOperationError(
                    task_id=task_id,
                    error=f"Task already owned by author ID {task.owner_id}. Use force=true to reassign.",
                    error_code="ALREADY_OWNED"
                ))

    # If ownership conflicts found, return errors
    if errors:
        logger.info(f"Pre-validation failed: {len(errors)} ownership conflict(s) found")
        return schemas.BulkOperationResult(
            success=False,
            processed_count=0,
            task_ids=[],
            errors=errors
        )

    # Phase 2: Apply ownership changes in transaction
    logger.debug("Phase 2: Applying ownership changes in transaction")

    try:
        # Track old owners for event tracking
        old_owners_map = {}
        for task_id in bulk_ownership.task_ids:
            task = tasks_dict[task_id]
            old_owners_map[task_id] = task.owner_id

        # Update all tasks
        for task_id in bulk_ownership.task_ids:
            task = tasks_dict[task_id]
            task.owner_id = bulk_ownership.author_id

        # Phase 3: Create ownership_change events for all tasks (within same transaction)
        logger.debug("Phase 3: Creating ownership_change events")
        for task_id in bulk_ownership.task_ids:
            old_owner_id = old_owners_map[task_id]

            create_task_event(
                db=db,
                task_id=task_id,
                event_type=models.TaskEventType.ownership_change,
                actor_id=bulk_ownership.author_id,
                old_value=str(old_owner_id) if old_owner_id is not None else None,
                new_value=str(bulk_ownership.author_id),
                metadata={"force": bulk_ownership.force},
                commit=False  # Commit once at end
            )

        # Commit all changes (ownership + events) in single transaction
        db.commit()

        logger.critical(f"Successfully assigned ownership of {len(bulk_ownership.task_ids)} tasks to author {bulk_ownership.author_id}")
        return schemas.BulkOperationResult(
            success=True,
            processed_count=len(bulk_ownership.task_ids),
            task_ids=bulk_ownership.task_ids,
            errors=[]
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Transaction failed during bulk take ownership: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bulk take ownership failed: {str(e)}")


@app.post("/api/tasks/bulk-delete", response_model=schemas.BulkDeleteResult)
def bulk_delete_tasks(
    bulk_delete: schemas.BulkTaskDelete,
    db: Session = Depends(get_db)
):
    """
    Delete multiple tasks in a single transaction.

    CASCADE DELETE automatically handles:
    - Subtasks (child tasks with parent_task_id)
    - Task dependencies (blocking relationships)
    - Comments
    - Events

    Returns information about cascade-deleted subtasks and tasks that became unblocked.
    """
    task_ids = bulk_delete.task_ids
    logger.info(f"Bulk deleting {len(task_ids)} tasks")
    logger.debug(f"Task IDs: {task_ids}")

    if not task_ids:
        logger.info("No task IDs provided for bulk delete")
        return schemas.BulkDeleteResult(
            success=True,
            deleted_count=0,
            deleted_task_ids=[],
            cascade_deleted_count=0,
            affected_tasks=[]
        )

    # De-duplicate task IDs (preserves order)
    task_ids = list(dict.fromkeys(task_ids))
    logger.debug(f"De-duplicated to {len(task_ids)} unique task IDs")

    # Limit batch size
    if len(task_ids) > 500:
        logger.info(f"Batch size {len(task_ids)} exceeds limit of 500")
        raise HTTPException(status_code=400, detail="Maximum 500 tasks per bulk operation")

    # Phase 1: Pre-validate and gather metadata
    logger.debug("Phase 1: Pre-validating and gathering metadata")

    # Fetch all tasks
    tasks = db.query(models.Task).filter(models.Task.id.in_(task_ids)).all()
    existing_task_ids = {task.id for task in tasks}

    # Check for non-existent tasks
    missing_tasks = set(task_ids) - existing_task_ids
    if missing_tasks:
        logger.info(f"Some tasks not found: {missing_tasks}")
        raise HTTPException(
            status_code=404,
            detail=f"Tasks not found: {sorted(missing_tasks)}"
        )

    # Count subtasks that will be cascade-deleted
    # This includes all descendants in the subtask tree
    logger.debug("Counting subtasks that will be cascade-deleted")
    all_task_ids_to_delete = set(task_ids)

    # BFS to find all descendant subtasks
    queue = deque(task_ids)
    visited = set(task_ids)

    while queue:
        current_id = queue.popleft()
        # Find direct subtasks
        subtasks = db.query(models.Task.id).filter(models.Task.parent_task_id == current_id).all()
        for (subtask_id,) in subtasks:
            if subtask_id not in visited:
                visited.add(subtask_id)
                all_task_ids_to_delete.add(subtask_id)
                queue.append(subtask_id)

    cascade_deleted_count = len(all_task_ids_to_delete) - len(task_ids)
    logger.debug(f"Will cascade-delete {cascade_deleted_count} subtask(s)")

    # Find candidate tasks that might become unblocked after deletion
    # These are tasks currently blocked by tasks we're deleting
    logger.debug("Finding candidate tasks that might become unblocked")
    candidate_affected = db.query(models.TaskDependency.blocked_task_id)\
        .filter(models.TaskDependency.blocking_task_id.in_(all_task_ids_to_delete))\
        .distinct()\
        .all()

    # Filter out tasks that are themselves being deleted
    candidate_task_ids = [
        row[0] for row in candidate_affected
        if row[0] not in all_task_ids_to_delete
    ]
    logger.debug(f"Found {len(candidate_task_ids)} candidate task(s) to check")

    # Calculate which candidates are currently blocked BEFORE deletion
    # This prevents reporting tasks that were never actually blocked
    blocked_before_map = {}
    if candidate_task_ids:
        logger.debug(f"Calculating is_blocked BEFORE deletion for {len(candidate_task_ids)} candidates")
        blocked_before_map = bulk_calculate_is_blocked(db, candidate_task_ids)
        actually_blocked_count = sum(blocked_before_map.values())
        logger.debug(f"{actually_blocked_count} of {len(candidate_task_ids)} candidates are actually blocked")

    # Phase 2: Delete all tasks in transaction
    logger.debug("Phase 2: Deleting tasks in transaction")

    try:
        # Delete all root tasks (CASCADE will handle subtasks, dependencies, comments, events)
        for task_id in task_ids:
            task = db.query(models.Task).filter(models.Task.id == task_id).first()
            if task:
                db.delete(task)

        db.commit()

        # Phase 3: Calculate which candidates actually became unblocked
        # Only report tasks that were blocked before AND unblocked after
        if candidate_task_ids:
            logger.debug(f"Recalculating is_blocked AFTER deletion for {len(candidate_task_ids)} candidates")
            blocked_after_map = bulk_calculate_is_blocked(db, candidate_task_ids)
            # Only include tasks that changed from blocked → unblocked
            affected_task_ids = [
                task_id for task_id in candidate_task_ids
                if blocked_before_map.get(task_id, False) and not blocked_after_map.get(task_id, False)
            ]
            logger.debug(f"After deletion, {len(affected_task_ids)} task(s) actually became unblocked")
        else:
            affected_task_ids = []

        logger.critical(
            f"Successfully bulk deleted {len(task_ids)} task(s), "
            f"cascade-deleted {cascade_deleted_count} subtask(s), "
            f"affected {len(affected_task_ids)} task(s)"
        )

        return schemas.BulkDeleteResult(
            success=True,
            deleted_count=len(task_ids),
            deleted_task_ids=task_ids,
            cascade_deleted_count=cascade_deleted_count,
            affected_tasks=affected_task_ids
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Transaction failed during bulk delete: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bulk delete failed: {str(e)}")


@app.post("/api/tasks/bulk-create", response_model=schemas.BulkOperationResult)
def bulk_create_tasks(bulk_create: schemas.BulkTaskCreate, db: Session = Depends(get_db)):
    """
    Create multiple tasks in a single transaction.

    Validates all task data before creating any tasks. If tasks have parent_task_id set,
    the parent task must already exist in the database. For creating hierarchies, create
    parent tasks first, then create child tasks in a subsequent call with parent_task_id set.
    """
    logger.info(f"Bulk creating {len(bulk_create.tasks)} tasks")
    logger.debug(f"Tasks: {[t.title for t in bulk_create.tasks]}")

    if not bulk_create.tasks:
        logger.info("No tasks provided for bulk create")
        return schemas.BulkOperationResult(success=True, processed_count=0, task_ids=[])

    # Limit batch size
    if len(bulk_create.tasks) > 500:
        logger.info(f"Batch size {len(bulk_create.tasks)} exceeds limit of 500")
        raise HTTPException(status_code=400, detail="Maximum 500 tasks per bulk operation")

    errors = []

    # Phase 1: Pre-validate ALL tasks
    logger.debug("Phase 1: Pre-validating all tasks")

    # Collect all project_ids, author_ids, owner_ids, parent_task_ids
    project_ids = set()
    author_ids = set()
    owner_ids = set()
    parent_task_ids = set()

    for i, task in enumerate(bulk_create.tasks):
        project_ids.add(task.project_id)
        if task.author_id is not None:
            author_ids.add(task.author_id)
        if task.owner_id is not None:
            owner_ids.add(task.owner_id)
        if task.parent_task_id is not None:
            if task.parent_task_id <= 0:
                errors.append(schemas.BulkOperationError(
                    task_id=i,  # Use index as temporary ID
                    error="Invalid parent task ID",
                    error_code="INVALID_PARENT_ID"
                ))
            else:
                parent_task_ids.add(task.parent_task_id)

    # Return early if there are invalid parent IDs
    if errors:
        logger.info(f"Pre-validation failed: {len(errors)} invalid parent ID(s)")
        return schemas.BulkOperationResult(
            success=False,
            processed_count=0,
            task_ids=[],
            errors=errors
        )

    # Verify all projects exist
    existing_projects = db.query(models.Project.id)\
        .filter(models.Project.id.in_(project_ids))\
        .all()
    existing_project_ids = {row[0] for row in existing_projects}

    missing_projects = project_ids - existing_project_ids
    if missing_projects:
        logger.info(f"Projects not found: {missing_projects}")
        for i, task in enumerate(bulk_create.tasks):
            if task.project_id in missing_projects:
                errors.append(schemas.BulkOperationError(
                    task_id=i,
                    error=f"Project {task.project_id} not found",
                    error_code="NOT_FOUND"
                ))

    # Verify all authors exist (if provided)
    if author_ids:
        existing_authors = db.query(models.Author.id)\
            .filter(models.Author.id.in_(author_ids))\
            .all()
        existing_author_ids = {row[0] for row in existing_authors}

        missing_authors = author_ids - existing_author_ids
        if missing_authors:
            logger.info(f"Authors not found: {missing_authors}")
            for i, task in enumerate(bulk_create.tasks):
                if task.author_id in missing_authors:
                    errors.append(schemas.BulkOperationError(
                        task_id=i,
                        error=f"Author {task.author_id} not found",
                        error_code="NOT_FOUND"
                    ))

    # Verify all owners exist (if provided)
    if owner_ids:
        existing_owners = db.query(models.Author.id)\
            .filter(models.Author.id.in_(owner_ids))\
            .all()
        existing_owner_ids = {row[0] for row in existing_owners}

        missing_owners = owner_ids - existing_owner_ids
        if missing_owners:
            logger.info(f"Owners not found: {missing_owners}")
            for i, task in enumerate(bulk_create.tasks):
                if task.owner_id in missing_owners:
                    errors.append(schemas.BulkOperationError(
                        task_id=i,
                        error=f"Owner {task.owner_id} not found",
                        error_code="NOT_FOUND"
                    ))

    # Verify all parent tasks exist and are in same project
    if parent_task_ids:
        existing_parent_tasks = db.query(models.Task)\
            .filter(models.Task.id.in_(parent_task_ids))\
            .all()
        existing_parent_map = {task.id: task for task in existing_parent_tasks}

        missing_parents = parent_task_ids - set(existing_parent_map.keys())
        if missing_parents:
            logger.info(f"Parent tasks not found: {missing_parents}")
            for i, task in enumerate(bulk_create.tasks):
                if task.parent_task_id in missing_parents:
                    errors.append(schemas.BulkOperationError(
                        task_id=i,
                        error=f"Parent task {task.parent_task_id} not found",
                        error_code="NOT_FOUND"
                    ))

        # Check same project constraint
        for i, task in enumerate(bulk_create.tasks):
            if task.parent_task_id is not None and task.parent_task_id in existing_parent_map:
                parent_task = existing_parent_map[task.parent_task_id]
                if parent_task.project_id != task.project_id:
                    logger.debug(f"Task {i}: parent task in different project")
                    errors.append(schemas.BulkOperationError(
                        task_id=i,
                        error="Parent task must be in the same project",
                        error_code="DIFFERENT_PROJECT"
                    ))

    # If validation failed, return errors
    if errors:
        logger.info(f"Pre-validation failed: {len(errors)} error(s) found")
        return schemas.BulkOperationResult(
            success=False,
            processed_count=0,
            task_ids=[],
            errors=errors
        )

    # Phase 2: Create all tasks in transaction
    logger.debug("Phase 2: Creating all tasks in transaction")

    try:
        created_task_ids = []

        # Create all tasks
        for task in bulk_create.tasks:
            db_task = models.Task(**task.model_dump())
            db.add(db_task)
            db.flush()  # Get the ID without committing
            created_task_ids.append(db_task.id)

        # Phase 3: Create task_created events for all tasks (within same transaction)
        logger.debug("Phase 3: Creating task_created events")
        for i, task_id in enumerate(created_task_ids):
            task = bulk_create.tasks[i]
            create_task_event(
                db=db,
                task_id=task_id,
                event_type=models.TaskEventType.task_created,
                actor_id=bulk_create.actor_id or task.author_id,
                metadata={
                    "title": task.title,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "tag": task.tag.value
                },
                commit=False  # Commit once at end
            )

        # Commit all changes (tasks + events) in single transaction
        db.commit()

        logger.critical(f"Successfully bulk created {len(created_task_ids)} tasks")
        return schemas.BulkOperationResult(
            success=True,
            processed_count=len(created_task_ids),
            task_ids=created_task_ids,
            errors=[]
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Transaction failed during bulk create: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bulk create failed: {str(e)}")


@app.post("/api/tasks/bulk-add-dependencies", response_model=schemas.BulkOperationResult)
def bulk_add_dependencies(bulk_deps: schemas.BulkAddDependencies, db: Session = Depends(get_db)):
    """
    Add multiple task dependencies in a single transaction.

    Validates all dependencies before creating any. Checks for:
    - Task existence
    - Same project constraint
    - Circular dependencies (within batch and against existing graph)
    - Parent-subtask deadlock prevention
    - Duplicate dependencies
    """
    logger.info(f"Bulk adding {len(bulk_deps.dependencies)} dependencies")
    logger.debug(f"Dependencies: {[(d.blocking_task_id, d.blocked_task_id) for d in bulk_deps.dependencies]}")

    if not bulk_deps.dependencies:
        logger.info("No dependencies provided for bulk add")
        return schemas.BulkOperationResult(success=True, processed_count=0, task_ids=[])

    # Limit batch size
    if len(bulk_deps.dependencies) > 500:
        logger.info(f"Batch size {len(bulk_deps.dependencies)} exceeds limit of 500")
        raise HTTPException(status_code=400, detail="Maximum 500 dependencies per bulk operation")

    errors = []

    # Phase 1: Pre-validate ALL dependencies
    logger.debug("Phase 1: Pre-validating all dependencies")

    # Collect all task IDs involved
    all_task_ids = set()
    for dep in bulk_deps.dependencies:
        all_task_ids.add(dep.blocking_task_id)
        all_task_ids.add(dep.blocked_task_id)

    # Fetch all tasks in a single query
    tasks = db.query(models.Task).filter(models.Task.id.in_(all_task_ids)).all()
    tasks_dict = {task.id: task for task in tasks}

    # Check for non-existent tasks
    missing_tasks = all_task_ids - set(tasks_dict.keys())
    if missing_tasks:
        logger.info(f"Tasks not found: {missing_tasks}")
        for i, dep in enumerate(bulk_deps.dependencies):
            if dep.blocking_task_id in missing_tasks:
                errors.append(schemas.BulkOperationError(
                    task_id=dep.blocked_task_id,  # Use blocked task ID for error tracking
                    error=f"Blocking task {dep.blocking_task_id} not found",
                    error_code="NOT_FOUND"
                ))
            elif dep.blocked_task_id in missing_tasks:
                errors.append(schemas.BulkOperationError(
                    task_id=dep.blocked_task_id,  # Use blocked task ID for error tracking
                    error=f"Blocked task {dep.blocked_task_id} not found",
                    error_code="NOT_FOUND"
                ))

    # Return early if tasks are missing
    if errors:
        logger.info(f"Pre-validation failed: {len(errors)} task(s) not found")
        return schemas.BulkOperationResult(
            success=False,
            processed_count=0,
            task_ids=[],
            errors=errors
        )

    # Check same project constraint
    logger.debug("Checking same project constraint")
    for i, dep in enumerate(bulk_deps.dependencies):
        blocking_task = tasks_dict[dep.blocking_task_id]
        blocked_task = tasks_dict[dep.blocked_task_id]

        if blocking_task.project_id != blocked_task.project_id:
            logger.debug(f"Dependency {i}: tasks in different projects")
            errors.append(schemas.BulkOperationError(
                task_id=dep.blocked_task_id,  # Use blocked task ID for error tracking
                error="Tasks must be in the same project to create a dependency",
                error_code="DIFFERENT_PROJECT"
            ))

    # Check for self-blocking
    logger.debug("Checking for self-blocking")
    for i, dep in enumerate(bulk_deps.dependencies):
        if dep.blocking_task_id == dep.blocked_task_id:
            logger.debug(f"Dependency {i}: task cannot block itself")
            errors.append(schemas.BulkOperationError(
                task_id=dep.blocked_task_id,  # Use blocked task ID for error tracking
                error="A task cannot block itself",
                error_code="SELF_BLOCKING"
            ))

    # Check for existing dependencies
    logger.debug("Checking for existing dependencies")
    existing_deps = db.query(models.TaskDependency)\
        .filter(
            models.TaskDependency.blocking_task_id.in_([d.blocking_task_id for d in bulk_deps.dependencies]),
            models.TaskDependency.blocked_task_id.in_([d.blocked_task_id for d in bulk_deps.dependencies])
        )\
        .all()

    existing_dep_pairs = {(dep.blocking_task_id, dep.blocked_task_id) for dep in existing_deps}

    for i, dep in enumerate(bulk_deps.dependencies):
        if (dep.blocking_task_id, dep.blocked_task_id) in existing_dep_pairs:
            logger.debug(f"Dependency {i}: already exists")
            errors.append(schemas.BulkOperationError(
                task_id=dep.blocked_task_id,  # Use blocked task ID for error tracking
                error="Dependency already exists",
                error_code="DUPLICATE"
            ))

    # Check for duplicates within the batch
    logger.debug("Checking for duplicates within batch")
    seen_deps = set()
    for i, dep in enumerate(bulk_deps.dependencies):
        dep_pair = (dep.blocking_task_id, dep.blocked_task_id)
        if dep_pair in seen_deps:
            logger.debug(f"Dependency {i}: duplicate within batch")
            errors.append(schemas.BulkOperationError(
                task_id=dep.blocked_task_id,  # Use blocked task ID for error tracking
                error="Duplicate dependency in batch",
                error_code="DUPLICATE"
            ))
        seen_deps.add(dep_pair)

    # Check for circular dependencies (including within the batch itself)
    logger.debug("Checking for circular dependencies (including batch)")

    # Build combined graph: existing DB dependencies + batch dependencies
    from collections import defaultdict, deque

    # Get initial task IDs from batch
    batch_task_ids = set()
    for dep in bulk_deps.dependencies:
        batch_task_ids.add(dep.blocking_task_id)
        batch_task_ids.add(dep.blocked_task_id)

    # Build adjacency list with existing dependencies
    # Optimization: Only load dependencies reachable from batch task IDs
    # This prevents loading the entire dependency graph on large datasets
    logger.debug(f"Loading reachable subgraph from {len(batch_task_ids)} batch task IDs")

    graph = defaultdict(set)
    reverse_graph = defaultdict(set)  # For backward traversal
    visited_tasks = set()
    tasks_to_explore = deque(batch_task_ids)

    # BFS to find all transitively reachable tasks and their dependencies
    while tasks_to_explore:
        current_batch = []
        # Process up to 100 tasks at a time
        for _ in range(min(100, len(tasks_to_explore))):
            if tasks_to_explore:
                task_id = tasks_to_explore.popleft()
                if task_id not in visited_tasks:
                    visited_tasks.add(task_id)
                    current_batch.append(task_id)

        if not current_batch:
            break

        # Load dependencies where these tasks are either blocking or blocked
        deps = db.query(models.TaskDependency).filter(
            (models.TaskDependency.blocking_task_id.in_(current_batch)) |
            (models.TaskDependency.blocked_task_id.in_(current_batch))
        ).all()

        # Add to graph and discover new tasks
        for dep in deps:
            graph[dep.blocking_task_id].add(dep.blocked_task_id)
            reverse_graph[dep.blocked_task_id].add(dep.blocking_task_id)

            # Add newly discovered tasks to explore
            if dep.blocking_task_id not in visited_tasks:
                tasks_to_explore.append(dep.blocking_task_id)
            if dep.blocked_task_id not in visited_tasks:
                tasks_to_explore.append(dep.blocked_task_id)

    logger.debug(f"Loaded subgraph with {len(visited_tasks)} tasks and {sum(len(v) for v in graph.values())} dependencies")

    # Add batch dependencies to graph and check for cycles
    for i, dep in enumerate(bulk_deps.dependencies):
        # Temporarily add this edge to the graph
        graph[dep.blocking_task_id].add(dep.blocked_task_id)

        # Check for cycle using BFS
        visited = set()
        queue = deque([dep.blocked_task_id])
        cycle_detected = False

        while queue and not cycle_detected:
            current = queue.popleft()

            if current == dep.blocking_task_id:
                # Found a cycle back to the blocking task
                cycle_detected = True
                break

            if current in visited:
                continue
            visited.add(current)

            # Add neighbors to queue
            for neighbor in graph.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)

        if cycle_detected:
            logger.debug(f"Dependency {i}: circular dependency detected (in batch or with existing)")
            errors.append(schemas.BulkOperationError(
                task_id=dep.blocked_task_id,  # Use blocked task ID for error tracking
                error="Cannot create dependency: would create a circular dependency",
                error_code="CIRCULAR_DEPENDENCY"
            ))
            # Remove the invalid edge from graph
            graph[dep.blocking_task_id].discard(dep.blocked_task_id)

    # Check for parent-subtask deadlock
    logger.debug("Checking for parent-subtask deadlock")
    for i, dep in enumerate(bulk_deps.dependencies):
        if is_ancestor_in_subtask_tree(db, dep.blocking_task_id, dep.blocked_task_id):
            logger.debug(f"Dependency {i}: parent-subtask deadlock detected")
            errors.append(schemas.BulkOperationError(
                task_id=dep.blocked_task_id,  # Use blocked task ID for error tracking
                error="Cannot create dependency: a parent task cannot block its own subtask (would create deadlock)",
                error_code="DEADLOCK"
            ))

    # If validation failed, return errors
    if errors:
        logger.info(f"Pre-validation failed: {len(errors)} error(s) found")
        return schemas.BulkOperationResult(
            success=False,
            processed_count=0,
            task_ids=[],
            errors=errors
        )

    # Phase 2: Create all dependencies in transaction
    logger.debug("Phase 2: Creating all dependencies in transaction")

    try:
        created_dependencies = []

        # Create all dependencies
        for dep in bulk_deps.dependencies:
            db_dependency = models.TaskDependency(
                blocking_task_id=dep.blocking_task_id,
                blocked_task_id=dep.blocked_task_id
            )
            db.add(db_dependency)
            created_dependencies.append((dep.blocking_task_id, dep.blocked_task_id))

        # Phase 3: Create dependency_added events for all dependencies (within same transaction)
        logger.debug("Phase 3: Creating dependency_added events")
        for blocking_id, blocked_id in created_dependencies:
            blocking_task = tasks_dict[blocking_id]
            create_task_event(
                db=db,
                task_id=blocked_id,
                event_type=models.TaskEventType.dependency_added,
                actor_id=bulk_deps.actor_id,
                metadata={
                    "blocking_task_id": blocking_id,
                    "blocking_task_title": blocking_task.title
                },
                commit=False  # Commit once at end
            )

        # Commit all changes (dependencies + events) in single transaction
        db.commit()

        # Get all affected blocked task IDs for response
        affected_task_ids = list(set(blocked_id for _, blocked_id in created_dependencies))

        logger.critical(f"Successfully bulk added {len(created_dependencies)} dependencies")
        return schemas.BulkOperationResult(
            success=True,
            processed_count=len(created_dependencies),
            task_ids=affected_task_ids,  # Return blocked task IDs
            errors=[]
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Transaction failed during bulk add dependencies: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bulk add dependencies failed: {str(e)}")


