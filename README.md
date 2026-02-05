# Task Tracker

A full-stack task tracking system with PostgreSQL, FastAPI backend, Next.js frontend, and MCP server for programmatic access.

## Features

- **Projects**: Create and manage projects
- **Tasks**: Track tasks with tags (bug, feature, idea), priorities (P0, P1), and status (pending, completed)
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

### Running the Application

1. **Start all services:**
   ```bash
   chmod +x start.sh stop.sh
   ./start.sh
   ```

2. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:6001
   - API Documentation: http://localhost:6001/docs
   - MCP Server (HTTP/SSE): http://localhost:6000

3. **Stop the application:**
   ```bash
   ./stop.sh
   ```

## MCP Server Setup

The MCP server allows programmatic access to the task tracker through Claude Desktop or other MCP clients.

### Installation

1. Install dependencies:
   ```bash
   cd mcp-server
   pip install -r requirements.txt
   ```

2. Add to your Claude Desktop configuration (`claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "task-tracker": {
         "command": "python",
         "args": ["/path/to/task-tracker/mcp-server/stdio_server.py"],
         "env": {
           "TASK_TRACKER_API_URL": "http://localhost:6001"
         }
       }
     }
   }
   ```

### Available MCP Tools

**Project Management:**
- `list_projects` - List all projects
- `create_project` - Create a new project
- `get_project` - Get project details with tasks
- `get_project_stats` - Get project statistics
- `update_project` - Update a project
- `delete_project` - Delete a project

**Task Management:**
- `list_tasks` - List tasks with optional filters (project_id, status, priority, tag)
- `create_task` - Create a new task
- `get_task` - Get task details with comments
- `update_task` - Update a task
- `complete_task` - Mark task as completed
- `delete_task` - Delete a task

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
├── status (pending | completed)
├── project_id → Project
├── author_id → Author
├── created_at
└── updated_at

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
