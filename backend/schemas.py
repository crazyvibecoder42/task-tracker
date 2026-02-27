from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List, Literal
from enum import Enum


class TaskTag(str, Enum):
    bug = "bug"
    feature = "feature"
    idea = "idea"


class TaskPriority(str, Enum):
    P0 = "P0"
    P1 = "P1"


class TaskEventType(str, Enum):
    """
    Known event types for task audit trail.

    Note: Database stores event_type as VARCHAR(50) for extensibility.
    This enum provides type safety for standard event types, but the
    database may contain additional custom event types without migration.
    Future MCP plugins and custom integrations can add new event types
    without requiring database schema changes.
    """
    task_created = "task_created"
    status_change = "status_change"
    field_update = "field_update"
    ownership_change = "ownership_change"
    dependency_added = "dependency_added"
    dependency_removed = "dependency_removed"
    comment_added = "comment_added"
    attachment_added = "attachment_added"
    attachment_deleted = "attachment_deleted"
    link_added = "link_added"
    link_removed = "link_removed"
    metadata_updated = "metadata_updated"


class TaskStatus(str, Enum):
    backlog = "backlog"
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    review = "review"
    done = "done"
    not_needed = "not_needed"


# Role type aliases for validation
UserRole = Literal["admin", "editor", "viewer"]
ProjectMemberRole = Literal["owner", "editor", "viewer"]
TeamMemberRole = Literal["admin", "member"]


# User schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100, description="Password must be at least 8 characters")
    role: Optional[UserRole] = "editor"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: int
    role: UserRole = "editor"
    is_active: bool = True
    email_verified: bool = False
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Auth schemas
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100, description="Password must be at least 8 characters")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# API Key schemas
class APIKeyCreate(BaseModel):
    name: str
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key: Optional[str] = None  # Only returned on creation
    key_preview: Optional[str] = None
    user_id: int
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Team schemas
class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class Team(TeamBase):
    id: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Team Member schemas
class TeamMemberCreate(BaseModel):
    user_id: int
    role: TeamMemberRole = "member"


class TeamMemberUpdate(BaseModel):
    role: TeamMemberRole


class TeamMemberResponse(BaseModel):
    id: int
    team_id: int
    user_id: int
    user: Optional[User] = None
    role: TeamMemberRole
    created_at: datetime

    class Config:
        from_attributes = True


class TeamWithMembers(Team):
    members: List[TeamMemberResponse] = []
    creator: Optional[User] = None

    class Config:
        from_attributes = True


class TeamWithProjects(Team):
    projects: List['Project'] = []
    members: List[TeamMemberResponse] = []
    creator: Optional[User] = None

    class Config:
        from_attributes = True


# Project Member schemas
class ProjectMemberCreate(BaseModel):
    user_id: int
    role: ProjectMemberRole = "editor"


class ProjectMemberResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    user: Optional[User] = None
    role: ProjectMemberRole
    created_at: datetime

    class Config:
        from_attributes = True


# Comment schemas
class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    pass


class CommentUpdate(BaseModel):
    content: Optional[str] = None


class Comment(CommentBase):
    id: int
    task_id: int
    author_id: Optional[int]
    author: Optional[User] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Task Attachment schemas
class AttachmentBase(BaseModel):
    filename: str
    original_filename: str
    mime_type: str
    file_size: int


class Attachment(AttachmentBase):
    id: int
    task_id: int
    filepath: str
    uploaded_by: Optional[int]
    uploader: Optional[User] = None
    created_at: datetime

    class Config:
        from_attributes = True


# External Link schemas
class ExternalLinkBase(BaseModel):
    url: str
    label: Optional[str] = None


class ExternalLinkCreate(ExternalLinkBase):
    pass


class ExternalLink(BaseModel):
    url: str
    label: Optional[str] = None
    created_at: str  # ISO datetime string


# Metadata schemas
class MetadataUpdate(BaseModel):
    key: str
    value: str


# Task Event schemas
class TaskEventBase(BaseModel):
    task_id: int
    event_type: TaskEventType
    actor_id: Optional[int] = None
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    metadata: Optional[dict] = Field(None, validation_alias="event_metadata")


class TaskEvent(TaskEventBase):
    id: int
    created_at: datetime
    actor: Optional[User] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class TaskEventsList(BaseModel):
    events: List[TaskEvent] = []
    total_count: int


# Subproject schemas
class SubprojectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class SubprojectUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class SubprojectResponse(BaseModel):
    id: int
    project_id: int
    name: str
    subproject_number: int
    is_default: bool
    is_active: bool = False  # computed field, NOT a DB column — populated by endpoint logic
    created_at: datetime

    class Config:
        from_attributes = True


# Task schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    tag: TaskTag = TaskTag.feature
    priority: TaskPriority = TaskPriority.P1
    status: TaskStatus = TaskStatus.todo  # Aligned with DB default in init.sql
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = Field(None, ge=0, description="Estimated hours (must be >= 0)")
    actual_hours: Optional[float] = Field(None, ge=0, description="Actual hours spent (must be >= 0)")


class TaskCreate(TaskBase):
    project_id: int
    owner_id: Optional[int] = None
    parent_task_id: Optional[int] = None
    subproject_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tag: Optional[TaskTag] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    owner_id: Optional[int] = None
    parent_task_id: Optional[int] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = Field(None, ge=0, description="Estimated hours (must be >= 0)")
    actual_hours: Optional[float] = Field(None, ge=0, description="Actual hours spent (must be >= 0)")
    subproject_id: Optional[int] = None


class TakeOwnership(BaseModel):
    force: bool = False


class Task(TaskBase):
    id: int
    project_id: int
    author_id: Optional[int]
    author: Optional[User] = None
    owner_id: Optional[int]
    owner: Optional[User] = None
    parent_task_id: Optional[int] = None
    subproject_id: Optional[int] = None
    subproject: Optional['SubprojectResponse'] = None
    comments: List[Comment] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)
    external_links: List[dict] = Field(default_factory=list)
    custom_metadata: dict = Field(default_factory=dict)
    is_blocked: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskSummary(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    tag: TaskTag = TaskTag.feature
    priority: TaskPriority = TaskPriority.P1
    status: TaskStatus = TaskStatus.todo
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    project_id: int
    author_id: Optional[int]
    author: Optional[User] = None
    owner_id: Optional[int]
    owner: Optional[User] = None
    parent_task_id: Optional[int] = None
    subproject_id: Optional[int] = None
    subproject: Optional['SubprojectResponse'] = None
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


# Kanban settings schemas
class KanbanWipLimits(BaseModel):
    todo: Optional[int] = None
    in_progress: Optional[int] = 5
    blocked: Optional[int] = None
    review: Optional[int] = 3
    backlog: Optional[int] = None
    done: Optional[int] = None


class KanbanSettings(BaseModel):
    wip_limits: KanbanWipLimits = Field(default_factory=KanbanWipLimits)
    hidden_columns: List[str] = Field(default_factory=lambda: ["backlog", "done"])


# Project schemas
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    # Note: author_id is automatically set to current user by backend
    # Not accepted from client to prevent privilege confusion
    team_id: Optional[int] = Field(default=None, ge=1)  # Must be positive if provided


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectTeamTransfer(BaseModel):
    """Schema for transferring project to a different team or making it personal."""
    team_id: Optional[int] = Field(
        None,
        description="Target team ID, or None to convert to personal project"
    )


class Project(ProjectBase):
    id: int
    author_id: Optional[int]
    author: Optional[User] = None
    team_id: Optional[int] = None
    team: Optional[Team] = None
    kanban_settings: Optional[KanbanSettings] = None
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
    not_needed_tasks: int
    p0_tasks: int
    p1_tasks: int
    bug_count: int
    feature_count: int
    idea_count: int


# Bulk operation schemas
class BulkOperationError(BaseModel):
    task_id: Optional[int]  # None for operation-level errors (permissions, validation)
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


# Search result schemas
class SearchResultTask(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    tag: TaskTag
    priority: TaskPriority
    status: TaskStatus
    project_id: int
    parent_task_id: Optional[int] = None
    rank: float  # Relevance score from ts_rank
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SearchResultProject(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    rank: float  # Relevance score from ts_rank
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SearchResultComment(BaseModel):
    id: int
    content: str
    task_id: int
    task_title: str  # Include task title for context
    rank: float  # Relevance score from ts_rank
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SearchResults(BaseModel):
    tasks: List[SearchResultTask] = []
    projects: List[SearchResultProject] = []
    comments: List[SearchResultComment] = []
    total_results: int = 0


# Resolve forward references for circular dependencies
TeamWithProjects.model_rebuild()
TaskWithDependencies.model_rebuild()
