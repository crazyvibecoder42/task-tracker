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


class TaskStatus(str, Enum):
    pending = "pending"
    completed = "completed"


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


# Task schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    tag: TaskTag = TaskTag.feature
    priority: TaskPriority = TaskPriority.P1
    status: TaskStatus = TaskStatus.pending


class TaskCreate(TaskBase):
    project_id: int
    author_id: Optional[int] = None
    owner_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tag: Optional[TaskTag] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    owner_id: Optional[int] = None


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
    comments: List[Comment] = []
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
    comment_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
    pending_tasks: int
    completed_tasks: int
    p0_tasks: int
    p1_tasks: int
    bug_count: int
    feature_count: int
    idea_count: int
