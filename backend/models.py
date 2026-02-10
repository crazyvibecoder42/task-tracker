from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, Numeric
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


class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    projects = relationship("Project", back_populates="author")
    tasks = relationship("Task", foreign_keys="Task.author_id", back_populates="author")
    owned_tasks = relationship("Task", foreign_keys="Task.owner_id", back_populates="owner")
    comments = relationship("Comment", back_populates="author")
    events = relationship("TaskEvent", back_populates="actor")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"))
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    author = relationship("Author", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    tag = Column(Enum(TaskTag, name="task_tag", create_type=False), nullable=False, default=TaskTag.feature)
    priority = Column(Enum(TaskPriority, name="task_priority", create_type=False), nullable=False, default=TaskPriority.P1)
    status = Column(Enum(TaskStatus, name="task_status", create_type=False), nullable=False, default=TaskStatus.backlog)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"))
    owner_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"))
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
    author = relationship("Author", foreign_keys=[author_id], back_populates="tasks")
    owner = relationship("Author", foreign_keys=[owner_id], back_populates="owned_tasks")
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
    actor_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"))
    field_name = Column(String(255))
    old_value = Column(Text)
    new_value = Column(Text)
    event_metadata = Column("metadata", JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    task = relationship("Task", back_populates="events")
    actor = relationship("Author", back_populates="events")


class TaskAttachment(Base):
    __tablename__ = "task_attachments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    task = relationship("Task", back_populates="attachments")
    uploader = relationship("Author")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"))
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("Author", back_populates="comments")
