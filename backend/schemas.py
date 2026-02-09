from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from enum import Enum


class TaskTag(str, Enum):
    bug = "bug"
    feature = "feature"
    idea = "idea"


class TaskPriority(str, Enum):
    P0 = "P0"
    P1 = "P1"


class TaskEventType(str, Enum):
    task_created = "task_created"
    status_change = "status_change"
    field_update = "field_update"
    ownership_change = "ownership_change"
    dependency_added = "dependency_added"
    dependency_removed = "dependency_removed"
    comment_added = "comment_added"


class TaskStatus(str, Enum):
    backlog = "backlog"
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    review = "review"
    done = "done"


# Author schemas
class AuthorBase(BaseModel):
    name: str
    email: EmailStr


class AuthorCreate(AuthorBase):
    pass


class AuthorUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class Author(AuthorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Comment schemas
class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    author_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: Optional[str] = None


class Comment(CommentBase):
    id: int
    task_id: int
    author_id: Optional[int]
    author: Optional[Author] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Task Event schemas
class TaskEventBase(BaseModel):
    task_id: int
    event_type: TaskEventType
    actor_id: Optional[int] = None
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    event_metadata: Optional[dict] = None


class TaskEvent(TaskEventBase):
    id: int
    created_at: datetime
    actor: Optional[Author] = None

    class Config:
        from_attributes = True


class TaskEventsList(BaseModel):
    events: List[TaskEvent] = []
    total: int


# Task schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    tag: TaskTag = TaskTag.feature
    priority: TaskPriority = TaskPriority.P1
    status: TaskStatus = TaskStatus.todo


class TaskCreate(TaskBase):
    project_id: int
    author_id: Optional[int] = None
    owner_id: Optional[int] = None
    parent_task_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tag: Optional[TaskTag] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    owner_id: Optional[int] = None
    parent_task_id: Optional[int] = None


class TakeOwnership(BaseModel):
    author_id: int
    force: bool = False


class Task(TaskBase):
    id: int
    project_id: int
    author_id: Optional[int]
    author: Optional[Author] = None
    owner_id: Optional[int]
    owner: Optional[Author] = None
    parent_task_id: Optional[int] = None
    comments: List[Comment] = []
    is_blocked: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskSummary(TaskBase):
    id: int
    project_id: int
    author_id: Optional[int]
    author: Optional[Author] = None
    owner_id: Optional[int]
    owner: Optional[Author] = None
    parent_task_id: Optional[int] = None
    comment_count: int = 0
    is_blocked: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Task Dependency schemas
class TaskDependencyBase(BaseModel):
    blocking_task_id: int
    blocked_task_id: int


class TaskDependencyCreate(BaseModel):
    blocking_task_id: int


class TaskDependency(TaskDependencyBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TaskWithDependencies(Task):
    subtasks: List['TaskSummary'] = []
    blocking_tasks: List['TaskSummary'] = []  # Tasks that block this one
    blocked_tasks: List['TaskSummary'] = []   # Tasks that this one blocks
    is_blocked: bool = False

    class Config:
        from_attributes = True


class TaskProgress(BaseModel):
    task_id: int
    total_subtasks: int
    completed_subtasks: int
    completion_percentage: float


# Project schemas
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    author_id: Optional[int] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Project(ProjectBase):
    id: int
    author_id: Optional[int]
    author: Optional[Author] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectWithTasks(Project):
    tasks: List[TaskSummary] = []

    class Config:
        from_attributes = True


class ProjectStats(BaseModel):
    id: int
    name: str
    total_tasks: int
    backlog_tasks: int
    todo_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    review_tasks: int
    done_tasks: int
    p0_tasks: int
    p1_tasks: int
    bug_count: int
    feature_count: int
    idea_count: int


# Bulk operation schemas
class BulkOperationError(BaseModel):
    task_id: int
    error: str
    error_code: str  # NOT_FOUND, BLOCKED, INCOMPLETE_SUBTASKS, etc.


class BulkOperationResult(BaseModel):
    success: bool
    processed_count: int = 0
    task_ids: List[int] = []
    errors: List[BulkOperationError] = []


class BulkTaskUpdate(BaseModel):
    task_ids: List[int]
    updates: TaskUpdate
    actor_id: Optional[int] = None


class BulkTakeOwnership(BaseModel):
    task_ids: List[int]
    author_id: int
    force: bool = False


class BulkDeleteResult(BaseModel):
    success: bool
    deleted_count: int
    deleted_task_ids: List[int]
    cascade_deleted_count: int  # Subtasks auto-deleted
    affected_tasks: List[int]  # Tasks that became unblocked


class BulkTaskCreate(BaseModel):
    tasks: List[TaskCreate]
    actor_id: Optional[int] = None


class BulkTaskDelete(BaseModel):
    task_ids: List[int]
    actor_id: Optional[int] = None


class BulkAddDependencies(BaseModel):
    dependencies: List[TaskDependencyBase]
    actor_id: Optional[int] = None
