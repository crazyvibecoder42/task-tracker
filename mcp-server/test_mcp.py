#!/usr/bin/env python3
"""Test script for the Task Tracker MCP Server"""
import asyncio
import json
import sys
from stdio_server import server, call_tool

async def test_mcp_server():
    """Test various MCP server operations"""
    print("=" * 60)
    print("Testing Task Tracker MCP Server")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    # Test 1: List Authors
    print("\n[TEST 1] Listing all authors...")
    try:
        result = await call_tool("list_authors", {})
        data = json.loads(result[0].text)
        if "error" in data:
            print(f"❌ FAILED: {data['error']}")
            tests_failed += 1
        else:
            print(f"✅ SUCCESS: Found {len(data)} authors")
            for author in data:
                print(f"   - {author['name']} ({author['email']})")
            tests_passed += 1
    except Exception as e:
        print(f"❌ FAILED: {e}")
        tests_failed += 1

    # Test 2: List Projects (create_author removed - use admin UI or /api/auth/register)
    print("\n[TEST 2] Listing all projects...")
    try:
        result = await call_tool("list_projects", {})
        data = json.loads(result[0].text)
        if "error" in data:
            print(f"❌ FAILED: {data['error']}")
            tests_failed += 1
        else:
            print(f"✅ SUCCESS: Found {len(data)} projects")
            for project in data:
                print(f"   - {project['name']}")
            tests_passed += 1
    except Exception as e:
        print(f"❌ FAILED: {e}")
        tests_failed += 1

    # Test 3: List Tasks (requires project_id - use project 1 from sample data)
    print("\n[TEST 3] Listing tasks in project 1...")
    try:
        result = await call_tool("list_tasks", {"project_id": 1})
        data = json.loads(result[0].text)
        # API returns a list directly, not {"tasks": [...]}
        if isinstance(data, dict) and "error" in data:
            print(f"❌ FAILED: {data['error']}")
            tests_failed += 1
        elif isinstance(data, list):
            tasks = data
            print(f"✅ SUCCESS: Found {len(tasks)} tasks")
            for task in tasks:
                print(f"   - [{task['priority']}] {task['title']} ({task['status']})")
            tests_passed += 1
        else:
            print(f"❌ FAILED: Unexpected response type: {type(data)}")
            tests_failed += 1
    except Exception as e:
        print(f"❌ FAILED: {e}")
        tests_failed += 1

    # Test 4: Get Overall Stats
    print("\n[TEST 4] Getting overall statistics...")
    try:
        result = await call_tool("get_stats", {})
        data = json.loads(result[0].text)
        if "error" in data:
            print(f"❌ FAILED: {data['error']}")
            tests_failed += 1
        else:
            print(f"✅ SUCCESS: Retrieved stats")
            print(f"   - Total Projects: {data['total_projects']}")
            print(f"   - Total Tasks: {data['total_tasks']}")
            print(f"   - Pending Tasks: {data['pending_tasks']}")
            print(f"   - Completed Tasks: {data['completed_tasks']}")
            print(f"   - Completion Rate: {data['completion_rate']}%")
            tests_passed += 1
    except Exception as e:
        print(f"❌ FAILED: {e}")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"Test Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)

    return tests_failed == 0

if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    sys.exit(0 if success else 1)
