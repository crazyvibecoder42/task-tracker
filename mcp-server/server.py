#!/usr/bin/env python3
"""
Task Tracker MCP Server

This MCP server provides programmatic access to the Task Tracker system.
It runs on port 6000 using SSE transport for HTTP-based connections.
"""

import os
import json
import asyncio
from typing import Any, Optional
import httpx
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
import uvicorn
from mcp.types import Tool, TextContent

# Configuration
API_BASE_URL = os.getenv("TASK_TRACKER_API_URL", "http://localhost:6001")
MCP_PORT = int(os.getenv("MCP_PORT", "6000"))

# Initialize MCP server
server = Server("task-tracker")

# HTTP client for API calls
http_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0)
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
        # Project tools
        Tool(
            name="list_projects",
            description="List all projects in the task tracker",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="create_project",
            description="Create a new project",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                    "description": {"type": "string", "description": "Project description"},
                    "author_id": {"type": "integer", "description": "Author ID (optional)"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="get_project",
            description="Get a project by ID with all its tasks",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "Project ID"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_project_stats",
            description="Get statistics for a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "Project ID"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="update_project",
            description="Update a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "Project ID"},
                    "name": {"type": "string", "description": "New project name"},
                    "description": {"type": "string", "description": "New project description"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="delete_project",
            description="Delete a project and all its tasks",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "Project ID"}
                },
                "required": ["project_id"]
            }
        ),

        # Task tools
        Tool(
            name="list_tasks",
            description="List tasks with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "Filter by project ID"},
                    "status": {"type": "string", "enum": ["pending", "completed"], "description": "Filter by status"},
                    "priority": {"type": "string", "enum": ["P0", "P1"], "description": "Filter by priority"},
                    "tag": {"type": "string", "enum": ["bug", "feature", "idea"], "description": "Filter by tag"},
                    "owner_id": {"type": "integer", "description": "Filter by owner ID (use 0 for unassigned tasks)"}
                },
                "required": []
            }
        ),
        Tool(
            name="create_task",
            description="Create a new task in a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "Project ID"},
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "tag": {"type": "string", "enum": ["bug", "feature", "idea"], "description": "Task tag (default: feature)"},
                    "priority": {"type": "string", "enum": ["P0", "P1"], "description": "Task priority (default: P1)"},
                    "author_id": {"type": "integer", "description": "Author ID (optional)"},
                    "owner_id": {"type": "integer", "description": "Owner ID (optional)"},
                    "parent_task_id": {"type": "integer", "description": "Parent task ID to create this as a subtask (optional)"}
                },
                "required": ["project_id", "title"]
            }
        ),
        Tool(
            name="get_task",
            description="Get a task by ID with all comments",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"}
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="update_task",
            description="Update a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"},
                    "title": {"type": "string", "description": "New task title"},
                    "description": {"type": "string", "description": "New task description"},
                    "tag": {"type": "string", "enum": ["bug", "feature", "idea"], "description": "New task tag"},
                    "priority": {"type": "string", "enum": ["P0", "P1"], "description": "New task priority"},
                    "status": {"type": "string", "enum": ["pending", "completed"], "description": "New task status"},
                    "owner_id": {"type": "integer", "description": "Owner ID (set to null to release ownership)"},
                    "parent_task_id": {"type": "integer", "description": "Parent task ID to make this a subtask (optional)"}
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="complete_task",
            description="Mark a task as completed",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"}
                },
                "required": ["task_id"]
            }
        ),
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
        ),
        Tool(
            name="delete_task",
            description="Delete a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"}
                },
                "required": ["task_id"]
            }
        ),

        # Task dependency and subtask tools
        Tool(
            name="get_task_subtasks",
            description="List all subtasks of a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"}
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="get_task_dependencies",
            description="Get full dependency graph for a task including subtasks, blocking tasks, and blocked tasks",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"}
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="add_task_dependency",
            description="Add a blocking relationship between tasks (blocking_task must be completed before task can start)",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID that will be blocked"},
                    "blocking_task_id": {"type": "integer", "description": "Task ID that blocks the first task"}
                },
                "required": ["task_id", "blocking_task_id"]
            }
        ),
        Tool(
            name="remove_task_dependency",
            description="Remove a blocking relationship between tasks",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"},
                    "blocking_task_id": {"type": "integer", "description": "Blocking task ID to remove"}
                },
                "required": ["task_id", "blocking_task_id"]
            }
        ),
        Tool(
            name="get_actionable_tasks",
            description="Get tasks that are not blocked and can be worked on immediately. This is critical for identifying what work can be done right now.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "Filter by project ID (optional)"},
                    "owner_id": {"type": "integer", "description": "Filter by owner ID (optional)"},
                    "priority": {"type": "string", "enum": ["P0", "P1"], "description": "Filter by priority (optional)"},
                    "tag": {"type": "string", "enum": ["bug", "feature", "idea"], "description": "Filter by tag (optional)"}
                },
                "required": []
            }
        ),
        Tool(
            name="get_task_progress",
            description="Get completion percentage for a task based on its subtasks",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"}
                },
                "required": ["task_id"]
            }
        ),

        # Comment tools
        Tool(
            name="list_comments",
            description="List all comments for a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"}
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="add_comment",
            description="Add a comment to a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"},
                    "content": {"type": "string", "description": "Comment content"},
                    "author_id": {"type": "integer", "description": "Author ID (optional)"}
                },
                "required": ["task_id", "content"]
            }
        ),
        Tool(
            name="delete_comment",
            description="Delete a comment",
            inputSchema={
                "type": "object",
                "properties": {
                    "comment_id": {"type": "integer", "description": "Comment ID"}
                },
                "required": ["comment_id"]
            }
        ),

        # Author tools
        Tool(
            name="list_authors",
            description="List all authors/users",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="create_author",
            description="Create a new author/user",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Author name"},
                    "email": {"type": "string", "description": "Author email"}
                },
                "required": ["name", "email"]
            }
        ),

        # Stats tool
        Tool(
            name="get_stats",
            description="Get overall task tracker statistics",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    result: dict = {}

    # Project tools
    if name == "list_projects":
        result = await api_request("GET", "/api/projects")

    elif name == "create_project":
        data = {"name": arguments["name"]}
        if "description" in arguments:
            data["description"] = arguments["description"]
        if "author_id" in arguments:
            data["author_id"] = arguments["author_id"]
        result = await api_request("POST", "/api/projects", data)

    elif name == "get_project":
        result = await api_request("GET", f"/api/projects/{arguments['project_id']}")

    elif name == "get_project_stats":
        result = await api_request("GET", f"/api/projects/{arguments['project_id']}/stats")

    elif name == "update_project":
        data = {}
        if "name" in arguments:
            data["name"] = arguments["name"]
        if "description" in arguments:
            data["description"] = arguments["description"]
        result = await api_request("PUT", f"/api/projects/{arguments['project_id']}", data)

    elif name == "delete_project":
        result = await api_request("DELETE", f"/api/projects/{arguments['project_id']}")

    # Task tools
    elif name == "list_tasks":
        params = {}
        if "project_id" in arguments:
            params["project_id"] = arguments["project_id"]
        if "status" in arguments:
            params["status"] = arguments["status"]
        if "priority" in arguments:
            params["priority"] = arguments["priority"]
        if "tag" in arguments:
            params["tag"] = arguments["tag"]
        if "owner_id" in arguments:
            # Special handling: 0 means filter for NULL owner_id
            params["owner_id"] = None if arguments["owner_id"] == 0 else arguments["owner_id"]
        result = await api_request("GET", "/api/tasks", params)

    elif name == "create_task":
        data = {
            "project_id": arguments["project_id"],
            "title": arguments["title"]
        }
        if "description" in arguments:
            data["description"] = arguments["description"]
        if "tag" in arguments:
            data["tag"] = arguments["tag"]
        if "priority" in arguments:
            data["priority"] = arguments["priority"]
        if "author_id" in arguments:
            data["author_id"] = arguments["author_id"]
        if "owner_id" in arguments:
            data["owner_id"] = arguments["owner_id"]
        if "parent_task_id" in arguments:
            data["parent_task_id"] = arguments["parent_task_id"]
        result = await api_request("POST", "/api/tasks", data)

    elif name == "get_task":
        result = await api_request("GET", f"/api/tasks/{arguments['task_id']}")

    elif name == "update_task":
        data = {}
        for field in ["title", "description", "tag", "priority", "status", "owner_id", "parent_task_id"]:
            if field in arguments:
                data[field] = arguments[field]
        result = await api_request("PUT", f"/api/tasks/{arguments['task_id']}", data)

    elif name == "complete_task":
        result = await api_request("PUT", f"/api/tasks/{arguments['task_id']}", {"status": "completed"})

    elif name == "take_ownership":
        data = {
            "author_id": arguments["author_id"],
            "force": arguments.get("force", False)
        }
        result = await api_request("POST", f"/api/tasks/{arguments['task_id']}/take-ownership", data)

    elif name == "delete_task":
        result = await api_request("DELETE", f"/api/tasks/{arguments['task_id']}")

    # Task dependency and subtask tools
    elif name == "get_task_subtasks":
        result = await api_request("GET", f"/api/tasks/{arguments['task_id']}/subtasks")

    elif name == "get_task_dependencies":
        result = await api_request("GET", f"/api/tasks/{arguments['task_id']}/dependencies")

    elif name == "add_task_dependency":
        data = {"blocking_task_id": arguments["blocking_task_id"]}
        result = await api_request("POST", f"/api/tasks/{arguments['task_id']}/dependencies", data)

    elif name == "remove_task_dependency":
        result = await api_request("DELETE", f"/api/tasks/{arguments['task_id']}/dependencies/{arguments['blocking_task_id']}")

    elif name == "get_actionable_tasks":
        params = {}
        if "project_id" in arguments:
            params["project_id"] = arguments["project_id"]
        if "owner_id" in arguments:
            params["owner_id"] = arguments["owner_id"]
        if "priority" in arguments:
            params["priority"] = arguments["priority"]
        if "tag" in arguments:
            params["tag"] = arguments["tag"]
        result = await api_request("GET", "/api/tasks/actionable", params)

    elif name == "get_task_progress":
        result = await api_request("GET", f"/api/tasks/{arguments['task_id']}/progress")

    # Comment tools
    elif name == "list_comments":
        result = await api_request("GET", f"/api/tasks/{arguments['task_id']}/comments")

    elif name == "add_comment":
        data = {"content": arguments["content"]}
        if "author_id" in arguments:
            data["author_id"] = arguments["author_id"]
        result = await api_request("POST", f"/api/tasks/{arguments['task_id']}/comments", data)

    elif name == "delete_comment":
        result = await api_request("DELETE", f"/api/comments/{arguments['comment_id']}")

    # Author tools
    elif name == "list_authors":
        result = await api_request("GET", "/api/authors")

    elif name == "create_author":
        data = {
            "name": arguments["name"],
            "email": arguments["email"]
        }
        result = await api_request("POST", "/api/authors", data)

    # Stats tool
    elif name == "get_stats":
        result = await api_request("GET", "/api/stats")

    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


# SSE Transport setup
sse = SseServerTransport("/messages/")

async def handle_sse(request):
    """Handle SSE connections."""
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0], streams[1], server.create_initialization_options()
        )

async def handle_messages(request):
    """Handle POST messages."""
    await sse.handle_post_message(request.scope, request.receive, request._send)

async def health_check(request):
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "server": "task-tracker-mcp", "port": MCP_PORT})

# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Route("/sse", handle_sse, methods=["GET"]),
        Route("/messages/", handle_messages, methods=["POST"]),
    ],
)

if __name__ == "__main__":
    print(f"🚀 Task Tracker MCP Server starting on port {MCP_PORT}")
    print(f"📡 SSE endpoint: http://localhost:{MCP_PORT}/sse")
    print(f"💬 Messages endpoint: http://localhost:{MCP_PORT}/messages/")
    print(f"🔗 Backend API: {API_BASE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=MCP_PORT)
