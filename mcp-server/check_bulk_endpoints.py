#!/usr/bin/env python3
"""
Bulk Operations Endpoint Readiness Checker

This script checks if all bulk operation endpoints are implemented and responding.
Use this to verify when backend implementation is complete and testing can begin.
"""

import asyncio
import httpx
import sys

API_BASE_URL = "http://localhost:6001"

REQUIRED_ENDPOINTS = {
    "/api/tasks/bulk-create": "POST",
    "/api/tasks/bulk-update": "POST",
    "/api/tasks/bulk-take-ownership": "POST",
    "/api/tasks/bulk-delete": "POST",
    "/api/tasks/bulk-add-dependencies": "POST",
}

async def check_endpoint(client: httpx.AsyncClient, path: str, method: str) -> bool:
    """Check if an endpoint exists and responds"""
    try:
        if method == "POST":
            # Send minimal valid request to check if endpoint exists
            # We expect validation errors, not 404
            response = await client.post(path, json={}, timeout=5.0)
            # 404 means endpoint not implemented
            # 422 (validation error) or 400 means endpoint exists but data is invalid
            # 500 might mean endpoint exists but has bugs
            if response.status_code == 404:
                return False
            else:
                return True
        elif method == "GET":
            response = await client.get(path, timeout=5.0)
            return response.status_code != 404
    except httpx.TimeoutException:
        print(f"  ⚠️  Timeout - endpoint may exist but is slow")
        return True  # Assume it exists if we get timeout
    except Exception as e:
        print(f"  ❌ Error checking endpoint: {e}")
        return False

def check_mcp_tools():
    """Check if bulk MCP tools are available"""
    try:
        # Read the stdio_server.py file and check for bulk tool definitions
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_file = os.path.join(script_dir, "stdio_server.py")

        with open(server_file, 'r') as f:
            content = f.read()

        required_tools = [
            "bulk_create_tasks",
            "bulk_update_tasks",
            "bulk_take_ownership",
            "bulk_delete_tasks",
            "bulk_add_dependencies",
        ]

        print("\n📋 MCP Tools Check:")
        all_present = True
        for tool in required_tools:
            # Check if tool is defined in the file
            if f'name="{tool}"' in content or f"name='{tool}'" in content:
                print(f"  ✅ {tool}")
            else:
                print(f"  ❌ {tool} - NOT FOUND")
                all_present = False

        return all_present
    except FileNotFoundError:
        print(f"\n⚠️  Cannot find stdio_server.py")
        return False
    except Exception as e:
        print(f"\n❌ Error checking MCP tools: {e}")
        return False

async def main():
    """Check all bulk operation endpoints and tools"""
    print("=" * 80)
    print("Bulk Operations Readiness Check")
    print("=" * 80)

    # Check backend health
    print("\n🏥 Backend Health Check:")
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            response = await client.get("/health")
            if response.status_code == 200:
                print("  ✅ Backend is running and healthy")
            else:
                print(f"  ❌ Backend responded with status {response.status_code}")
                sys.exit(1)
    except Exception as e:
        print(f"  ❌ Cannot connect to backend: {e}")
        print(f"  Make sure backend is running at {API_BASE_URL}")
        sys.exit(1)

    # Check bulk endpoints
    print("\n🔌 Bulk Endpoints Check:")
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        endpoints_ready = True
        for path, method in REQUIRED_ENDPOINTS.items():
            is_ready = await check_endpoint(client, path, method)
            status = "✅" if is_ready else "❌ NOT IMPLEMENTED"
            print(f"  {status} {method} {path}")
            if not is_ready:
                endpoints_ready = False

    # Check MCP tools
    mcp_tools_ready = check_mcp_tools()

    # Summary
    print("\n" + "=" * 80)
    if endpoints_ready and mcp_tools_ready:
        print("✅ ALL DEPENDENCIES READY - Testing can begin!")
        print("\nRun tests with:")
        print("  cd mcp-server")
        print("  python test_bulk_operations.py")
        return 0
    else:
        print("⏳ DEPENDENCIES NOT READY - Wait for implementation to complete")
        if not endpoints_ready:
            print("\n  Missing: Backend endpoints (Tasks #2-6)")
        if not mcp_tools_ready:
            print("  Missing: MCP tools (Task #7)")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    print("=" * 80)
    sys.exit(exit_code)
