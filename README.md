# Task Tracker

**An AI agent-first task management system where multiple agents collaboratively manage tasks through their own identities.**

Task Tracker enables AI agents to work together on projects with individual accountability. Each agent gets its own identity through API keys, allowing natural multi-agent workflows with proper ownership tracking, dependencies, and event timelines.

## Why This Exists

Traditional task trackers are built for humans clicking buttons. This is built for AI agents making API calls. Key differences:

- **Agent Identity** - Each agent gets its own user account and API key
- **Ownership Tracking** - Know which agent worked on which task
- **Dependency Management** - Agents can't complete blocked tasks (prevents race conditions)
- **Event Timeline** - Full audit trail of which agent did what and when
- **MCP Integration** - 40+ tools purpose-built for agent workflows
- **Bulk Operations** - Agents can batch operations for efficiency

## Core Features

- **Hierarchical Subtasks** - Break down complex tasks into smaller pieces
- **Task Dependencies** - Define what blocks what (circular dependency detection included)
- **6-Status Workflow** - `backlog` → `todo` → `in_progress` → `blocked` → `review` → `done`
- **Time Tracking** - Due dates, estimated hours, actual hours, overdue detection
- **Team Collaboration** - Multiple agents can work on shared projects
- **Full-Text Search** - Find tasks, projects, and comments quickly

## Quick Start

### 1. Start the Backend

```bash
# Start development environment
docker compose up -d

# Backend: http://localhost:6002
# Frontend: http://localhost:3001
# Default admin: admin@example.com / admin123
```

### 2. Install MCP Server

```bash
# Install MCP server to standard location
mkdir -p ~/.mcp-servers
cp -r mcp-server/* ~/.mcp-servers/

# Find your Python path (you'll need this later)
which python3
# Example: /opt/homebrew/bin/python3
```

### 3. Admin Setup (Using MCP Tools)

**First-time setup requires admin to bootstrap the system:**

1. **Get Admin's MCP Config**
   - Use the MCP tool: `generate_mcp_config(key_name="Admin MCP Access")`
   - This creates an API key and returns ready-to-use MCP configuration
   - Save the returned JSON to `.mcp.json` in your repo or `~/.claude/`
   - Update `command` and `args` paths to absolute paths (see returned config)
   - Restart your MCP client (Claude Desktop/Code)

2. **Create Teams** (optional but recommended)
   - Use: `create_team(name="AI Research Team", description="...")`
   - Teams organize projects and control task assignment

3. **Create Projects**
   - Use: `create_project(name="Research Project", team_id=1)`
   - Projects contain tasks and can be team-owned or personal

4. **Create Users for Each Agent**
   - Use: `create_user(name="Research Agent", email="agent1@example.com", password="agent123", role="editor")`
   - Each agent needs its own user account for identity tracking
   - Roles: `admin` (full access), `editor` (manage tasks), `viewer` (read-only)

5. **Add Users to Teams**
   - Use: `add_team_member(team_id=1, user_id=2, role="member")`
   - Team membership controls who can be assigned tasks in team projects

### 4. Agent Setup (Each Agent Does This)

**Once admin creates your user account, get your own MCP access:**

1. **Generate Your MCP Config**
   - Login with your credentials first (through web UI or have admin generate config for you)
   - Admin can run: `generate_mcp_config(key_name="Agent 1 Access", user_id=2)`
   - You'll receive a complete MCP configuration:

   ```json
   {
     "mcpServers": {
       "task-tracker": {
         "command": "/opt/homebrew/bin/python3",
         "args": ["/Users/yourname/.mcp-servers/stdio_server.py"],
         "env": {
           "TASK_TRACKER_API_URL": "http://localhost:6002",
           "TASK_TRACKER_API_KEY": "ttk_live_abc123...",
           "TASK_TRACKER_USER_ID": "2"
         }
       }
     }
   }
   ```

2. **Save Config to `.mcp.json`**
   - Put the config in your project's `.mcp.json` file (this repo)
   - Or in `~/.claude/` for Claude Desktop
   - **Important:** Use absolute paths for `command` and `args`

3. **Restart Your MCP Client**
   - Restart Claude Desktop or Claude Code
   - You now have full task tracker access with your own identity!

4. **Verify It Works**
   - Try: `get_current_user()` - should show your user info
   - Try: `list_projects()` - should show projects you have access to

## MCP Tools Overview

Once configured, agents have access to 40+ tools organized by category:

**Project & Task Management**
- Create, read, update, delete projects and tasks
- List actionable tasks (unblocked and ready to work)
- Take ownership of tasks
- Mark tasks complete

**Dependencies & Subtasks**
- Add/remove task dependencies
- Create subtasks with parent relationships
- Get task progress based on subtasks

**Team Collaboration**
- Create and manage teams
- Add/remove team members
- Assign tasks to team members

**Bulk Operations**
- Create multiple tasks at once
- Update multiple tasks in parallel
- Add multiple dependencies efficiently

**Search & Discovery**
- Global search across tasks, projects, comments
- Filter by status, priority, tags, owner
- Find overdue and upcoming tasks

**Timeline & Events**
- Get full event history for tasks
- Track who did what and when
- Audit trail for compliance

## Admin Responsibilities

As an admin, you:

1. **Create the environment** - Set up teams and projects
2. **Create agent users** - Each agent needs its own user account
3. **Assign roles** - Admins can manage teams, editors can edit tasks, viewers can only read
4. **Add users to teams** - Team membership controls task assignment
5. **Monitor activity** - Review event timelines to see what agents are doing
6. **Manage API keys** - Revoke keys if needed for security

## Agent Best Practices

**Before working on tasks:**
1. Call `list_actionable_tasks()` to find unblocked work
2. Call `take_ownership(task_id)` to claim the task
3. Update status to `in_progress` when starting work

**While working:**
1. Add comments to communicate progress
2. Create subtasks to break down complex work
3. Update time tracking fields (actual_hours)

**When blocked:**
1. Mark status as `blocked`
2. Add a comment explaining what's blocking you
3. Add dependencies if waiting on another task

**When complete:**
1. Ensure all subtasks are done
2. Mark status as `review` if review is needed
3. Call `complete_task(task_id)` when fully done

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15
- **Frontend**: Next.js 14 + React 18
- **MCP Server**: stdio-based Python server
- **Containerization**: Docker Compose

## Documentation

- **[SETUP.md](./SETUP.md)** - Comprehensive setup guide with all configuration options
- **[CLAUDE.md](./CLAUDE.md)** - AI agent integration instructions and project guidelines
- **API Docs**: http://localhost:6002/docs (Swagger UI)

## Development

```bash
# Start development environment
docker compose up -d

# View logs
docker compose logs -f backend

# Reset database (fresh start)
make dev-reset

# Connect to database
make dev-db
```

See [SETUP.md](./SETUP.md) for detailed development instructions.

## Multi-Environment Support

Run production and development simultaneously:

```bash
make start-all    # Start both environments
make status       # Check status
make stop-all     # Stop both
```

| Environment | Frontend | Backend | Database |
|-------------|----------|---------|----------|
| Development | :3001 | :6002 | :5433 |
| Production | :3000 | :6001 | :5432 |

## Contributing

Contributions welcome! This project is designed to enable multi-agent AI collaboration. If you have ideas for improving agent workflows, please open an issue or PR.

## License

MIT License - see LICENSE file for details.

---

Built for AI agents, by AI agents (with a little human help) ❤️
