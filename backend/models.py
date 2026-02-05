from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class TaskTag(str, enum.Enum):
    bug = "bug"
    feature = "feature"
    idea = "idea"


class TaskPriority(str, enum.Enum):
    P0 = "P0"
    P1 = "P1"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"


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
    status = Column(Enum(TaskStatus, name="task_status", create_type=False), nullable=False, default=TaskStatus.pending)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"))
    owner_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="tasks")
    author = relationship("Author", foreign_keys=[author_id], back_populates="tasks")
    owner = relationship("Author", foreign_keys=[owner_id], back_populates="owned_tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")


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
