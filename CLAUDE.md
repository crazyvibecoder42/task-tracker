# Task Tracker Enhancements - AI Agent Features

## Project Overview

This repository contains the Task Tracker application with enhanced features for AI agent task management, including hierarchical subtasks and task dependencies.

## Persona Configuration

**Author/Owner ID:** `aman`

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

3. **Update task status** when complete:
   - Tasks start as `pending`
   - Mark as `completed` when done
   - **Note:** Only two statuses are supported: `pending` and `completed`

4. **Respect dependencies:**
   - Tasks with `is_blocked: true` cannot be completed
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
- 8 MCP tools for AI agent workflows
- Real-time task management
- Dependency-aware task queries

## Database Schema

### Tasks Table
- `parent_task_id`: References parent task for subtasks (nullable)
- `is_blocked`: Computed field based on blocking dependencies

### Task Dependencies Table
- `blocking_task_id`: Task that blocks another
- `blocked_task_id`: Task being blocked
- Unique constraint on (blocking_task_id, blocked_task_id)

## API Endpoints

### Task Dependencies
- `GET /api/tasks/{id}/dependencies` - Get task with full dependency info
- `POST /api/tasks/{id}/dependencies` - Add blocking relationship
- `DELETE /api/tasks/{id}/dependencies/{blocking_id}` - Remove dependency
- `GET /api/tasks/actionable` - Query unblocked pending tasks

### Subtasks
- `GET /api/tasks/{id}/subtasks` - List subtasks
- `GET /api/tasks/{id}/progress` - Get completion percentage
- `POST /api/tasks` with `parent_task_id` - Create subtask

## Business Rules

### Task Completion
- Cannot complete task with pending subtasks
- Cannot complete blocked task (has pending blocking dependencies)
- Parent task requires all subtasks complete

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

## Worktree Configuration

Prefer using `.worktrees/` directory for isolated development branches.

## Memory Location

Auto memory files are stored in: `~/.claude/projects/-Users-delusionalmakubex-Documents-projects-experimental-task-tracker/memory/`
