# Task Ownership Feature Design

**Date:** 2026-02-04
**Status:** Approved

## Overview

Add task ownership functionality to the task tracker system. Tasks will have a separate `owner_id` field (distinct from `author_id`) to track who is responsible for completing the task.

## Key Design Decisions

1. **Separate Owner from Author**: `author_id` tracks who created the task, `owner_id` tracks who's responsible for it
2. **Owner as Foreign Key**: `owner_id` references the `authors` table for data integrity
3. **Nullable Owner**: Tasks can be unassigned (owner_id = NULL)
4. **Force Parameter**: Taking ownership has a safety mechanism via optional `force` parameter
5. **Release Ownership**: Users can set owner_id to NULL to unassign tasks
6. **Owner Filtering**: Tasks can be filtered by owner_id in list queries

## Database Schema Changes

### Tasks Table Migration

```sql
ALTER TABLE tasks ADD COLUMN owner_id INTEGER REFERENCES authors(id) ON DELETE SET NULL;
CREATE INDEX idx_tasks_owner_id ON tasks(owner_id);
```

### SQLAlchemy Model Updates

**Task Model (models.py):**
- Add `owner_id` column with foreign key to authors
- Add `owner` relationship

**Author Model (models.py):**
- Add `owned_tasks` relationship for reverse lookup

## API Changes

### Pydantic Schemas (schemas.py)

- Add `owner_id: Optional[int]` and `owner: Optional[Author]` to task schemas
- Include owner_id in TaskCreate, TaskUpdate, Task, and TaskSummary

### Backend Endpoints (main.py)

**Modified Endpoints:**
- `POST /api/tasks` - Accept optional `owner_id` in request body
- `PUT /api/tasks/{task_id}` - Accept optional `owner_id` in request body (can be None to release)
- `GET /api/tasks` - Accept optional `owner_id` query parameter for filtering

**New Endpoint:**
- `POST /api/tasks/{task_id}/take-ownership`
  - Request: `{"author_id": int, "force": bool (default: False)}`
  - Logic:
    - If no current owner → assign owner
    - If current owner exists and force=False → return error
    - If current owner exists and force=True → reassign owner
  - Response: Updated task object or error message

## MCP Server Changes

### New Tool: `take_ownership`

```python
Tool(
    name="take_ownership",
    description="Take ownership of a task. Optionally force reassignment if already owned.",
    inputSchema={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "Task ID"},
            "author_id": {"type": "integer", "description": "Author ID to assign as owner"},
            "force": {"type": "boolean", "description": "Force reassignment if already owned (default: false)"}
        },
        "required": ["task_id", "author_id"]
    }
)
```

### Updated Tools

- `create_task`: Add optional `owner_id` parameter
- `update_task`: Add optional `owner_id` parameter (can be null)
- `list_tasks`: Add optional `owner_id` filter parameter

### Implementation Files

Both `server.py` and `stdio_server.py` require identical updates:
- Tool definitions in `list_tools()`
- Handler implementation in `call_tool()`

## Implementation Order

1. **Database Layer**
   - Update `init.sql` with ALTER TABLE statement
   - Update `models.py` with owner_id field and relationships
   - Update `schemas.py` with owner_id in all relevant schemas

2. **Backend API**
   - Update existing endpoints to handle owner_id
   - Add new take-ownership endpoint

3. **MCP Server**
   - Update both server files with new tool and updated schemas
   - Implement handlers

## Testing Checklist

- [ ] Database migration executes successfully
- [ ] Foreign key constraint works (NULL allowed)
- [ ] Index created on owner_id
- [ ] Take ownership with no existing owner succeeds
- [ ] Take ownership with existing owner and force=False fails with proper error
- [ ] Take ownership with existing owner and force=True succeeds
- [ ] Release ownership via update_task with owner_id=None works
- [ ] Filter tasks by owner_id returns correct results
- [ ] Filter tasks by owner_id=None returns unassigned tasks
- [ ] MCP tool integration works end-to-end
