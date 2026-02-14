# Task Tracker Enhancements - AI Agent Features

## Project Overview

This repository contains the Task Tracker application with enhanced features for AI agent task management, including hierarchical subtasks and task dependencies.

## Authentication

The task tracker backend requires authentication for all API endpoints. Two authentication methods are supported:

1. **JWT Bearer Token** - For web UI (login via `/api/auth/login`)
2. **API Key** - For MCP server and programmatic access (sent via `X-API-Key` header)

### Admin Credentials (Fresh Deployments)
- **Email:** `admin@example.com`
- **Password:** `admin123` (default password - **CHANGE ON FIRST LOGIN IN PRODUCTION**)
- **User ID:** `1`
- **Role:** `admin`

**Note:** Fresh deployments from `init.sql` will seed this admin account with the default password. For production use, change this password immediately after first login.

### MCP Server Configuration

The MCP server supports **separate configurations for production and development environments**:

**Configuration Files:**
- `.mcp.prod.json` - Production MCP config (gitignored, contains production API key)
- `.mcp.dev.json` - Development MCP config (gitignored, contains development API key)
- `.mcp.prod.json.template` - Production template (committed)
- `.mcp.dev.json.template` - Development template (committed)

**Environment Variables:**
- `TASK_TRACKER_API_URL`: Backend URL (production: http://localhost:6001, development: http://localhost:6002)
- `TASK_TRACKER_API_KEY`: API key for authentication (format: `ttk_live_<random>`)
- `TASK_TRACKER_USER_ID`: User ID associated with the API key

### Creating New API Keys

**For Production Environment (port 6001):**

1. Login to get an access token:
   ```bash
   curl -X POST http://localhost:6001/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"your-prod-password"}'
   ```

2. Use the access token to create an API key:
   ```bash
   curl -X POST http://localhost:6001/api/auth/api-keys \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <access_token>" \
     -d '{"name":"MCP Production Key","expires_days":365}'
   ```

3. Update `.mcp.prod.json` with the new key and restart Claude Code.

**For Development Environment (port 6002):**

1. Login to get an access token:
   ```bash
   curl -X POST http://localhost:6002/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"admin123"}'
   ```

2. Use the access token to create an API key:
   ```bash
   curl -X POST http://localhost:6002/api/auth/api-keys \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <access_token>" \
     -d '{"name":"MCP Development Key","expires_days":365}'
   ```

3. Update `.mcp.dev.json` with the new key and restart Claude Code.

**Note:** After updating MCP configuration files, you must restart Claude Code for changes to take effect.

**Using Both Environments Simultaneously:**

You can configure Claude Code to connect to both production and development environments at the same time. When both are configured, MCP tools will have distinct prefixes:
- Production tools: `mcp__task-tracker-prod__*`
- Development tools: `mcp__task-tracker-dev__*`

This allows you to work with both environments without conflicts.

### Setting Up MCP Configuration Files

**IMPORTANT:** MCP servers require absolute paths for both the Python interpreter and the server script. Relative paths will fail because MCP servers run in their own process with an unpredictable working directory.

**Step 1: Find Your Python Path**

```bash
which python3
# Example output: /Users/yourname/.pyenv/shims/python3
```

**Step 2: Install MCP Server to Standard Location**

```bash
mkdir -p ~/.mcp-servers
cp -r mcp-server/* ~/.mcp-servers/
```

This copies the MCP server files to `~/.mcp-servers/` which is a standard location for MCP servers.

**Step 3: Create Configuration from Template**

For production:
```bash
cp .mcp.prod.json.template .mcp.prod.json
```

Edit `.mcp.prod.json` and replace:
- `/ABSOLUTE/PATH/TO/python3` → your `which python3` output (e.g., `/Users/yourname/.pyenv/shims/python3`)
- `/ABSOLUTE/PATH/TO/.mcp-servers/stdio_server.py` → `/Users/yourname/.mcp-servers/stdio_server.py` (replace `yourname` with your username)
- `GET_API_KEY_FROM_SETTINGS` → your actual API key from http://localhost:6001/settings
- `YOUR_USER_ID` → your user ID from the settings page

For development:
```bash
cp .mcp.dev.json.template .mcp.dev.json
```

Edit `.mcp.dev.json` with the same replacements (but use port 6002 for the settings page).

**Step 4: Get Your User ID**

Visit the settings page (http://localhost:6001/settings for production or http://localhost:6002/settings for development) after logging in. Your User ID will be displayed on the page.

**Step 5: Restart Claude Code**

After updating MCP configuration files, you must restart Claude Code for changes to take effect.

**Example of Final Configuration:**

```json
{
  "mcpServers": {
    "task-tracker-prod": {
      "command": "/Users/yourname/.pyenv/shims/python3",
      "args": ["/Users/yourname/.mcp-servers/stdio_server.py"],
      "env": {
        "TASK_TRACKER_API_URL": "http://localhost:6001",
        "TASK_TRACKER_API_KEY": "ttk_live_abc123def456...",
        "TASK_TRACKER_USER_ID": "1"
      }
    }
  }
}
```

**Why Absolute Paths Are Required:**

- MCP servers run in their own process, not from your project directory
- Relative paths like `./mcp-server/stdio_server.py` won't work because the working directory is unpredictable
- The Python command needs the full path to ensure the correct interpreter is used
- Using `~/.mcp-servers/` as a standard location keeps your configuration portable across projects

## Task Workflow

### Before Working on Tasks

**IMPORTANT:** Always take ownership of a task before starting work on it:

```bash
# Take ownership of a task (assigns to authenticated user)
curl -X POST http://localhost:6001/api/tasks/{task_id}/take-ownership \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

Or use the MCP tool:
```
mcp__task-tracker__take_ownership(task_id, force=False)
```

**Note:** Ownership is always assigned to the authenticated user. This prevents privilege escalation.

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
- Project management tools:
  - `list_assignable_users(project_id)` - List users who can be assigned tasks in a project
  - `transfer_project_team(project_id, team_id)` - Transfer project between teams or make personal

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

**Schema Management:** The complete database schema is defined in `backend/init.sql`, which serves as the single source of truth for fresh deployments. All schema enhancements (full-text search, time tracking, rich context, Kanban settings, and authentication) have been consolidated into this file. There are no migration files—the application is designed for fresh deployments via Docker Compose initialization.

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
  - Body: `{"title": "...", "due_date": "2026-02-25T14:00:00Z", "estimated_hours": 10.0}`
  - Note: `author_id` is automatically set to the authenticated user
- `PUT /api/tasks/{id}` - Update task with actual hours
  - Body: `{"actual_hours": 8.5}`

### Assignable Users
- `GET /api/projects/{id}/assignable-users` - List users who can be assigned tasks
  - For team projects: Returns all team members
  - For personal projects: Returns all project members
  - Requires: Viewer access to project

### Project Team Transfer
- `PUT /api/projects/{id}/transfer` - Transfer project to different team or make personal
  - Body: `{"team_id": 1}` (or `null` for personal)
  - Requires: Owner role in project, admin role in target team
  - Validates: All task owners must be in target team

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

## Agent Teams for Coding

### When to Delegate to Specialized Agents

**IMPORTANT:** For any non-trivial coding task, delegate to specialized agents using the Task tool. This ensures focused expertise, better code quality, and maintains conversation context efficiency.

### Backend Development (Python/FastAPI)

**Use `backend-code-writer` agent for:**
- Implementing new API endpoints
- Adding business logic and validation
- Database operations and ORM queries
- Backend bug fixes and refactoring
- Writing backend tests

**Example:**
```
Task(
  subagent_type="backend-code-writer",
  description="Add dependency endpoints",
  prompt="Implement POST /api/tasks/{id}/dependencies endpoint with circular dependency validation"
)
```

### Frontend Development (React/Next.js)

**Use `frontend-code-writer` agent for:**
- Creating or modifying React components
- Implementing UI features and interactions
- API integration from frontend
- State management
- Frontend bug fixes
- Using Playwright for flow testing

**Example:**
```
Task(
  subagent_type="frontend-code-writer",
  description="Update task detail page",
  prompt="Add dependency visualization to the task detail page, showing blocking and blocked tasks"
)
```

### End-to-End Testing

**Use `e2e-flow-tester` agent for:**
- Verifying complete user journeys after implementation
- Testing multi-step workflows (create task → assign → complete)
- Integration testing across frontend and backend
- Testing after frontend changes are deployed

**Example:**
```
Task(
  subagent_type="e2e-flow-tester",
  description="Test dependency workflow",
  prompt="Verify the complete flow: create two tasks, add dependency relationship, attempt to complete blocked task (should fail), complete blocking task, then complete blocked task (should succeed)"
)
```

### API Testing

**Use `curl-api-tester` agent for:**
- Testing API endpoints after backend changes
- Verifying request/response formats
- Testing edge cases and validation
- Quick endpoint verification without writing code

**Example:**
```
Task(
  subagent_type="curl-api-tester",
  description="Test dependency endpoints",
  prompt="Test the new dependency endpoints: create dependency, verify it appears in GET /api/tasks/{id}/dependencies, delete it"
)
```

### Debugging and Root Cause Analysis

**Use `root-cause-analyzer` agent for:**
- Investigating failing tests
- Diagnosing API errors or 500s
- Analyzing performance issues
- Understanding why features aren't working as expected

**Example:**
```
Task(
  subagent_type="root-cause-analyzer",
  description="Debug circular dependency check",
  prompt="The circular dependency validation is allowing some circular paths. Investigate why the BFS algorithm isn't catching all cases."
)
```

### Code Review

**Use `superpowers:code-reviewer` agent for:**
- Reviewing completed implementations
- Validating against requirements
- Checking for security vulnerabilities
- Ensuring code quality and best practices

**Example:**
```
Skill(skill="superpowers:requesting-code-review")
```

### Best Practices

1. **Delegate Early:** Use agents for any implementation task beyond 5-10 lines of code
2. **Be Specific:** Provide clear context, requirements, and acceptance criteria
3. **Sequential Tasks:** Use agents in sequence (backend → testing → frontend → e2e)
4. **Parallel Tasks:** Launch multiple agents concurrently for independent work
5. **Context Preservation:** Agents keep the main conversation clean and focused
6. **Verification:** Always test with appropriate agent after making changes

### Agent Workflow Example

For a new feature like "Add task dependencies":

1. **Backend:** `backend-code-writer` implements API endpoints
2. **API Test:** `curl-api-tester` verifies endpoints work
3. **Frontend:** `frontend-code-writer` adds UI for dependencies
4. **E2E Test:** `e2e-flow-tester` validates complete user flow
5. **Review:** `superpowers:code-reviewer` checks implementation quality

## Development Workflow

### Environment Overview

The Task Tracker supports **separate production and development environments** that can run simultaneously:

| Environment | Frontend | Backend | Database | DB Name | Volume |
|-------------|----------|---------|----------|---------|--------|
| **Production** | 3000 | 6001 | 5432 | tasktracker | postgres_data |
| **Development** | 3001 | 6002 | 5433 | tasktracker_dev | postgres_data_dev |

### Running the Application

**Quickest Start (Development):**
```bash
# Simplest command - automatically starts development environment
docker compose up -d

# Access at: http://localhost:3001 (frontend), http://localhost:6002 (backend)
# Stop with: docker compose down
```

This uses `docker-compose.override.yml` which provides development defaults automatically. **No additional configuration needed!**

**Make Commands (Recommended):**
```bash
# Production (ports 3000/6001/5432)
make prod-start      # Start production
make prod-stop       # Stop production
make prod-logs       # View logs
make prod-restart    # Restart services
make prod-db         # Connect to database

# Development (ports 3001/6002/5433)
make dev-start       # Start development (explicit)
make dev-stop        # Stop development
make dev-logs        # View logs
make dev-restart     # Restart services
make dev-reset       # Reset database (fresh start)
make dev-db          # Connect to database

# Both Environments
make start-all       # Start both production and development
make stop-all        # Stop both environments
make status          # Show status of all environments
```

**Manual Docker Compose (Advanced):**

Three ways to run:

1. **Default Development** (uses `docker-compose.override.yml` automatically):
   ```bash
   docker compose up -d
   docker compose down
   ```

2. **Explicit Development**:
   ```bash
   docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml up -d
   docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml down
   ```

3. **Production** (requires explicit flags):
   ```bash
   docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml up -d
   docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml down
   ```

**IMPORTANT:**
- Bare `docker compose up` automatically loads `docker-compose.override.yml` (development defaults)
- The `-p` (project name) flag is **required** for explicit environments to run both simultaneously
- Without `-p`, both environments would share the same Docker Compose project and conflict

### Environment Configuration Files

```
├── docker-compose.yml              # Base configuration (shared)
├── docker-compose.override.yml     # Auto-loaded development defaults
├── docker-compose.prod.yml         # Production overrides (explicit)
├── docker-compose.dev.yml          # Development overrides (explicit)
├── .env.production                 # Production config (no secrets)
├── .env.development               # Development config (safe defaults)
├── .env.local                     # Local secrets (gitignored)
├── .mcp.prod.json                 # Production MCP (gitignored)
├── .mcp.dev.json                  # Development MCP (gitignored)
├── .mcp.prod.json.template        # Production MCP template
└── .mcp.dev.json.template         # Development MCP template
```

**File Hierarchy:**
- `docker-compose.yml` - Base services (no ports, no environment-specific config)
- `docker-compose.override.yml` - **Auto-loaded** for `docker compose up` (development defaults)
- `docker-compose.{prod,dev}.yml` - Explicit environment overrides (require `-f` flag)

**Production Setup:**
- Edit `.env.local` (gitignored) with secrets:
  ```bash
  ADMIN_PASSWORD=your-strong-password
  JWT_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
  ```
- Create `.mcp.prod.json` from template with production API key

**Development Setup:**
- Uses `.env.development` with safe defaults (admin123, dev JWT key)
- Create `.mcp.dev.json` from template with development API key
- No additional configuration needed

### Database Access

**Production Database:**
```bash
# Using Make
make prod-db

# Or manually
docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml exec postgres psql -U taskuser -d tasktracker

# Or from host
psql postgresql://taskuser:taskpass@localhost:5432/tasktracker
```

**Development Database:**
```bash
# Using Make
make dev-db

# Or manually
docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml exec postgres psql -U taskuser -d tasktracker_dev

# Or from host
psql postgresql://taskuser:taskpass@localhost:5433/tasktracker_dev
```

**Common Queries:**
```sql
-- View tasks
SELECT id, title, status, parent_task_id, project_id FROM tasks;

-- View dependencies
SELECT blocking_task_id, blocked_task_id FROM task_dependencies;

-- View database size
SELECT pg_database_size(current_database());
```

**Fresh Database Setup:**
- Docker Compose automatically initializes the database using `backend/init.sql` on first run
- To reset production: `make prod-reset` (⚠️ WARNING: destroys all data)
- To reset development: `make dev-reset` (safe, designed for frequent resets)

### Testing

**Production Environment:**
```bash
# Restart after code changes
make prod-restart

# Test endpoints
curl http://localhost:6001/health
curl http://localhost:6001/api/tasks
curl http://localhost:6001/api/tasks/actionable

# View logs
make prod-logs
```

**Development Environment:**
```bash
# Restart after code changes
make dev-restart

# Test endpoints
curl http://localhost:6002/health
curl http://localhost:6002/api/tasks
curl http://localhost:6002/api/tasks/actionable

# View logs
make dev-logs

# Reset database for clean state
make dev-reset
```

### Multi-Environment Benefits

1. **Complete Isolation** - Dev and prod never interfere with each other
2. **Data Safety** - Development experiments never affect production data
3. **Parallel Operation** - Both environments can run simultaneously
4. **Easy Reset** - `make dev-reset` wipes development without touching production
5. **Independent APIs** - Separate API keys and authentication for each environment
6. **Database Isolation** - Separate databases prevent data corruption
7. **Port Separation** - No conflicts when running both environments

### MCP Configuration Per Environment

**Production MCP (`.mcp.prod.json`):**
```json
{
  "mcpServers": {
    "task-tracker-prod": {
      "command": "python3",
      "args": ["./mcp-server/stdio_server.py"],
      "env": {
        "TASK_TRACKER_API_URL": "http://localhost:6001",
        "TASK_TRACKER_API_KEY": "ttk_live_production_key",
        "TASK_TRACKER_USER_ID": "1"
      }
    }
  }
}
```

**Development MCP (`.mcp.dev.json`):**
```json
{
  "mcpServers": {
    "task-tracker-dev": {
      "command": "python3",
      "args": ["./mcp-server/stdio_server.py"],
      "env": {
        "TASK_TRACKER_API_URL": "http://localhost:6002",
        "TASK_TRACKER_API_KEY": "ttk_live_development_key",
        "TASK_TRACKER_USER_ID": "1"
      }
    }
  }
}
```

**Note:** After updating MCP configuration, restart Claude Code for changes to take effect.

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
