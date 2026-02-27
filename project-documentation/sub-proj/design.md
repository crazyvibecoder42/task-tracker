# Sub-Projects — Design Document

> A lightweight grouping layer that lets tasks within a project be organized into named sub-projects, surfaced in the sidebar as a filter and accessible to AI agents via dedicated MCP tools.

## Overview

Projects in the Task Tracker can contain dozens or hundreds of tasks spanning unrelated workstreams. Sub-projects provide a named, lightweight grouping layer directly beneath a project — tasks optionally belong to one sub-project, and the sidebar surfaces these groups as click-to-filter entries when a user is viewing that project.

Every project automatically receives a non-deletable **Default** sub-project (subproject_number = 1). Users create additional sub-projects freely; each receives a monotonically increasing `subproject_number` scoped to its parent project. When a user-created sub-project is deleted, its tasks retain their `project_id` but have `subproject_id` set to NULL (they become "Unassigned"). Sub-projects have no independent lifecycle beyond their tasks — "active" is a derived property indicating at least one task with status outside `('done', 'not_needed')`.

This feature extends the backend (new table + FK, new/updated endpoints), the MCP server (new tools + updated parameter lists), and the frontend (sidebar sub-navigation, task filtering, and task assignment forms).

## Goals and Non-Goals

### Goals
- Persist sub-projects as first-class database entities scoped to a project
- Allow each task to optionally belong to one sub-project (nullable FK)
- Auto-create a non-deletable "Default" sub-project for every new project
- Expose sub-project CRUD via REST API and MCP tools
- Filter tasks by sub-project in existing `list_tasks` and `list_actionable_tasks` MCP tools
- Provide `list_active_subprojects` and `list_actionable_tasks_in_subproject` MCP tools
- Render sub-projects in the sidebar as clickable filters when viewing a project page
- Support assigning/changing a task's sub-project via the task create and edit forms

### Non-Goals
- Sub-project-level permissions (sub-projects inherit project permissions)
- Nested sub-projects (no hierarchy beyond project → sub-project → task)
- Sub-project statistics or progress rollups (out of scope for v1)
- Moving tasks between projects when reassigning sub-projects
- Sub-project ordering beyond `subproject_number` ascending

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Next.js)                                         │
│  ┌──────────────────────┐   ┌─────────────────────────────┐ │
│  │  Sidebar.tsx         │   │  projects/[id]/page.tsx     │ │
│  │  - detects active    │   │  - reads ?subproject=N URL  │ │
│  │    project from URL  │   │    param                    │ │
│  │  - loads subprojects │   │  - passes subproject_id to  │ │
│  │  - renders filter    │   │    getTasks()               │ │
│  │    links with        │   │  - shows assignment         │ │
│  │    active indicators │   │    dropdown in create form  │ │
│  └──────────────────────┘   └─────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  lib/api.ts                                          │   │
│  │  getSubprojects(), createSubproject(),               │   │
│  │  updateSubproject(), deleteSubproject()              │   │
│  │  getTasks({ subproject_id })  ← updated             │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP
┌────────────────────────────▼────────────────────────────────┐
│  Backend (FastAPI / SQLAlchemy)                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  main.py                                             │   │
│  │  POST /api/projects/{id}/subprojects                 │   │
│  │  GET  /api/projects/{id}/subprojects                 │   │
│  │  GET  /api/projects/{id}/subprojects/active          │   │
│  │  PUT  /api/subprojects/{id}                          │   │
│  │  DELETE /api/subprojects/{id}                        │   │
│  │  GET /api/tasks?subproject_id=N  ← updated           │   │
│  │  GET /api/tasks/actionable?subproject_id=N ← updated │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  models.py + schemas.py                              │   │
│  │  Subproject model, SubprojectCreate/Update/Response  │   │
│  │  Task.subproject_id FK                               │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  MCP Server (stdio_server.py)                               │
│  list_active_subprojects(project_id)            ← new       │
│  list_actionable_tasks_in_subproject(pid, spid) ← new       │
│  list_tasks(..., subproject_id=None)            ← updated   │
│  list_actionable_tasks(..., subproject_id=None) ← updated   │
│  create_task(..., subproject_id=None)           ← updated   │
│  update_task(task_id, subproject_id=None, ...)  ← updated   │
│  + CRUD tools for sub-projects                  ← new       │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### Subproject Number as Per-Project Monotonic Counter
**Decision**: Add `subproject_number INTEGER NOT NULL` with a `UNIQUE(project_id, subproject_number)` constraint. Computed at INSERT time using `SELECT COALESCE(MAX(subproject_number), 0) + 1 FROM subprojects WHERE project_id = ?` inside the same transaction.

**Rationale**: Provides human-friendly, project-scoped identifiers (SP-1, SP-2…) without global auto-increment gaps polluting the sequence.

**Trade-offs**: Concurrent inserts on the same project could theoretically race; the unique constraint acts as a safety net (insert retry on conflict). At task tracker scale this is not a practical concern.

### Default Subproject as a Real Database Row
**Decision**: Auto-create a "Default" sub-project row (`is_default = true`, `subproject_number = 1`) in the same transaction as project creation. Enforce non-deletion via an API-layer check (`403 if subproject.is_default`), not a DB constraint.

**Rationale**: Treating Default as a real row simplifies queries (no special NULL-handling needed in the active-subprojects query), keeps the API uniform, and lets users rename it if desired.

**Trade-offs**: Requires a trigger-or-hook on project creation. Chosen approach: call `_create_default_subproject(project_id, db)` helper immediately after the project INSERT in `main.py`.

### "Active" is Derived, Not Stored
**Decision**: `is_active` is not a column. The `/subprojects/active` endpoint and the `is_active` flag in list responses are computed via a subquery: `EXISTS(SELECT 1 FROM tasks WHERE subproject_id = sp.id AND status NOT IN ('done', 'not_needed'))`.

**Rationale**: Keeps the schema simple and avoids stale flags. Sub-project activity changes every time a task status changes — a stored flag would require triggers or update cascades.

**Trade-offs**: Adds a correlated subquery cost to list responses. Acceptable at current scale; can be cached later.

### Sidebar Uses URL Search Param for Active Filter
**Decision**: Selected sub-project is communicated via `?subproject=<id>` URL query parameter. The Sidebar renders `<Link href="/projects/ID?subproject=SP_ID">` entries; the project page reads `useSearchParams().get('subproject')`.

**Rationale**: URL-based state is bookmarkable, shareable, and survives page refresh without client-side state management complexity. Keeps the Sidebar and project page decoupled — neither needs shared context.

**Trade-offs**: Sidebar must detect active project from `pathname` (`/projects/[id]`), which couples it lightly to URL structure.

### Deletion Sets Tasks to NULL (Not Moved to Default)
**Decision**: `ON DELETE SET NULL` on `tasks.subproject_id`. Tasks in a deleted sub-project become "Unassigned" (shown in the Unassigned filter entry in sidebar), not auto-moved to Default.

**Rationale**: Moving tasks to Default on deletion would silently alter task data. Unassigned is a clearly distinct state that users can correct.

## Data Models and Interfaces

### Database Schema (additions to `backend/init.sql`)

```sql
CREATE TABLE subprojects (
    id                 SERIAL PRIMARY KEY,
    project_id         INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name               VARCHAR(255) NOT NULL,
    subproject_number  INTEGER NOT NULL,
    is_default         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (project_id, subproject_number)
);

ALTER TABLE tasks ADD COLUMN subproject_id INTEGER REFERENCES subprojects(id) ON DELETE SET NULL;
```

### SQLAlchemy Model (`backend/models.py`)

```python
class Subproject(Base):
    __tablename__ = "subprojects"
    id               = Column(Integer, primary_key=True)
    project_id       = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name             = Column(String(255), nullable=False)
    subproject_number = Column(Integer, nullable=False)
    is_default       = Column(Boolean, nullable=False, default=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    # Relationships
    project          = relationship("Project", back_populates="subprojects")
    tasks            = relationship("Task", back_populates="subproject")

# Task model addition:
# subproject_id = Column(Integer, ForeignKey("subprojects.id", ondelete="SET NULL"), nullable=True)
# subproject = relationship("Subproject", back_populates="tasks")
```

### Pydantic Schemas (`backend/schemas.py`)

```python
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
    is_active: bool   # computed field, not a DB column
    created_at: datetime
    class Config:
        from_attributes = True

# Updated TaskCreate / TaskUpdate:
# subproject_id: Optional[int] = None
```

### Frontend API Types (`frontend/lib/api.ts` additions)

```typescript
interface Subproject {
  id: number;
  project_id: number;
  name: string;
  subproject_number: number;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
}

// Updated Task interface:
// subproject_id?: number | null;
// subproject?: Subproject | null;
```

## Component Responsibilities

| Component / Module | Responsibility |
|---|---|
| `backend/init.sql` | Schema source of truth: `subprojects` table, `tasks.subproject_id` FK |
| `backend/models.py` | `Subproject` ORM model; add `subproject_id` FK + relationship to `Task` |
| `backend/schemas.py` | `SubprojectCreate`, `SubprojectUpdate`, `SubprojectResponse`; update `TaskCreate`, `TaskUpdate`, `Task`, `TaskSummary` |
| `backend/main.py` | All subproject API endpoints; hook into project creation to auto-create Default; add `subproject_id` filter to task list/actionable queries |
| `mcp-server/stdio_server.py` | New MCP tools: `list_active_subprojects`, `list_actionable_tasks_in_subproject`, subproject CRUD; update `list_tasks`, `list_actionable_tasks`, `create_task`, `update_task` |
| `frontend/lib/api.ts` | `getSubprojects()`, `createSubproject()`, `updateSubproject()`, `deleteSubproject()`; update `getTasks()` and `createTask()` types |
| `frontend/components/Sidebar.tsx` | Detect active project from pathname; load + render sub-projects as filter links; show active/inactive styling; include "All" and "Unassigned" entries |
| `frontend/app/projects/[id]/page.tsx` | Read `?subproject=` search param; pass to `getTasks()`; add subproject dropdown to new-task form |
| `frontend/app/tasks/[id]/page.tsx` | Add subproject dropdown to task edit form; display subproject badge |

## Constraints

- No new external dependencies (frontend or backend)
- `backend/init.sql` is the schema source of truth — no migration files; live environments apply `ALTER TABLE` manually
- Sub-projects must belong to the same project as their tasks (validated at API layer)
- Default sub-project cannot be deleted (enforced at API layer, not DB constraint)
- The `is_active` field must never be persisted as a column — always computed at query time
- MCP tool parameter additions must be backward compatible (all new params are optional with `None` default)

## Open Questions

- Should the `Unassigned` entry in the sidebar only appear when at least one task in the project has `subproject_id = NULL`? (Implementer discretion — showing it always is simpler and avoids an extra query)
- Should sub-project name uniqueness be enforced per project? (Not in current design — two sub-projects can share a name, differentiated by their number. Implementer may add a unique constraint if desired.)
