# Task Tracker

A full-stack task management application designed for AI agent workflows with advanced features like hierarchical subtasks, task dependencies, time tracking, and comprehensive MCP (Model Context Protocol) integration.

## Features

### Core Task Management
- **Hierarchical Subtasks** - Break down tasks into smaller, manageable subtasks with automatic progress tracking
- **Task Dependencies** - Define blocking relationships between tasks with circular dependency detection (BFS algorithm)
- **Time Tracking** - Track estimated hours, actual hours, and due dates with overdue detection
- **6-Status Workflow** - Tasks progress through `backlog` → `todo` → `in_progress` → `blocked` → `review` → `done`
- **Rich Context** - Full-text search across tasks, projects, and comments
- **Event Timeline** - Comprehensive audit trail for all task operations with detailed metadata

### Team Collaboration
- **Team Management** - Create teams with admin/member roles for better organization
- **Project Organization** - Team projects or personal projects with flexible ownership
- **Task Assignment** - Assign tasks to team members with ownership tracking
- **Comments & Discussion** - Threaded comments on tasks with author attribution
- **Assignable Users** - Query users who can be assigned tasks in a project

### AI Agent Integration
- **MCP Server** - 40+ tools for programmatic task management via Claude Code or other MCP clients
- **Bulk Operations** - Create, update, or delete multiple tasks in a single transaction
- **Actionable Tasks Query** - Find unblocked tasks ready to work on (excludes backlog, blocked, done)
- **Dependency-Aware Queries** - Automatically exclude blocked tasks from actionable queries
- **API Key Authentication** - Secure authentication for AI agents separate from user sessions
- **Generate MCP Config** - Programmatically generate MCP configuration with API keys

## Tech Stack

- **Database**: PostgreSQL 16 (Docker)
- **Backend**: Python FastAPI
- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **MCP Server**: Python-based stdio MCP server

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for MCP server)
- Make (optional, for convenience commands)

### Quickest Start (Development)

For the fastest local development setup:

```bash
# Simple command - automatically starts development environment
docker compose up -d

# Access the application
# - Frontend: http://localhost:3001
# - Backend API: http://localhost:6002
# - API Docs: http://localhost:6002/docs

# Stop
docker compose down
```

This uses `docker-compose.override.yml` which provides development defaults automatically. No additional configuration needed!

**Default Development Credentials:**
- Email: `admin@example.com`
- Password: `admin123`
- User ID: `1`
- Role: `admin`

**⚠️ Note:** Fresh deployments from `init.sql` will seed this admin account with the default password. For production use, change this password immediately after first login.

### Environment Overview

The Task Tracker supports **separate production and development environments** that can run simultaneously:

| Environment | Frontend | Backend | Database | DB Name | Volume |
|-------------|----------|---------|----------|---------|--------|
| **Production** | 3000 | 6001 | 5432 | tasktracker | postgres_data |
| **Development** | 3001 | 6002 | 5433 | tasktracker_dev | postgres_data_dev |
| **Default (`docker compose up`)** | 3001 | 6002 | 5433 | tasktracker_dev | postgres_data_dev_default |

**Note:** Running bare `docker compose up` automatically loads `docker-compose.override.yml` and starts the development environment. This is the standard Docker Compose pattern for local development.

### Running Production Environment

```bash
# Start production (ports 3000/6001/5432)
make prod-start

# Access the application
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:6001
# - API Docs: http://localhost:6001/docs

# Stop production
make prod-stop

# View logs
make prod-logs
```

### Running Development Environment

```bash
# Start development (ports 3001/6002/5433)
make dev-start

# Access the application
# - Frontend: http://localhost:3001
# - Backend API: http://localhost:6002
# - API Docs: http://localhost:6002/docs

# Stop development
make dev-stop

# Reset development database (fresh start)
make dev-reset
```

### Running Both Environments Simultaneously

```bash
# Start both production and development
make start-all

# Check status of both environments
make status

# Stop both environments
make stop-all
```

### Available Make Commands

Run `make help` to see all available commands:

- **Production**: `prod-start`, `prod-stop`, `prod-logs`, `prod-restart`, `prod-reset`, `prod-db`
- **Development**: `dev-start`, `dev-stop`, `dev-logs`, `dev-restart`, `dev-reset`, `dev-db`
- **Combined**: `start-all`, `stop-all`, `status`, `clean`

### Manual Docker Compose Commands

**Three Ways to Run:**

1. **Simplest - Default Development** (uses `docker-compose.override.yml` automatically):
   ```bash
   docker compose up -d           # Start development
   docker compose down            # Stop development
   ```

2. **Explicit Development** (same as `make dev-start`):
   ```bash
   docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml up -d
   docker compose -p tasktracker_dev -f docker-compose.yml -f docker-compose.dev.yml down
   ```

3. **Production** (requires explicit flags, same as `make prod-start`):
   ```bash
   docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml up -d
   docker compose -p tasktracker_prod -f docker-compose.yml -f docker-compose.prod.yml down
   ```

**Important Notes:**
- Bare `docker compose up` automatically loads `docker-compose.override.yml` (development defaults)
- The `-p` (project name) flag is required for explicit environments to avoid conflicts
- For production, always use explicit commands (option 3) or `make prod-start`

## Environment Configuration

### Development vs Production

The Task Tracker supports different security levels based on the `ENVIRONMENT` variable:

**Development Environments** (`dev`, `development`, `local`):
- Default admin password: `admin123` (if `ADMIN_PASSWORD` not set)
- Auto-generated JWT secret key (if `JWT_SECRET_KEY` not set)
- Relaxed cookie security settings (HTTP allowed)
- Designed for local development convenience

**Production-like Environments** (`production`, `staging`):
- Requires explicit `ADMIN_PASSWORD` (startup fails if not set)
- Requires explicit `JWT_SECRET_KEY` (startup fails if not set)
- Enforces secure cookie settings (HTTPS only)
- Stricter security validations

### Configuration Files

The project uses separate configuration files for each environment:

**File Structure:**
```
├── docker-compose.yml              # Base configuration (shared)
├── docker-compose.prod.yml         # Production overrides
├── docker-compose.dev.yml          # Development overrides
├── .env.production                 # Production config (committed, no secrets)
├── .env.development               # Development config (committed, safe defaults)
├── .env.local                     # Local secrets (gitignored)
├── .mcp.prod.json                 # Production MCP config (gitignored)
├── .mcp.dev.json                  # Development MCP config (gitignored)
├── .mcp.prod.json.template        # Production MCP template (committed)
└── .mcp.dev.json.template         # Development MCP template (committed)
```

**For Production Environment:**
1. Edit `.env.production` (committed as template, no secrets)
2. Create `.env.local` (gitignored) with secrets:
   ```bash
   ADMIN_PASSWORD=your-strong-password-here
   JWT_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
   ```
3. **MUST** set a strong `ADMIN_PASSWORD` (minimum 8 characters, cannot be "admin123")
4. **MUST** set a secure `JWT_SECRET_KEY`

**For Development Environment:**
- Uses `.env.development` with safe defaults (`admin123`, dev JWT key)
- No additional configuration needed for local development
- Optionally create `.env.local` to override defaults

**For MCP Server Configuration:**
- Copy `.mcp.prod.json.template` to `.mcp.prod.json` and add production API key
- Copy `.mcp.dev.json.template` to `.mcp.dev.json` and add development API key
- See [MCP Server Setup](#mcp-server-setup) below for details

### Security Function: `is_production_like()`

The backend uses `is_production_like()` helper to determine security behavior:
- Returns `True` for `production` and `staging` environments
- Returns `False` for `dev`, `development`, `local` environments
- Used for JWT validation, cookie security, and admin password requirements

**Example:**
```python
# In backend/auth/security.py
def is_production_like() -> bool:
    env = os.environ.get("ENVIRONMENT", "development").lower()
    return env in ("production", "staging")
```

### Database Isolation

Each environment has its own isolated database:

**Production:**
- Database: `tasktracker`
- Volume: `postgres_data`
- Port: `5432`
- Access: `make prod-db` or `psql postgresql://taskuser:taskpass@localhost:5432/tasktracker`

**Development:**
- Database: `tasktracker_dev`
- Volume: `postgres_data_dev`
- Port: `5433`
- Access: `make dev-db` or `psql postgresql://taskuser:taskpass@localhost:5433/tasktracker_dev`

**Benefits:**
- Data safety: Development experiments never affect production
- Independent schemas: Can test migrations safely
- Parallel operation: Both environments can run simultaneously
- Easy reset: `make dev-reset` wipes development data without touching production

## MCP Server Setup

The MCP server allows programmatic access to the task tracker through Claude Desktop or other MCP clients. You can configure separate MCP connections for production and development environments.

### Installation and Configuration

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

**Step 3: Generate API Keys**

**For Production Environment (port 6001):**
```bash
# Login to get access token
curl -X POST http://localhost:6001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your-password"}'

# Create API key (use the access_token from login response)
curl -X POST http://localhost:6001/api/auth/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"name":"MCP Production Key","expires_days":365}'
```

**For Development Environment (port 6002):**
```bash
# Login to get access token
curl -X POST http://localhost:6002/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'

# Create API key (use the access_token from login response)
curl -X POST http://localhost:6002/api/auth/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"name":"MCP Development Key","expires_days":365}'
```

**Step 4: Create Configuration Files from Templates**

**For Production:**
```bash
cp .mcp.prod.json.template .mcp.prod.json
```

Edit `.mcp.prod.json` and replace:
- `/ABSOLUTE/PATH/TO/python3` → your `which python3` output (e.g., `/Users/yourname/.pyenv/shims/python3`)
- `/ABSOLUTE/PATH/TO/.mcp-servers/stdio_server.py` → `/Users/yourname/.mcp-servers/stdio_server.py` (replace `yourname`)
- `GET_API_KEY_FROM_SETTINGS` → your actual API key from http://localhost:6001/settings
- `YOUR_USER_ID` → your user ID from the settings page

**For Development:**
```bash
cp .mcp.dev.json.template .mcp.dev.json
```

Edit `.mcp.dev.json` with the same replacements (but use port 6002 for the settings page).

**Step 5: Example of Final Configuration**

After replacing placeholders, your `.mcp.prod.json` should look like:
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

**Step 6: Restart Claude Code**

After updating MCP configuration files, you must restart Claude Code for changes to take effect.

**Why Absolute Paths Are Required:**
- MCP servers run in their own process, not from your project directory
- Relative paths like `./mcp-server/stdio_server.py` won't work because the working directory is unpredictable
- The Python command needs the full path to ensure the correct interpreter is used
- Using `~/.mcp-servers/` as a standard location keeps your configuration portable across projects

### MCP Environment Switching

With both environments configured, MCP tools will have separate prefixes:
- Production tools: `mcp__task-tracker-prod__*`
- Development tools: `mcp__task-tracker-dev__*`

This allows you to work with both environments simultaneously without conflicts.

### Available MCP Tools (40+)

**Project Management:**
- `list_projects` - List all projects
- `create_project` - Create a new project
- `get_project` - Get project details with tasks
- `get_project_stats` - Get project statistics (task counts, completion rates)
- `update_project` - Update project details
- `delete_project` - Delete a project and all its tasks
- `list_assignable_users` - List users who can be assigned tasks in a project
- `transfer_project_team` - Transfer project to different team or make personal

**Task Management:**
- `list_tasks` - List tasks with filters (project_id, status, priority, tag, owner_id, dates)
- `list_actionable_tasks` - Get unblocked tasks ready for work (excludes backlog, blocked, done)
- `list_overdue_tasks` - List tasks past their due date
- `list_upcoming_tasks` - List tasks due within N days
- `create_task` - Create a new task (supports subtasks via parent_task_id)
- `get_task` - Get task details with comments
- `update_task` - Update task fields (status, priority, time tracking, etc.)
- `complete_task` - Mark task as completed (sets status to `done`)
- `take_ownership` - Claim task ownership (assigns to authenticated user)
- `delete_task` - Delete a task
- `search` - Global search across tasks, projects, and comments

**Subtasks & Dependencies:**
- `get_task_dependencies` - Get task with full dependency information
- `add_task_dependency` - Add a blocking dependency between tasks
- `remove_task_dependency` - Remove a blocking dependency
- `get_task_subtasks` - Get all subtasks of a task
- `get_task_progress` - Get completion percentage based on subtasks

**Bulk Operations:**
- `bulk_create_tasks` - Create multiple tasks in a single transaction
- `bulk_update_tasks` - Update multiple tasks at once
- `bulk_delete_tasks` - Delete multiple tasks in a single transaction
- `bulk_take_ownership` - Claim ownership of multiple tasks
- `bulk_add_dependencies` - Add multiple task dependencies at once

**Team Management:**
- `list_teams` - List all teams
- `create_team` - Create a new team (creator becomes admin)
- `get_team` - Get team details with members and projects
- `update_team` - Update team details (admin only)
- `delete_team` - Delete a team (admin only)
- `list_team_members` - List all members of a team
- `add_team_member` - Add a user to a team (admin only)
- `update_team_member` - Update team member role (admin only)
- `remove_team_member` - Remove user from team (admin only)

**User Management:**
- `list_users` - List all users (admin only)
- `create_user` - Create a new user (admin only)
- `get_current_user` - Get authenticated user information

**Events & Timeline:**
- `get_task_events` - Get event history for a specific task
- `get_project_events` - Get event history for all tasks in a project

**Comments:**
- `list_comments` - List comments for a task
- `add_comment` - Add a comment to a task
- `delete_comment` - Delete a comment

**Configuration:**
- `generate_mcp_config` - Generate complete MCP configuration with API key

**Statistics:**
- `get_stats` - Get overall task tracker statistics

## API Overview

### Authentication
All endpoints require authentication via:
- **JWT Bearer Token** - For web UI (login via `/api/auth/login`)
- **API Key** - For MCP/programmatic access (send via `X-API-Key` header)

### Key Endpoints

#### Authentication
- `POST /api/auth/login` - Login with email/password (returns JWT token)
- `POST /api/auth/api-keys` - Create API key for programmatic access
- `GET /api/auth/api-keys` - List user's API keys
- `DELETE /api/auth/api-keys/{key_id}` - Revoke an API key

#### Tasks
- `GET /api/tasks` - List tasks with filtering (status, priority, owner, dates, search)
- `POST /api/tasks` - Create task (supports `parent_task_id` for subtasks)
- `GET /api/tasks/{id}` - Get task details with comments
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `POST /api/tasks/{id}/take-ownership` - Claim task ownership
- `POST /api/tasks/{id}/complete` - Mark task as done

#### Subtasks & Progress
- `GET /api/tasks/{id}/subtasks` - List subtasks
- `GET /api/tasks/{id}/progress` - Get completion percentage

#### Dependencies
- `GET /api/tasks/{id}/dependencies` - Get task with dependency info
- `POST /api/tasks/{id}/dependencies` - Add blocking relationship
- `DELETE /api/tasks/{id}/dependencies/{blocking_id}` - Remove dependency
- `GET /api/tasks/actionable` - Query unblocked, actionable tasks

#### Time Tracking
- `GET /api/tasks/overdue` - List overdue tasks
- `GET /api/tasks/upcoming?days=7` - List tasks due soon

#### Events
- `GET /api/tasks/{id}/events` - Get task event history
- `GET /api/projects/{id}/events` - Get project event timeline

#### Projects
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create project
- `GET /api/projects/{id}` - Get project with tasks
- `GET /api/projects/{id}/stats` - Get project statistics
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project
- `GET /api/projects/{id}/assignable-users` - List assignable users
- `PUT /api/projects/{id}/transfer` - Transfer project to different team

#### Teams
- `GET /api/teams` - List all teams
- `POST /api/teams` - Create team
- `GET /api/teams/{id}` - Get team details
- `PUT /api/teams/{id}` - Update team (admin only)
- `DELETE /api/teams/{id}` - Delete team (admin only)
- `GET /api/teams/{id}/members` - List team members
- `POST /api/teams/{id}/members` - Add team member (admin only)
- `PUT /api/teams/{id}/members/{user_id}` - Update member role (admin only)
- `DELETE /api/teams/{id}/members/{user_id}` - Remove member (admin only)

#### Users
- `GET /api/users` - List all users (admin only)
- `POST /api/users` - Create user (admin only)
- `GET /api/users/me` - Get current user

#### Comments
- `GET /api/tasks/{task_id}/comments` - List comments
- `POST /api/tasks/{task_id}/comments` - Create comment
- `DELETE /api/comments/{id}` - Delete comment

#### Search
- `GET /api/search?q=query` - Global search across tasks, projects, comments

#### Statistics
- `GET /api/stats` - Overall statistics

See the [API documentation](http://localhost:6001/docs) (Swagger UI) for complete endpoint details.

## Business Rules

### Task Completion
- Cannot mark task as `done` if it has incomplete subtasks
- Cannot mark task as `done` if blocked by incomplete dependencies
- Parent task requires all subtasks to be `done` before it can be marked `done`
- Tasks in `backlog` or `done` status are excluded from actionable queries

### Dependency Creation
- No circular dependencies allowed (validated with BFS algorithm)
- Parent task cannot block its own subtask (prevents deadlock)
- Tasks must be in the same project
- No self-blocking allowed

### Time Tracking
- All time fields (`due_date`, `estimated_hours`, `actual_hours`) are optional
- **Overdue Definition:** `due_date < now AND status NOT IN ('done', 'backlog')`
- **Progress Calculation:** `(actual_hours / estimated_hours) * 100`
- Red indicator when over budget (actual > estimated)
- Green indicator when under budget (actual <= estimated)

### Validation Order
1. Task existence (404 for missing entities)
2. Same project constraint
3. Circular dependency check (BFS algorithm)
4. Parent-subtask deadlock check
5. Status and completion validations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Task Tracker                          │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React/Next.js)                                   │
│    ├─ Task Lists & Kanban Board                            │
│    ├─ Dependency Visualization                             │
│    ├─ Time Tracking & Progress                             │
│    └─ Team & Project Management                            │
├─────────────────────────────────────────────────────────────┤
│  Backend (FastAPI)                                          │
│    ├─ REST API (40+ endpoints)                             │
│    ├─ JWT + API Key Authentication                         │
│    ├─ Business Logic & Validation                          │
│    │   ├─ Circular Dependency Detection (BFS)              │
│    │   ├─ Parent-Subtask Validation                        │
│    │   └─ Task Completion Rules                            │
│    └─ Event Timeline Tracking                              │
├─────────────────────────────────────────────────────────────┤
│  Database (PostgreSQL)                                      │
│    ├─ Tasks, Projects, Teams, Users                        │
│    ├─ Task Dependencies                                     │
│    ├─ Task Events (Audit Trail)                            │
│    └─ Full-Text Search Indexes                             │
├─────────────────────────────────────────────────────────────┤
│  MCP Server (stdio)                                         │
│    ├─ 40+ Tools for AI Agents                              │
│    ├─ Bulk Operations                                       │
│    └─ Actionable Tasks Query                               │
└─────────────────────────────────────────────────────────────┘
```

## Data Model

```
User
├── id
├── name
├── email
├── password_hash
├── role (admin | editor | viewer)
├── is_active
├── email_verified
├── last_login_at
└── created_at

Team
├── id
├── name
├── description
├── created_by → User
├── created_at
└── updated_at

TeamMember
├── team_id → Team
├── user_id → User
├── role (admin | member)
└── joined_at

Project
├── id
├── name
├── description
├── author_id → User
├── team_id → Team (nullable, for team projects)
├── kanban_settings (JSONB)
├── created_at
└── updated_at

Task
├── id
├── title
├── description
├── tag (bug | feature | idea)
├── priority (P0 | P1)
├── status (backlog | todo | in_progress | blocked | review | done)
├── project_id → Project
├── author_id → User
├── owner_id → User (nullable)
├── parent_task_id → Task (nullable, for subtasks)
├── due_date (datetime)
├── estimated_hours (decimal)
├── actual_hours (decimal)
├── is_blocked (computed field)
├── created_at
└── updated_at

TaskEvent
├── id
├── task_id → Task
├── event_type (task_created | status_change | field_update | ownership_change | dependency_added | dependency_removed | comment_added)
├── actor_id → User
├── field_name
├── old_value
├── new_value
├── event_metadata (JSONB)
└── created_at

TaskDependency
├── blocking_task_id → Task
└── blocked_task_id → Task

Comment
├── id
├── content
├── task_id → Task
├── author_id → User
├── created_at
└── updated_at

APIKey
├── id
├── user_id → User
├── name
├── key_hash
├── key_prefix
├── expires_at
├── last_used_at
└── created_at
```

## Task Workflow Best Practices

### Before Working on Tasks

**IMPORTANT:** Always take ownership of a task before starting work on it:

```bash
# Take ownership via API
curl -X POST http://localhost:6002/api/tasks/{task_id}/take-ownership \
  -H "X-API-Key: your-api-key" \
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
   curl http://localhost:6002/api/tasks/actionable
   ```
   Or use: `mcp__task-tracker__list_actionable_tasks()`

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

## Multi-Environment Benefits

The task tracker supports **separate production and development environments** that can run simultaneously:

| Feature | Production | Development |
|---------|-----------|-------------|
| Frontend Port | 3000 | 3001 |
| Backend Port | 6001 | 6002 |
| Database Port | 5432 | 5433 |
| Database Name | tasktracker | tasktracker_dev |
| Docker Volume | postgres_data | postgres_data_dev |

**Benefits:**
- ✅ Complete isolation - experiments never affect production
- ✅ Data safety - development resets don't touch production
- ✅ Parallel operation - run both environments simultaneously
- ✅ Independent APIs - separate authentication and API keys
- ✅ Easy reset - `make dev-reset` wipes development cleanly
- ✅ Database isolation - separate databases prevent data corruption
- ✅ Port separation - no conflicts when running both

## Development

### Project Structure

```
task-tracker/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy models
│   │   ├── routes/          # API endpoints
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── auth/            # Authentication & authorization
│   │   └── main.py          # FastAPI app
│   ├── init.sql             # Database schema (source of truth)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Next.js pages
│   │   └── lib/             # Utilities
│   └── package.json
├── mcp-server/
│   ├── stdio_server.py      # MCP server implementation
│   └── requirements.txt
├── docker-compose.yml       # Base Docker config
├── docker-compose.override.yml  # Development defaults
├── docker-compose.prod.yml  # Production overrides
├── docker-compose.dev.yml   # Development overrides (explicit)
├── .env.production          # Production config (no secrets)
├── .env.development        # Development config (safe defaults)
├── .env.local              # Local secrets (gitignored)
├── Makefile                # Convenience commands
├── CLAUDE.md               # AI agent instructions
└── README.md               # This file
```

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Database Access

**Development:**
```bash
# Via Make
make dev-db

# Or direct connection
psql postgresql://taskuser:taskpass@localhost:5433/tasktracker_dev
```

**Production:**
```bash
# Via Make
make prod-db

# Or direct connection
psql postgresql://taskuser:taskpass@localhost:5432/tasktracker
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

### Testing Backend Changes

```bash
# Restart backend after code changes
make dev-restart backend

# Test health endpoint
curl http://localhost:6002/health

# Test API endpoints
curl http://localhost:6002/api/tasks \
  -H "X-API-Key: your-api-key"

# View logs
make dev-logs
```

## Contributing

This is an experimental project for AI agent task management. Contributions are welcome!

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch** from `main`
3. **Make your changes** in the development environment
4. **Test thoroughly** using the development environment
5. **Submit a pull request** with a clear description

### Code Style

- **Backend:** Follow PEP 8 (Python), use type hints
- **Frontend:** ESLint configuration, TypeScript strict mode
- **Commits:** Use conventional commits (feat:, fix:, docs:, etc.)

## Support

For issues, questions, or contributions:
- **GitHub Issues:** Create an issue in the repository
- **Documentation:** See CLAUDE.md for AI agent integration details

## License

MIT License - see LICENSE file for details.

---

Built with ❤️ for AI agent workflows
