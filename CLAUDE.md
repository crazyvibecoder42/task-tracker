# Task Tracker Enhancements - AI Agent Features

## Project Overview

This repository contains the Task Tracker application with enhanced features for AI agent task management, including hierarchical subtasks and task dependencies.

## Persona Configuration

**Author/Owner ID:** `aman`

**Project Assignment:** Task Tracker Enhancements - AI Agent Features (Project ID: 4)

When interacting with the task-tracker backend API (http://localhost:6001), always use `author_id: 1` (aman) for:
- Creating tasks (`POST /api/tasks`)
- Creating comments (`POST /api/tasks/{id}/comments`)
- Taking ownership of tasks (`POST /api/tasks/{id}/take-ownership`)

## Task Workflow

### Before Working on Tasks

**IMPORTANT:** Always take ownership of a task before starting work on it:

```bash
# Take ownership of a task
curl -X POST http://localhost:6001/api/tasks/{task_id}/take-ownership \
  -H "Content-Type: application/json" \
  -d '{"author_id": 1}'
```

Or use the MCP tool:
```
mcp__task-tracker__take_ownership(task_id, author_id=1)
```

### Task Management Guidelines

1. **Check actionable tasks** before claiming:
   ```bash
   curl http://localhost:6001/api/tasks/actionable
   ```
   Or use: `mcp__task-tracker__get_actionable_tasks()`

2. **Take ownership** when you find a task to work on

3. **Update task status** following the workflow:
   - Tasks default to `todo` status when created
   - **6-Status Workflow:** `backlog` → `todo` → `in_progress` → `review` → `done`
   - Tasks can be marked as `blocked` (temporary state) when dependencies are incomplete
   - Valid status values: `backlog`, `todo`, `in_progress`, `blocked`, `review`, `done`

4. **Status Transition Best Practices:**
   - Move task to `in_progress` when you start working on it
   - Move to `review` when ready for review
   - Move to `done` when fully completed (requires all subtasks to be done)
   - Mark as `blocked` when waiting on dependencies

5. **Respect dependencies:**
   - Tasks with `is_blocked: true` cannot be marked as done
   - Complete blocking tasks first
   - Use actionable tasks endpoint to find unblocked work

## Features Implemented

### Subtasks
- Hierarchical task breakdown with `parent_task_id`
- Progress tracking based on subtask completion
- Circular subtask detection (BFS algorithm)
- Parent completion validation (requires all subtasks complete)

### Dependencies
- Blocking task relationships (task A blocks task B)
- Circular dependency detection (BFS algorithm)
- Actionable tasks query (excludes blocked tasks)
- Dynamic `is_blocked` calculation
- Parent-subtask deadlock prevention

### MCP Server Integration
- 12+ MCP tools for AI agent workflows
- Real-time task management
- Dependency-aware task queries
- Event timeline tracking with `get_task_events` and `get_project_events`
- Time tracking tools:
  - `list_overdue_tasks(project_id, limit)` - Query overdue tasks
  - `list_upcoming_tasks(project_id, days, limit)` - Query upcoming tasks
- Task creation/update with time fields:
  - `create_task(..., due_date="2026-02-25T14:00:00Z", estimated_hours=10.0)`
  - `update_task(task_id, actual_hours=8.5)`

### Event Tracking
- Comprehensive audit trail for all task operations
- Timeline feature showing task history with timestamps
- **Event Types:**
  - `task_created` - Task was created
  - `status_change` - Task status was updated
  - `field_update` - Other task fields were modified (title, description, priority, tag, etc.)
  - `ownership_change` - Task ownership was assigned or reassigned
  - `dependency_added` - Blocking dependency was added
  - `dependency_removed` - Blocking dependency was removed
  - `comment_added` - Comment was added to task
- Event metadata includes actor information, old/new values, and contextual data
- Events are queryable with filtering by event type and pagination support

### Time Tracking
- Three new fields for time management: `due_date`, `estimated_hours`, `actual_hours`
- Overdue detection and visual indicators (red badges)
- Progress calculation based on actual vs estimated hours
- Dashboard widget showing overdue and upcoming tasks
- Date-based filtering and sorting
- **Overdue Definition:** Tasks with `due_date` in the past and status not in (`done`, `backlog`)
- **Progress Calculation:** `(actual_hours / estimated_hours) * 100`
  - Green progress bar when under budget (actual < estimated)
  - Red progress bar when over budget (actual > estimated)

## Database Schema

### Tasks Table
- `parent_task_id`: References parent task for subtasks (nullable)
- `is_blocked`: Computed field based on blocking dependencies
- `status`: ENUM type with values: `backlog`, `todo`, `in_progress`, `blocked`, `review`, `done`

### Task Dependencies Table
- `blocking_task_id`: Task that blocks another
- `blocked_task_id`: Task being blocked
- Unique constraint on (blocking_task_id, blocked_task_id)

### Task Events Table
- `task_id`: References task that the event belongs to
- `event_type`: Type of event (task_created, status_change, field_update, etc.)
- `actor_id`: User who triggered the event (nullable for system events)
- `field_name`: Name of field that changed (for field_update and status_change events)
- `old_value`: Previous value (nullable)
- `new_value`: New value (nullable)
- `event_metadata`: JSONB field for additional context
- `created_at`: Timestamp of the event

## API Endpoints

### Task Dependencies
- `GET /api/tasks/{id}/dependencies` - Get task with full dependency info
- `POST /api/tasks/{id}/dependencies` - Add blocking relationship
- `DELETE /api/tasks/{id}/dependencies/{blocking_id}` - Remove dependency
- `GET /api/tasks/actionable` - Query unblocked tasks (excludes backlog, blocked, and done)

### Subtasks
- `GET /api/tasks/{id}/subtasks` - List subtasks
- `GET /api/tasks/{id}/progress` - Get completion percentage
- `POST /api/tasks` with `parent_task_id` - Create subtask

### Task Events
- `GET /api/tasks/{id}/events` - Get event history for a specific task
  - Query params: `event_type` (filter), `limit` (max 500), `offset` (pagination)
- `GET /api/projects/{id}/events` - Get event history for all tasks in a project
  - Query params: `event_type` (filter), `limit` (max 500), `offset` (pagination)

### Time Tracking
- `GET /api/tasks/overdue` - List overdue tasks (due_date in past, status not done)
  - Query params: `project_id` (filter by project), `limit` (default: 50)
  - Example: `curl http://localhost:6001/api/tasks/overdue?project_id=4&limit=10`
- `GET /api/tasks/upcoming` - List upcoming tasks (due within N days)
  - Query params: `days` (default: 7), `project_id` (filter), `limit` (default: 50)
  - Example: `curl http://localhost:6001/api/tasks/upcoming?days=14&limit=10`
- `GET /api/tasks` - Enhanced with date filtering
  - Query params: `due_after` (ISO 8601 datetime), `due_before` (ISO 8601 datetime), `overdue` (boolean)
  - Example: `curl "http://localhost:6001/api/tasks?due_after=2026-02-01T00:00:00Z&due_before=2026-03-01T23:59:59Z"`
- `POST /api/tasks` - Create task with time tracking fields
  - Body: `{"title": "...", "due_date": "2026-02-25T14:00:00Z", "estimated_hours": 10.0, "author_id": 1}`
- `PUT /api/tasks/{id}` - Update task with actual hours
  - Body: `{"actual_hours": 8.5}`

## Business Rules

### Task Completion
- Cannot mark task as `done` if it has subtasks that are not `done`
- Cannot mark task as `done` if it is blocked by incomplete dependencies
- Parent task requires all subtasks to be `done` before it can be marked `done`
- Tasks in `backlog`, `blocked`, or `done` status are excluded from actionable tasks query

### Dependency Creation
- No circular dependencies allowed
- Parent cannot block its own subtask (prevents deadlock)
- Tasks must be in same project
- No self-blocking allowed

### Validation Order
1. Task existence
2. Same project constraint
3. Circular dependency check
4. Parent-subtask deadlock check
5. Status and completion validations

### Time Tracking
- All three time fields (`due_date`, `estimated_hours`, `actual_hours`) are optional
- Overdue tasks are defined as: `due_date < now() AND status NOT IN ('done', 'backlog')`
- Upcoming tasks are: `due_date BETWEEN now() AND now() + N days AND status NOT IN ('done', 'backlog')`
- Progress percentage: `(actual_hours / estimated_hours) * 100` when both fields are present
- Over-budget indicator: actual_hours > estimated_hours (shown in red)
- Under-budget indicator: actual_hours <= estimated_hours (shown in green)
- Tasks without due_date are excluded from overdue/upcoming queries
- Date filters expect ISO 8601 datetime format (e.g., `2026-02-01T00:00:00Z`)

## Development Workflow

### Running the Application
```bash
# Start all services
docker-compose up -d

# Check backend health
curl http://localhost:6001/health

# Check frontend
open http://localhost:3000
```

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U taskuser -d tasktracker

# View tasks
SELECT id, title, status, parent_task_id, project_id FROM tasks;

# View dependencies
SELECT blocking_task_id, blocked_task_id FROM task_dependencies;
```

### Testing
```bash
# Restart backend after code changes
docker-compose restart backend

# Test endpoints
curl http://localhost:6001/api/tasks
curl http://localhost:6001/api/tasks/actionable
```

## Documentation Policy

**IMPORTANT:** Do NOT create temporary documentation files (.md) for testing, bug reports, planning, or status tracking. These files clutter the repository and should be avoided.

**Allowed .md files:**
- `README.md` - Essential project documentation
- `CLAUDE.md` - This file (project instructions for AI)

**Do NOT create:**
- Test plans, test results, or test status files
- Bug reports or issue tracking files
- Design documents or planning files
- Status update files or progress tracking

**Instead:**
- Use inline comments in code or test files
- Track issues in the task tracker system itself
- Store plans in auto memory (`~/.claude/projects/.../memory/`)
- Use git commit messages for change history

## Worktree Configuration

Prefer using `.worktrees/` directory for isolated development branches.

## Memory Location

Auto memory files are stored in: `~/.claude/projects/-Users-delusionalmakubex-Documents-projects-experimental-task-tracker/memory/`
