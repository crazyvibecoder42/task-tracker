#!/usr/bin/env python3
"""
Task Tracker MCP Server - STDIO Mode

This is the stdio-based server for Claude Desktop integration.
For HTTP/SSE access on port 6000, use server.py instead.
"""

import os
import json
import asyncio
from typing import Any, Optional
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configuration
API_BASE_URL = os.getenv("TASK_TRACKER_API_URL", "http://localhost:6001")
API_KEY = os.getenv("TASK_TRACKER_API_KEY")


def validate_api_key():
    """
    Validate API key configuration.

    Raises SystemExit if API key is missing, invalid, or incorrectly formatted.
    This validation is deferred to runtime (not import time) to allow module
    imports for testing and tooling.
    """
    import sys

    # Validate API key is not a placeholder or invalid format
    INVALID_KEYS = ["SET_YOUR_API_KEY_HERE", "YOUR_API_KEY", "PLACEHOLDER", "", "null", "None", "undefined"]
    if not API_KEY or API_KEY in INVALID_KEYS:
        print("ERROR: Invalid or missing TASK_TRACKER_API_KEY", file=sys.stderr)
        print("Run: ./setup-mcp-quick.sh to configure", file=sys.stderr)
        sys.exit(1)

    # Validate API key format (must start with ttk_)
    if not API_KEY.startswith("ttk_"):
        print("ERROR: Invalid TASK_TRACKER_API_KEY format. Must start with 'ttk_'", file=sys.stderr)
        print("Run: ./setup-mcp-quick.sh to generate a valid API key", file=sys.stderr)
        sys.exit(1)

# Initialize MCP server
server = Server("task-tracker")

# HTTP client for API calls
http_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    global http_client
    if http_client is None:
        headers = {}
        if API_KEY:
            headers["X-API-Key"] = API_KEY
        http_client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0, headers=headers)
    return http_client


async def api_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Make an API request to the backend."""
    client = await get_client()
    try:
        if method == "GET":
            response = await client.get(endpoint, params=data)
        elif method == "POST":
            response = await client.post(endpoint, json=data)
        elif method == "PUT":
            response = await client.put(endpoint, json=data)
        elif method == "DELETE":
            response = await client.delete(endpoint)
        else:
            return {"error": f"Unsupported method: {method}"}

        if response.status_code >= 400:
            return {"error": f"API error: {response.status_code}", "detail": response.text}

        if response.status_code == 204 or not response.text:
            return {"success": True}

        return response.json()
    except httpx.RequestError as e:
        return {"error": f"Request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON response from API"}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(name="list_projects", description="List all projects in the task tracker",
             inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="create_project", description="Create a new project",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string", "description": "Project name"},
                 "description": {"type": "string", "description": "Project description"},
                 "author_id": {"type": "integer", "description": "Author ID (optional)"},
                 "team_id": {"type": "integer", "description": "Team ID to associate with project (optional)"}
             }, "required": ["name"]}),
        Tool(name="get_project", description="Get a project by ID with all its tasks",
             inputSchema={"type": "object", "properties": {
                 "project_id": {"type": "integer", "description": "Project ID"}
             }, "required": ["project_id"]}),
        Tool(name="get_project_stats", description="Get statistics for a project",
             inputSchema={"type": "object", "properties": {
                 "project_id": {"type": "integer", "description": "Project ID"}
             }, "required": ["project_id"]}),
        Tool(name="update_project", description="Update a project",
             inputSchema={"type": "object", "properties": {
                 "project_id": {"type": "integer", "description": "Project ID"},
                 "name": {"type": "string", "description": "New project name"},
                 "description": {"type": "string", "description": "New project description"}
             }, "required": ["project_id"]}),
        Tool(name="delete_project", description="Delete a project and all its tasks",
             inputSchema={"type": "object", "properties": {
                 "project_id": {"type": "integer", "description": "Project ID"}
             }, "required": ["project_id"]}),
        Tool(
            name="list_assignable_users",
            description="List users who can be assigned tasks in a project. Returns team members for team projects or project members for personal projects.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "Project ID"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="transfer_project_team",
            description="Transfer project to a different team or make it personal. Requires owner role in project and admin role in target team. Set team_id to null to make personal.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "Project ID to transfer"},
                    "team_id": {"type": ["integer", "null"], "description": "Target team ID (or null for personal)"}
                },
                "required": ["project_id", "team_id"]
            }
        ),
        Tool(name="list_teams", description="List all teams the user is a member of",
             inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="create_team", description="Create a new team (creator becomes admin)",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string", "description": "Team name"},
                 "description": {"type": "string", "description": "Team description (optional)"}
             }, "required": ["name"]}),
        Tool(name="get_team", description="Get team details with members and projects",
             inputSchema={"type": "object", "properties": {
                 "team_id": {"type": "integer", "description": "Team ID"}
             }, "required": ["team_id"]}),
        Tool(name="update_team", description="Update team details (admin only)",
             inputSchema={"type": "object", "properties": {
                 "team_id": {"type": "integer", "description": "Team ID"},
                 "name": {"type": "string", "description": "New team name (optional)"},
                 "description": {"type": "string", "description": "New team description (optional)"}
             }, "required": ["team_id"]}),
        Tool(name="delete_team", description="Delete a team (admin only)",
             inputSchema={"type": "object", "properties": {
                 "team_id": {"type": "integer", "description": "Team ID"}
             }, "required": ["team_id"]}),
        Tool(name="list_team_members", description="List all members of a team",
             inputSchema={"type": "object", "properties": {
                 "team_id": {"type": "integer", "description": "Team ID"}
             }, "required": ["team_id"]}),
        Tool(name="add_team_member", description="Add a user to a team (admin only)",
             inputSchema={"type": "object", "properties": {
                 "team_id": {"type": "integer", "description": "Team ID"},
                 "user_id": {"type": "integer", "description": "User ID to add"},
                 "role": {"type": "string", "enum": ["admin", "member"], "description": "Member role (default: member)"}
             }, "required": ["team_id", "user_id"]}),
        Tool(name="update_team_member", description="Update a team member's role (admin only)",
             inputSchema={"type": "object", "properties": {
                 "team_id": {"type": "integer", "description": "Team ID"},
                 "user_id": {"type": "integer", "description": "User ID"},
                 "role": {"type": "string", "enum": ["admin", "member"], "description": "New member role"}
             }, "required": ["team_id", "user_id", "role"]}),
        Tool(name="remove_team_member", description="Remove a user from a team (admin only)",
             inputSchema={"type": "object", "properties": {
                 "team_id": {"type": "integer", "description": "Team ID"},
                 "user_id": {"type": "integer", "description": "User ID to remove"}
             }, "required": ["team_id", "user_id"]}),
        Tool(name="list_tasks", description="List tasks with optional filters. Requires project_id to prevent cross-project queries (see CLAUDE.md).",
             inputSchema={"type": "object", "properties": {
                 "project_id": {"type": "integer", "description": "Project ID (required - see CLAUDE.md for project assignments)"},
                 "status": {"type": "string", "enum": ["backlog", "todo", "in_progress", "blocked", "review", "done"], "description": "Filter by status"},
                 "priority": {"type": "string", "enum": ["P0", "P1"], "description": "Filter by priority"},
                 "tag": {"type": "string", "enum": ["bug", "feature", "idea"], "description": "Filter by tag"},
                 "owner_id": {"type": "integer", "description": "Filter by owner ID (use 0 for unassigned tasks)"},
                 "q": {"type": "string", "description": "Text search query (searches title and description)"},
                 "sort_by": {"type": "string", "description": "Multi-field sorting (e.g., '-priority,created_at' for priority desc, created_at asc)"},
                 "due_before": {"type": "string", "description": "Filter tasks due before this datetime (ISO 8601 format, e.g., 2026-02-20T15:00:00Z)"},
                 "due_after": {"type": "string", "description": "Filter tasks due after this datetime (ISO 8601 format, e.g., 2026-02-10T00:00:00Z)"},
                 "overdue": {"type": "boolean", "description": "Filter to show only overdue tasks (due_date < now and status not in (done, backlog))"},
                 "limit": {"type": "integer", "description": "Optional: Max tasks to return (no default, max: 500). Omit to get all tasks."},
                 "offset": {"type": "integer", "description": "Pagination offset (default: 0)"}
             }, "required": ["project_id"]}),
        Tool(name="list_actionable_tasks", description="List actionable tasks (excludes backlog, blocked, and done tasks). Requires project_id to prevent cross-project queries (see CLAUDE.md).",
             inputSchema={"type": "object", "properties": {
                 "project_id": {"type": "integer", "description": "Project ID (required - see CLAUDE.md for project assignments)"},
                 "priority": {"type": "string", "enum": ["P0", "P1"], "description": "Filter by priority"},
                 "tag": {"type": "string", "enum": ["bug", "feature", "idea"], "description": "Filter by tag"},
                 "owner_id": {"type": "integer", "description": "Filter by owner ID (use 0 for unassigned tasks)"},
                 "limit": {"type": "integer", "description": "Optional: Max tasks to return (no default, max: 500). Omit to get all tasks."},
                 "offset": {"type": "integer", "description": "Pagination offset (default: 0)"}
             }, "required": ["project_id"]}),
        Tool(name="list_overdue_tasks", description="List tasks that are overdue (due_date < now and status not in (done, backlog))",
             inputSchema={"type": "object", "properties": {
                 "project_id": {"type": "integer", "description": "Filter by project ID (optional)"},
                 "limit": {"type": "integer", "description": "Max tasks to return (default: 10)"},
                 "offset": {"type": "integer", "description": "Pagination offset (default: 0)"}
             }, "required": []}),
        Tool(name="list_upcoming_tasks", description="List tasks due in the next N days (excludes done and backlog)",
             inputSchema={"type": "object", "properties": {
                 "project_id": {"type": "integer", "description": "Filter by project ID (optional)"},
                 "days": {"type": "integer", "description": "Number of days to look ahead (default: 7)"},
                 "limit": {"type": "integer", "description": "Max tasks to return (default: 10)"},
                 "offset": {"type": "integer", "description": "Pagination offset (default: 0)"}
             }, "required": []}),
        Tool(name="search", description="Global search across tasks, projects, and comments with optional filters",
             inputSchema={"type": "object", "properties": {
                 "q": {"type": "string", "description": "Search query (minimum 2 characters)"},
                 "project_id": {"type": "integer", "description": "Filter results to a specific project (optional)"},
                 "search_in": {"type": "array", "items": {"type": "string", "enum": ["tasks", "projects", "comments"]}, "description": "Limit search to specific entity types (optional, defaults to all)"},
                 "status": {"type": "string", "enum": ["backlog", "todo", "in_progress", "blocked", "review", "done"], "description": "Filter tasks by status (optional)"},
                 "priority": {"type": "string", "enum": ["P0", "P1"], "description": "Filter tasks by priority (optional)"},
                 "tag": {"type": "string", "enum": ["bug", "feature", "idea"], "description": "Filter tasks by tag (optional)"},
                 "owner_id": {"type": "integer", "description": "Filter tasks by owner ID (optional, use 0 for unassigned tasks)"},
                 "limit": {"type": "integer", "description": "Max results per entity type (optional, default: 10, max: 100)"}
             }, "required": ["q"]}),
        Tool(name="create_task", description="Create a new task in a project",
             inputSchema={"type": "object", "properties": {
                 "project_id": {"type": "integer", "description": "Project ID"},
                 "title": {"type": "string", "description": "Task title"},
                 "description": {"type": "string", "description": "Task description"},
                 "tag": {"type": "string", "enum": ["bug", "feature", "idea"], "description": "Task tag"},
                 "priority": {"type": "string", "enum": ["P0", "P1"], "description": "Task priority"},
                 "due_date": {"type": "string", "description": "ISO 8601 datetime string (e.g., 2026-02-20T15:00:00Z)"},
                 "estimated_hours": {"type": "number", "description": "Estimated effort in hours (e.g., 5.5)"},
                 "author_id": {"type": "integer", "description": "Author ID (optional)"},
                 "owner_id": {"type": "integer", "description": "Owner ID (optional)"}
             }, "required": ["project_id", "title"]}),
        Tool(name="get_task", description="Get a task by ID with all comments",
             inputSchema={"type": "object", "properties": {
                 "task_id": {"type": "integer", "description": "Task ID"}
             }, "required": ["task_id"]}),
        Tool(name="update_task", description="Update a task",
             inputSchema={"type": "object", "properties": {
                 "task_id": {"type": "integer", "description": "Task ID"},
                 "title": {"type": "string", "description": "New task title"},
                 "description": {"type": "string", "description": "New task description"},
                 "tag": {"type": "string", "enum": ["bug", "feature", "idea"], "description": "New task tag"},
                 "priority": {"type": "string", "enum": ["P0", "P1"], "description": "New task priority"},
                 "status": {"type": "string", "enum": ["backlog", "todo", "in_progress", "blocked", "review", "done"], "description": "New task status"},
                 "due_date": {"type": "string", "description": "ISO 8601 datetime string (e.g., 2026-02-20T15:00:00Z)"},
                 "estimated_hours": {"type": "number", "description": "Estimated effort in hours (e.g., 5.5)"},
                 "actual_hours": {"type": "number", "description": "Actual effort spent in hours (e.g., 6.0)"},
                 "owner_id": {"type": "integer", "description": "Owner ID (set to null to release ownership)"}
             }, "required": ["task_id"]}),
        Tool(name="complete_task", description="Mark a task as completed",
             inputSchema={"type": "object", "properties": {
                 "task_id": {"type": "integer", "description": "Task ID"}
             }, "required": ["task_id"]}),
        Tool(name="take_ownership", description="Take ownership of a task. Assigns ownership to the authenticated user. Optionally force reassignment if already owned.",
             inputSchema={"type": "object", "properties": {
                 "task_id": {"type": "integer", "description": "Task ID"},
                 "force": {"type": "boolean", "description": "Force reassignment if already owned (default: false)"}
             }, "required": ["task_id"]}),
        Tool(name="delete_task", description="Delete a task",
             inputSchema={"type": "object", "properties": {
                 "task_id": {"type": "integer", "description": "Task ID"}
             }, "required": ["task_id"]}),
        Tool(name="list_comments", description="List all comments for a task",
             inputSchema={"type": "object", "properties": {
                 "task_id": {"type": "integer", "description": "Task ID"}
             }, "required": ["task_id"]}),
        Tool(name="add_comment", description="Add a comment to a task",
             inputSchema={"type": "object", "properties": {
                 "task_id": {"type": "integer", "description": "Task ID"},
                 "content": {"type": "string", "description": "Comment content"},
                 "author_id": {"type": "integer", "description": "Author ID (optional)"}
             }, "required": ["task_id", "content"]}),
        Tool(name="delete_comment", description="Delete a comment",
             inputSchema={"type": "object", "properties": {
                 "comment_id": {"type": "integer", "description": "Comment ID"}
             }, "required": ["comment_id"]}),
        Tool(name="list_users", description="List all users (admin only). Returns users with role, email, and activity status.",
             inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="get_current_user", description="Get the currently authenticated user's information",
             inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="list_authors", description="DEPRECATED: Use list_users instead. Alias for backward compatibility.",
             inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="create_user", description="Create a new user (admin only). Requires admin privileges to execute.",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string", "description": "User's full name"},
                 "email": {"type": "string", "description": "Unique email address"},
                 "password": {"type": "string", "description": "Password (minimum 8 characters)"},
                 "role": {"type": "string", "enum": ["admin", "editor", "viewer"], "description": "User role (default: editor)"}
             }, "required": ["name", "email", "password"]}),
        Tool(name="get_stats", description="Get overall task tracker statistics",
             inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="get_task_events", description="Get timeline of events for a task with optional filtering",
             inputSchema={"type": "object", "properties": {
                 "task_id": {"type": "integer", "description": "Task ID"},
                 "event_type": {"type": "string", "description": "Filter by event type (optional)"},
                 "limit": {"type": "integer", "description": "Max events to return (default: 100, max: 500)"},
                 "offset": {"type": "integer", "description": "Pagination offset (default: 0)"}
             }, "required": ["task_id"]}),
        Tool(name="get_project_events", description="Get timeline of events across all tasks in a project",
             inputSchema={"type": "object", "properties": {
                 "project_id": {"type": "integer", "description": "Project ID"},
                 "event_type": {"type": "string", "description": "Filter by event type (optional)"},
                 "limit": {"type": "integer", "description": "Max events to return (default: 100, max: 500)"},
                 "offset": {"type": "integer", "description": "Pagination offset (default: 0)"}
             }, "required": ["project_id"]}),
        Tool(name="bulk_update_tasks", description="Update multiple tasks in a single transaction",
             inputSchema={"type": "object", "properties": {
                 "task_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of task IDs to update"},
                 "updates": {"type": "object", "properties": {
                     "title": {"type": "string", "description": "New task title"},
                     "description": {"type": "string", "description": "New task description"},
                     "tag": {"type": "string", "enum": ["bug", "feature", "idea"], "description": "New task tag"},
                     "priority": {"type": "string", "enum": ["P0", "P1"], "description": "New task priority"},
                     "status": {"type": "string", "enum": ["backlog", "todo", "in_progress", "blocked", "review", "done"], "description": "New task status"},
                     "owner_id": {"type": ["integer", "null"], "description": "Owner ID (set to null to release ownership)"},
                     "parent_task_id": {"type": ["integer", "null"], "description": "Parent task ID for subtasks (set to null to clear parent)"}
                 }, "description": "Fields to update (all optional)"},
                 "actor_id": {"type": "integer", "description": "Actor ID for event tracking (optional)"}
             }, "required": ["task_ids", "updates"]}),
        Tool(name="bulk_take_ownership", description="Take ownership of multiple tasks at once. Assigns ownership to the authenticated user.",
             inputSchema={"type": "object", "properties": {
                 "task_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of task IDs to claim"},
                 "force": {"type": "boolean", "description": "Force reassignment if already owned (default: false)"}
             }, "required": ["task_ids"]}),
        Tool(name="bulk_delete_tasks", description="Delete multiple tasks in a single transaction (cascades to subtasks)",
             inputSchema={"type": "object", "properties": {
                 "task_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of task IDs to delete"},
                 "actor_id": {"type": "integer", "description": "Actor ID for event tracking (optional)"}
             }, "required": ["task_ids"]}),
        Tool(name="bulk_create_tasks", description="Create multiple tasks in a single transaction",
             inputSchema={"type": "object", "properties": {
                 "tasks": {"type": "array", "items": {
                     "type": "object",
                     "properties": {
                         "project_id": {"type": "integer", "description": "Project ID"},
                         "title": {"type": "string", "description": "Task title"},
                         "description": {"type": "string", "description": "Task description"},
                         "tag": {"type": "string", "enum": ["bug", "feature", "idea"], "description": "Task tag"},
                         "priority": {"type": "string", "enum": ["P0", "P1"], "description": "Task priority"},
                         "status": {"type": "string", "enum": ["backlog", "todo", "in_progress", "blocked", "review", "done"], "description": "Task status"},
                         "author_id": {"type": "integer", "description": "Author ID (optional)"},
                         "owner_id": {"type": "integer", "description": "Owner ID (optional)"},
                         "parent_task_id": {"type": "integer", "description": "Parent task ID for subtasks (optional)"}
                     },
                     "required": ["project_id", "title"]
                 }, "description": "List of tasks to create"},
                 "actor_id": {"type": "integer", "description": "Actor ID for event tracking (optional)"}
             }, "required": ["tasks"]}),
        Tool(name="bulk_add_dependencies", description="Add multiple task dependencies (blocking relationships) in a single transaction",
             inputSchema={"type": "object", "properties": {
                 "dependencies": {"type": "array", "items": {
                     "type": "object",
                     "properties": {
                         "blocking_task_id": {"type": "integer", "description": "Task that blocks another"},
                         "blocked_task_id": {"type": "integer", "description": "Task being blocked"}
                     },
                     "required": ["blocking_task_id", "blocked_task_id"]
                 }, "description": "List of dependencies to create"},
                 "actor_id": {"type": "integer", "description": "Actor ID for event tracking (optional)"}
             }, "required": ["dependencies"]})
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    result: dict = {}

    if name == "list_projects":
        result = await api_request("GET", "/api/projects")
    elif name == "create_project":
        data = {"name": arguments["name"]}
        if "description" in arguments: data["description"] = arguments["description"]
        if "author_id" in arguments: data["author_id"] = arguments["author_id"]
        if "team_id" in arguments: data["team_id"] = arguments["team_id"]
        result = await api_request("POST", "/api/projects", data)
    elif name == "get_project":
        result = await api_request("GET", f"/api/projects/{arguments['project_id']}")
    elif name == "get_project_stats":
        result = await api_request("GET", f"/api/projects/{arguments['project_id']}/stats")
    elif name == "update_project":
        data = {}
        if "name" in arguments: data["name"] = arguments["name"]
        if "description" in arguments: data["description"] = arguments["description"]
        result = await api_request("PUT", f"/api/projects/{arguments['project_id']}", data)
    elif name == "delete_project":
        result = await api_request("DELETE", f"/api/projects/{arguments['project_id']}")

    elif name == "list_assignable_users":
        project_id = arguments["project_id"]
        result = await api_request("GET", f"/api/projects/{project_id}/assignable-users")

    elif name == "transfer_project_team":
        project_id = arguments["project_id"]
        team_id = arguments["team_id"]  # Required field - fail fast if missing
        result = await api_request("PUT", f"/api/projects/{project_id}/transfer", {"team_id": team_id})

    # Team Management
    elif name == "list_teams":
        result = await api_request("GET", "/api/teams")
    elif name == "create_team":
        data = {"name": arguments["name"]}
        if "description" in arguments:
            data["description"] = arguments["description"]
        result = await api_request("POST", "/api/teams", data)
    elif name == "get_team":
        result = await api_request("GET", f"/api/teams/{arguments['team_id']}")
    elif name == "update_team":
        data = {}
        if "name" in arguments:
            data["name"] = arguments["name"]
        if "description" in arguments:
            data["description"] = arguments["description"]
        result = await api_request("PUT", f"/api/teams/{arguments['team_id']}", data)
    elif name == "delete_team":
        result = await api_request("DELETE", f"/api/teams/{arguments['team_id']}")

    # Team Member Management
    elif name == "list_team_members":
        result = await api_request("GET", f"/api/teams/{arguments['team_id']}/members")
    elif name == "add_team_member":
        data = {"user_id": arguments["user_id"]}
        if "role" in arguments:
            data["role"] = arguments["role"]
        result = await api_request("POST", f"/api/teams/{arguments['team_id']}/members", data)
    elif name == "update_team_member":
        data = {"role": arguments["role"]}
        result = await api_request("PUT", f"/api/teams/{arguments['team_id']}/members/{arguments['user_id']}", data)
    elif name == "remove_team_member":
        result = await api_request("DELETE", f"/api/teams/{arguments['team_id']}/members/{arguments['user_id']}")

    elif name == "list_tasks":
        # Validate project_id is provided
        if "project_id" not in arguments or arguments["project_id"] is None:
            result = {
                "error": "project_id is required",
                "message": """ERROR: project_id is required. Please:
1. Check CLAUDE.md for your project assignment
2. Call list_projects to see available projects
3. Choose the appropriate project
4. Call list_tasks with project_id parameter

Example: list_tasks(project_id=4, status='todo', limit=10)"""
            }
        else:
            params = {}
            for k in ["project_id", "status", "priority", "tag", "offset", "q", "sort_by", "due_before", "due_after", "overdue"]:
                if k in arguments: params[k] = arguments[k]

            # Only pass limit if explicitly provided (matches backend opt-in behavior)
            if "limit" in arguments:
                params["limit"] = arguments["limit"]

            if "owner_id" in arguments:
                # Special handling: 0 means filter for NULL owner_id
                params["owner_id"] = None if arguments["owner_id"] == 0 else arguments["owner_id"]
            result = await api_request("GET", "/api/tasks", params)
    elif name == "list_actionable_tasks":
        # Validate project_id is provided
        if "project_id" not in arguments or arguments["project_id"] is None:
            result = {
                "error": "project_id is required",
                "message": """ERROR: project_id is required. Please:
1. Check CLAUDE.md for your project assignment
2. Call list_projects to see available projects
3. Choose the appropriate project
4. Call list_actionable_tasks with project_id parameter

Example: list_actionable_tasks(project_id=4, priority='P0', limit=10)"""
            }
        else:
            params = {}
            for k in ["project_id", "priority", "tag", "offset"]:
                if k in arguments: params[k] = arguments[k]

            # Only pass limit if explicitly provided (matches backend opt-in behavior)
            if "limit" in arguments:
                params["limit"] = arguments["limit"]

            if "owner_id" in arguments:
                # Special handling: 0 means filter for NULL owner_id
                params["owner_id"] = None if arguments["owner_id"] == 0 else arguments["owner_id"]
            result = await api_request("GET", "/api/tasks/actionable", params)
    elif name == "list_overdue_tasks":
        params = {}
        for k in ["project_id", "limit", "offset"]:
            if k in arguments:
                params[k] = arguments[k]
        result = await api_request("GET", "/api/tasks/overdue", params)
    elif name == "list_upcoming_tasks":
        params = {}
        for k in ["project_id", "days", "limit", "offset"]:
            if k in arguments:
                params[k] = arguments[k]
        result = await api_request("GET", "/api/tasks/upcoming", params)
    elif name == "search":
        params = {"q": arguments["q"]}

        # Add optional filters
        for k in ["project_id", "status", "priority", "tag", "limit"]:
            if k in arguments:
                params[k] = arguments[k]

        # Handle search_in array - convert to comma-separated string
        if "search_in" in arguments and arguments["search_in"]:
            params["search_in"] = ",".join(arguments["search_in"])

        # Handle owner_id with special 0 => None conversion
        if "owner_id" in arguments:
            params["owner_id"] = None if arguments["owner_id"] == 0 else arguments["owner_id"]

        result = await api_request("GET", "/api/search", params)
    elif name == "create_task":
        data = {"project_id": arguments["project_id"], "title": arguments["title"]}
        for k in ["description", "tag", "priority", "due_date", "estimated_hours", "author_id", "owner_id"]:
            if k in arguments: data[k] = arguments[k]
        result = await api_request("POST", "/api/tasks", data)
    elif name == "get_task":
        result = await api_request("GET", f"/api/tasks/{arguments['task_id']}")
    elif name == "update_task":
        data = {k: arguments[k] for k in ["title", "description", "tag", "priority", "status", "due_date", "estimated_hours", "actual_hours", "owner_id"] if k in arguments}
        result = await api_request("PUT", f"/api/tasks/{arguments['task_id']}", data)
    elif name == "complete_task":
        result = await api_request("PUT", f"/api/tasks/{arguments['task_id']}", {"status": "done"})
    elif name == "take_ownership":
        data = {"force": arguments.get("force", False)}
        result = await api_request("POST", f"/api/tasks/{arguments['task_id']}/take-ownership", data)
    elif name == "delete_task":
        result = await api_request("DELETE", f"/api/tasks/{arguments['task_id']}")
    elif name == "list_comments":
        result = await api_request("GET", f"/api/tasks/{arguments['task_id']}/comments")
    elif name == "add_comment":
        data = {"content": arguments["content"]}
        if "author_id" in arguments: data["author_id"] = arguments["author_id"]
        result = await api_request("POST", f"/api/tasks/{arguments['task_id']}/comments", data)
    elif name == "delete_comment":
        result = await api_request("DELETE", f"/api/comments/{arguments['comment_id']}")
    elif name == "list_users":
        result = await api_request("GET", "/api/users")
    elif name == "get_current_user":
        result = await api_request("GET", "/api/auth/me")
    elif name == "list_authors":
        # Backward compatibility alias - returns original array shape
        # Deprecation warning logged to stderr (not in response to preserve API contract)
        import sys
        print("WARNING: list_authors is deprecated, use list_users instead", file=sys.stderr)
        result = await api_request("GET", "/api/users")
    elif name == "create_user":
        # Validate required fields exist
        required_fields = ["name", "email", "password"]
        missing_fields = [field for field in required_fields if field not in arguments]
        if missing_fields:
            result = {
                "error": "Missing required fields",
                "detail": f"Required fields missing: {', '.join(missing_fields)}"
            }
        else:
            # Validate role
            role = arguments.get("role", "editor")
            valid_roles = ["admin", "editor", "viewer"]
            if role not in valid_roles:
                result = {
                    "error": "Invalid role",
                    "detail": f"Role must be one of: {', '.join(valid_roles)}"
                }
            # Validate password length
            elif len(arguments["password"]) < 8:
                result = {
                    "error": "Password too short",
                    "detail": "Password must be at least 8 characters"
                }
            else:
                data = {
                    "name": arguments["name"],
                    "email": arguments["email"],
                    "password": arguments["password"],
                    "role": role
                }
                result = await api_request("POST", "/api/users", data)
    elif name == "get_stats":
        result = await api_request("GET", "/api/stats")
    elif name == "get_task_events":
        params = {}
        if "event_type" in arguments:
            params["event_type"] = arguments["event_type"]
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        if "offset" in arguments:
            params["offset"] = arguments["offset"]
        result = await api_request("GET", f"/api/tasks/{arguments['task_id']}/events", params)
    elif name == "get_project_events":
        params = {}
        if "event_type" in arguments:
            params["event_type"] = arguments["event_type"]
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        if "offset" in arguments:
            params["offset"] = arguments["offset"]
        result = await api_request("GET", f"/api/projects/{arguments['project_id']}/events", params)
    elif name == "bulk_update_tasks":
        data = {"task_ids": arguments["task_ids"], "updates": arguments["updates"]}
        if "actor_id" in arguments:
            data["actor_id"] = arguments["actor_id"]
        result = await api_request("POST", "/api/tasks/bulk-update", data)
    elif name == "bulk_take_ownership":
        data = {"task_ids": arguments["task_ids"]}
        if "force" in arguments:
            data["force"] = arguments["force"]
        result = await api_request("POST", "/api/tasks/bulk-take-ownership", data)
    elif name == "bulk_delete_tasks":
        data = {"task_ids": arguments["task_ids"]}
        if "actor_id" in arguments:
            data["actor_id"] = arguments["actor_id"]
        result = await api_request("POST", "/api/tasks/bulk-delete", data)
    elif name == "bulk_create_tasks":
        data = {"tasks": arguments["tasks"]}
        if "actor_id" in arguments:
            data["actor_id"] = arguments["actor_id"]
        result = await api_request("POST", "/api/tasks/bulk-create", data)
    elif name == "bulk_add_dependencies":
        data = {"dependencies": arguments["dependencies"]}
        if "actor_id" in arguments:
            data["actor_id"] = arguments["actor_id"]
        result = await api_request("POST", "/api/tasks/bulk-add-dependencies", data)
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def main():
    # Validate API key before starting server
    validate_api_key()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
