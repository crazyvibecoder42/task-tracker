# Task Tracker - Detailed Setup Guide

This document contains comprehensive setup and configuration information for the Task Tracker application.

## Table of Contents

- [Environment Overview](#environment-overview)
- [Quick Start](#quick-start)
- [Environment Configuration](#environment-configuration)
- [MCP Server Setup](#mcp-server-setup)
- [API Endpoints](#api-endpoints)
- [Business Rules](#business-rules)
- [Architecture](#architecture)
- [Data Model](#data-model)
- [Development](#development)

## Environment Overview

The Task Tracker supports **separate production and development environments** that can run simultaneously:

| Environment | Frontend | Backend | Database | DB Name | Volume |
|-------------|----------|---------|----------|---------|--------|
| **Production** | 3000 | 6001 | 5432 | tasktracker | postgres_data |
| **Development** | 3001 | 6002 | 5433 | tasktracker_dev | postgres_data_dev |

## Quick Start

### Development Environment (Recommended)

```bash
# Simplest command - automatically starts development environment
docker compose up -d

# Access the application
# Frontend: http://localhost:3001
# Backend API: http://localhost:6002
# API Docs: http://localhost:6002/docs

# Stop
docker compose down
```

**Default Development Credentials:**
- Email: `admin@example.com`
- Password: `admin123`
- User ID: `1`
- Role: `admin`

### Production Environment

```bash
# Start production (ports 3000/6001/5432)
make prod-start

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:6001
# API Docs: http://localhost:6001/docs

# Stop production
make prod-stop
```

**⚠️ Production Setup:**
1. Create `.env.local` with secure credentials:
   ```bash
   ADMIN_PASSWORD=your-strong-password
   JWT_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
   ```
2. Change the admin password immediately after first login

### Running Both Environments Simultaneously

```bash
make start-all    # Start both production and development
make status       # Check status of all containers
make stop-all     # Stop both environments
```

### Available Make Commands

- **Production**: `prod-start`, `prod-stop`, `prod-logs`, `prod-restart`, `prod-reset`, `prod-db`
- **Development**: `dev-start`, `dev-stop`, `dev-logs`, `dev-restart`, `dev-reset`, `dev-db`
- **Combined**: `start-all`, `stop-all`, `status`, `clean`

## Environment Configuration

### Development vs Production

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

```
├── docker-compose.yml              # Base configuration (shared)
├── docker-compose.override.yml     # Auto-loaded development defaults
├── docker-compose.prod.yml         # Production overrides
├── docker-compose.dev.yml          # Development overrides (explicit)
├── .env.production                 # Production config (no secrets)
├── .env.development               # Development config (safe defaults)
├── .env.local                     # Local secrets (gitignored)
├── .mcp.prod.json                 # Production MCP (gitignored)
├── .mcp.dev.json                  # Development MCP (gitignored)
├── .mcp.prod.json.template        # Production MCP template
└── .mcp.dev.json.template         # Development MCP template
```

## REST API Usage (Direct curl)

**Note:** Most users will interact through MCP tools, not direct API calls. This section is for reference or custom integrations.

### Admin Setup via REST API

**Step 1: Login as Admin**
```bash
curl -X POST http://localhost:6002/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

**Step 2: Create a Team**
```bash
curl -X POST http://localhost:6002/api/teams \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"AI Research Team","description":"Collaborative AI agents"}'
```

**Step 3: Create a Project**
```bash
curl -X POST http://localhost:6002/api/projects \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Research Project","team_id":1}'
```

**Step 4: Create Users for Each Agent**
```bash
curl -X POST http://localhost:6002/api/users \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Research Agent","email":"agent1@example.com","password":"agent123","role":"editor"}'
```

**Step 5: Add User to Team**
```bash
curl -X POST http://localhost:6002/api/teams/1/members \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":2,"role":"member"}'
```

### Agent MCP Configuration via REST API

**Generate MCP Config for an Agent:**
```bash
# Login as the agent
curl -X POST http://localhost:6002/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"agent1@example.com","password":"agent123"}'

# Generate MCP configuration (creates API key and returns config)
curl -X POST http://localhost:6002/api/auth/generate-mcp-config \
  -H "Authorization: Bearer <agent_token>" \
  -H "Content-Type: application/json" \
  -d '{"key_name":"Agent 1 MCP Access","api_url":"http://localhost:6002"}'
```

## MCP Server Setup

### MCP Configuration (Recommended Method)

**IMPORTANT:** MCP servers require absolute paths for both the Python interpreter and the server script.

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

**Step 3: Generate API Keys**

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

**Step 4: Create Configuration from Template**

```bash
cp .mcp.dev.json.template .mcp.dev.json
```

Edit `.mcp.dev.json` and replace:
- `/ABSOLUTE/PATH/TO/python3` → your `which python3` output
- `/ABSOLUTE/PATH/TO/.mcp-servers/stdio_server.py` → `/Users/yourname/.mcp-servers/stdio_server.py`
- `GET_API_KEY_FROM_SETTINGS` → your actual API key
- `YOUR_USER_ID` → your user ID from http://localhost:6002/settings

**Step 5: Restart Claude Code**

After updating MCP configuration files, you must restart Claude Code for changes to take effect.

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with email/password (returns JWT token)
- `POST /api/auth/api-keys` - Create API key for programmatic access
- `GET /api/auth/api-keys` - List user's API keys
- `DELETE /api/auth/api-keys/{key_id}` - Revoke an API key

### Tasks
- `GET /api/tasks` - List tasks with filtering
- `POST /api/tasks` - Create task (supports `parent_task_id` for subtasks)
- `GET /api/tasks/{id}` - Get task details
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `POST /api/tasks/{id}/take-ownership` - Claim task ownership
- `POST /api/tasks/{id}/complete` - Mark task as done

### Subtasks & Dependencies
- `GET /api/tasks/{id}/subtasks` - List subtasks
- `GET /api/tasks/{id}/progress` - Get completion percentage
- `GET /api/tasks/{id}/dependencies` - Get task with dependency info
- `POST /api/tasks/{id}/dependencies` - Add blocking relationship
- `DELETE /api/tasks/{id}/dependencies/{blocking_id}` - Remove dependency
- `GET /api/tasks/actionable` - Query unblocked, actionable tasks

### Time Tracking
- `GET /api/tasks/overdue` - List overdue tasks
- `GET /api/tasks/upcoming?days=7` - List tasks due soon

### Projects & Teams
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create project
- `GET /api/teams` - List all teams
- `POST /api/teams` - Create team
- `GET /api/teams/{id}/members` - List team members
- `POST /api/teams/{id}/members` - Add team member (admin only)

### Search
- `GET /api/search?q=query` - Global search across tasks, projects, comments

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
└── created_at

Team
├── id
├── name
├── description
├── created_by → User
└── created_at

Project
├── id
├── name
├── description
├── author_id → User
├── team_id → Team (nullable)
└── created_at

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
└── created_at

TaskDependency
├── blocking_task_id → Task
└── blocked_task_id → Task

Comment
├── id
├── content
├── task_id → Task
├── author_id → User
└── created_at

APIKey
├── id
├── user_id → User
├── name
├── key_prefix
├── expires_at
└── created_at
```

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
└── Makefile                # Convenience commands
```

### Database Access

**Development:**
```bash
make dev-db
# Or: psql postgresql://taskuser:taskpass@localhost:5433/tasktracker_dev
```

**Production:**
```bash
make prod-db
# Or: psql postgresql://taskuser:taskpass@localhost:5432/tasktracker
```

### Testing Backend Changes

```bash
# Restart backend after code changes
make dev-restart backend

# Test endpoints
curl http://localhost:6002/health

# View logs
make dev-logs
```

## Multi-Environment Benefits

| Feature | Production | Development |
|---------|-----------|-------------|
| Frontend Port | 3000 | 3001 |
| Backend Port | 6001 | 6002 |
| Database Port | 5432 | 5433 |
| Database Name | tasktracker | tasktracker_dev |

**Benefits:**
- ✅ Complete isolation - experiments never affect production
- ✅ Data safety - development resets don't touch production
- ✅ Parallel operation - run both environments simultaneously
- ✅ Independent APIs - separate authentication and API keys
- ✅ Easy reset - `make dev-reset` wipes development cleanly
