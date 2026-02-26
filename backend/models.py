from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
import enum
from database import Base


class TaskTag(str, enum.Enum):
    bug = "bug"
    feature = "feature"
    idea = "idea"


class TaskPriority(str, enum.Enum):
    P0 = "P0"
    P1 = "P1"


class TaskEventType(str, enum.Enum):
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


class TaskStatus(str, enum.Enum):
    backlog = "backlog"
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    review = "review"
    done = "done"


class User(Base):
    __tablename__ = "users"  # Renamed from authors in migration 006

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Auth fields (added in migration 006)
    password_hash = Column(String(255), nullable=True)  # Nullable for migrated users
    role = Column(String(50), nullable=False, server_default="editor")
    is_active = Column(Boolean, nullable=False, server_default="true")
    email_verified = Column(Boolean, nullable=False, server_default="false")
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    projects = relationship("Project", back_populates="author")
    tasks = relationship("Task", foreign_keys="Task.author_id", back_populates="author")
    owned_tasks = relationship("Task", foreign_keys="Task.owner_id", back_populates="owner")
    comments = relationship("Comment", back_populates="author")
    events = relationship("TaskEvent", back_populates="actor")
    project_memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    team_memberships = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan")
    created_teams = relationship("Team", foreign_keys="Team.created_by", back_populates="creator")


class Team(Base):
    """
    Team table for organizing users and projects.

    Teams provide a layer of organization between users and projects:
    - Team admins have full control over team management
    - Team members automatically access all team projects (auto-join)
    - Users can belong to multiple teams
    - Projects can belong to at most one team
    """
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_teams")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="team")


class TeamMember(Base):
    """
    Team membership table for user-team relationships.

    Defines user access to teams with two roles:
    - admin: Full team control (manage members, projects)
    - member: Standard access (view team, access team projects)
    """
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False, server_default="member")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"))
    search_vector = Column(TSVECTOR)
    kanban_settings = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    author = relationship("User", back_populates="projects")
    team = relationship("Team", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    tag = Column(Enum(TaskTag, name="task_tag", create_type=False), nullable=False, default=TaskTag.feature)
    priority = Column(Enum(TaskPriority, name="task_priority", create_type=False), nullable=False, default=TaskPriority.P1)
    status = Column(Enum(TaskStatus, name="task_status", create_type=False), nullable=False, default=TaskStatus.todo)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    parent_task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Time tracking fields
    due_date = Column(DateTime(timezone=True), nullable=True)
    estimated_hours = Column(Numeric(10, 2), nullable=True)
    actual_hours = Column(Numeric(10, 2), nullable=True)

    # Rich context fields
    external_links = Column(JSONB, default=list)
    custom_metadata = Column(JSONB, default=dict)

    # Relationships
    project = relationship("Project", back_populates="tasks")
    author = relationship("User", foreign_keys=[author_id], back_populates="tasks")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")

    # Subtask relationships (self-referential)
    parent_task = relationship("Task", remote_side=[id], back_populates="subtasks", foreign_keys=[parent_task_id])
    subtasks = relationship("Task", back_populates="parent_task", cascade="all, delete-orphan", foreign_keys=[parent_task_id])

    # Dependency relationships (many-to-many through task_dependencies)
    blocking_dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.blocking_task_id",
        back_populates="blocking_task",
        cascade="all, delete-orphan"
    )
    blocked_dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.blocked_task_id",
        back_populates="blocked_task",
        cascade="all, delete-orphan"
    )

    # Event relationships
    events = relationship("TaskEvent", back_populates="task", cascade="all, delete-orphan")

    # Attachment relationships
    attachments = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    blocking_task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    blocked_task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    blocking_task = relationship("Task", foreign_keys=[blocking_task_id], back_populates="blocking_dependencies")
    blocked_task = relationship("Task", foreign_keys=[blocked_task_id], back_populates="blocked_dependencies")


class TaskEvent(Base):
    __tablename__ = "task_events"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)

    # event_type stored as VARCHAR(50) for flexibility (not PostgreSQL enum)
    # This allows adding new event types without database migrations.
    # Python TaskEventType enum provides validation layer for known types,
    # but the database may contain additional custom event types.
    event_type = Column(String(50), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    field_name = Column(String(255))
    old_value = Column(Text)
    new_value = Column(Text)
    event_metadata = Column("metadata", JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    task = relationship("Task", back_populates="events")
    actor = relationship("User", back_populates="events")


class TaskAttachment(Base):
    __tablename__ = "task_attachments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    task = relationship("Task", back_populates="attachments")
    uploader = relationship("User")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("User", back_populates="comments")


class ProjectMember(Base):
    """
    Project membership table for project-level permissions.

    Defines user access to specific projects with granular roles:
    - viewer: Read-only access
    - editor: Can create/edit tasks
    - owner: Full control over project
    """
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False, server_default="editor")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("Project")
    user = relationship("User", back_populates="project_memberships")


class ApiKey(Base):
    """
    API keys for programmatic access to the Task Tracker API.

    Supports:
    - API key authentication for agents and scripts
    - Optional expiration dates
    - Rate limiting (future)
    - Project-scoped permissions (future)
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    project_ids = Column(JSONB, server_default="[]")
    permissions = Column(JSONB, server_default="[]")
    rate_limit = Column(Integer, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="api_keys")


class RefreshToken(Base):
    """
    Refresh tokens for JWT token rotation.

    Stores JWT refresh token identifiers (JTI) for:
    - Token revocation
    - Token rotation
    - Session management
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_jti = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
