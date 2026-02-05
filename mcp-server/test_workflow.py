#!/usr/bin/env python3
"""Test complete task workflow"""
import asyncio
import json
from stdio_server import call_tool

async def test_task_workflow():
    """Test creating, updating, and completing a task with comments"""
    print("\n" + "=" * 60)
    print("Testing Complete Task Management Workflow")
    print("=" * 60)

    # Step 1: Create a new task
    print("\n[STEP 1] Creating a new task...")
    result = await call_tool("create_task", {
        "project_id": 1,
        "title": "Test MCP Integration",
        "description": "Verify MCP server can create and manage tasks",
        "tag": "feature",
        "priority": "P0",
        "author_id": 3  # The MCP Test User we created
    })
    task = json.loads(result[0].text)
    task_id = task['id']
    print(f"✅ Created task ID {task_id}: {task['title']}")

    # Step 2: Add a comment to the task
    print("\n[STEP 2] Adding a comment to the task...")
    result = await call_tool("add_comment", {
        "task_id": task_id,
        "content": "This task was created by the MCP server test!",
        "author_id": 3
    })
    comment = json.loads(result[0].text)
    print(f"✅ Added comment ID {comment['id']}")

    # Step 3: Get task details with comments
    print("\n[STEP 3] Retrieving task details...")
    result = await call_tool("get_task", {"task_id": task_id})
    task_details = json.loads(result[0].text)
    print(f"✅ Task: {task_details['title']}")
    print(f"   Status: {task_details['status']}")
    print(f"   Comments: {len(task_details['comments'])}")

    # Step 4: Update the task
    print("\n[STEP 4] Updating task priority...")
    result = await call_tool("update_task", {
        "task_id": task_id,
        "priority": "P1"
    })
    updated_task = json.loads(result[0].text)
    print(f"✅ Updated priority: {updated_task['priority']}")

    # Step 5: Complete the task
    print("\n[STEP 5] Marking task as completed...")
    result = await call_tool("complete_task", {"task_id": task_id})
    completed_task = json.loads(result[0].text)
    print(f"✅ Task status: {completed_task['status']}")

    # Step 6: Get updated stats
    print("\n[STEP 6] Checking updated statistics...")
    result = await call_tool("get_stats", {})
    stats = json.loads(result[0].text)
    print(f"✅ Updated Stats:")
    print(f"   Total Tasks: {stats['total_tasks']}")
    print(f"   Pending: {stats['pending_tasks']}")
    print(f"   Completed: {stats['completed_tasks']}")
    print(f"   Completion Rate: {stats['completion_rate']}%")

    print("\n" + "=" * 60)
    print("✅ All workflow steps completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_task_workflow())
