from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional

from database import get_db, engine, Base
import models
import schemas

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

    # Add comment count to each task
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
                "comment_count": len(task.comments)
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

    # Add comment count
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
            "comment_count": len(task.comments),
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        result.append(task_dict)

    return result


@app.post("/api/tasks", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    # Verify project exists
    project = db.query(models.Project).filter(models.Project.id == task.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_task = models.Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


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
    return task


@app.put("/api/tasks/{task_id}", response_model=schemas.Task)
def update_task(task_id: int, task_update: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task


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
