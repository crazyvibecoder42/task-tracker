from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
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
    status = Column(Enum(TaskStatus, name="task_status", create_type=False), nullable=False, default=TaskStatus.todo)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"))
    owner_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"))
    parent_task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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
    event_type = Column(Enum(TaskEventType, name="task_event_type", create_type=False), nullable=False)
    actor_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"))
    field_name = Column(String(255))
    old_value = Column(Text)
    new_value = Column(Text)
    event_metadata = Column("metadata", JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    task = relationship("Task", back_populates="events")
    actor = relationship("Author", back_populates="events")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("Author", back_populates="comments")
