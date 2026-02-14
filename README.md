# Task Tracker

A full-stack task tracking system with PostgreSQL, FastAPI backend, Next.js frontend, and MCP server for programmatic access.

## Features

- **Projects**: Create and manage projects
- **Tasks**: Track tasks with tags (bug, feature, idea), priorities (P0, P1), and 6-status workflow system
- **6-Status Workflow**: Tasks progress through `backlog` → `todo` → `in_progress` → `review` → `done`, with `blocked` as a temporary state
- **Event Tracking**: Comprehensive audit trail and timeline for all task operations
- **Task Dependencies**: Create blocking relationships between tasks with circular dependency detection
- **Hierarchical Subtasks**: Break down tasks into subtasks with automatic progress tracking
- **Comments**: Add comments to tasks with author attribution
- **Authors**: Manage team members/authors
- **Dashboard**: Overview with statistics and completion rate
- **MCP Server**: Programmatic access to manage tasks via Claude or other MCP clients

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

### Available MCP Tools

**Project Management:**
- `list_projects` - List all projects
- `create_project` - Create a new project
- `get_project` - Get project details with tasks
- `get_project_stats` - Get project statistics
- `update_project` - Update a project
- `delete_project` - Delete a project

**Task Management:**
- `list_tasks` - List tasks with optional filters (project_id, status, priority, tag, owner_id)
- `create_task` - Create a new task
- `get_task` - Get task details with comments
- `update_task` - Update a task
- `complete_task` - Mark task as completed (sets status to `done`)
- `take_ownership` - Assign task ownership to an author
- `delete_task` - Delete a task
- `get_actionable_tasks` - Get unblocked tasks ready for work (excludes backlog, blocked, done)
- `get_task_dependencies` - Get task with full dependency information
- `add_task_dependency` - Add a blocking dependency between tasks
- `remove_task_dependency` - Remove a blocking dependency
- `get_task_subtasks` - Get all subtasks of a task
- `get_task_progress` - Get completion percentage based on subtasks
- `get_task_events` - Get event history for a specific task
- `get_project_events` - Get event history for all tasks in a project

**Comment Management:**
- `list_comments` - List comments for a task
- `add_comment` - Add a comment to a task
- `delete_comment` - Delete a comment

**Author Management:**
- `list_authors` - List all authors
- `create_author` - Create a new author

**Statistics:**
- `get_stats` - Get overall statistics

## API Endpoints

### Authors
- `GET /api/authors` - List all authors
- `POST /api/authors` - Create author
- `GET /api/authors/{id}` - Get author
- `PUT /api/authors/{id}` - Update author
- `DELETE /api/authors/{id}` - Delete author

### Projects
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create project
- `GET /api/projects/{id}` - Get project with tasks
- `GET /api/projects/{id}/stats` - Get project statistics
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

### Tasks
- `GET /api/tasks` - List tasks (query params: project_id, status, priority, tag)
- `POST /api/tasks` - Create task
- `GET /api/tasks/{id}` - Get task with comments
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task

### Comments
- `GET /api/tasks/{task_id}/comments` - List comments
- `POST /api/tasks/{task_id}/comments` - Create comment
- `PUT /api/comments/{id}` - Update comment
- `DELETE /api/comments/{id}` - Delete comment

### Statistics
- `GET /api/stats` - Overall statistics

## Data Model

```
Author
├── id
├── name
├── email
└── created_at

Project
├── id
├── name
├── description
├── author_id → Author
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
├── author_id → Author
├── owner_id → Author
├── parent_task_id → Task (for subtasks)
├── created_at
└── updated_at

TaskEvent
├── id
├── task_id → Task
├── event_type (task_created | status_change | field_update | ownership_change | dependency_added | dependency_removed | comment_added)
├── actor_id → Author
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
├── author_id → Author
├── created_at
└── updated_at
```

## Development

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

## License

MIT
