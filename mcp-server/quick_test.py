#!/usr/bin/env python3
"""Quick validation test for bulk endpoints"""
import asyncio
import httpx
import json

API_BASE_URL = "http://localhost:6001"
AUTHOR_ID = 1
PROJECT_ID = 4

async def test_endpoint(name, method, endpoint, payload):
    """Test a single endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    print(f"Endpoint: {method} {endpoint}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
            if method == "POST":
                response = await client.post(endpoint, json=payload)
            else:
                response = await client.get(endpoint)

            print(f"Status: {response.status_code}")

            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")

                if response.status_code == 200:
                    print("✅ PASS - Endpoint working")
                    return data
                else:
                    print(f"⚠️  WARN - Status {response.status_code}")
                    return data
            except:
                print(f"Response text: {response.text[:200]}")
                print("❌ FAIL - Invalid JSON response")
                return None

    except asyncio.TimeoutError:
        print("❌ FAIL - Request timed out")
        return None
    except Exception as e:
        print(f"❌ FAIL - Exception: {e}")
        return None

async def main():
    print("Quick Bulk Operations Endpoint Test")
    print("="*60)

    # Test 1: Bulk Create
    result = await test_endpoint(
        "Bulk Create Tasks",
        "POST",
        "/api/tasks/bulk-create",
        {
            "tasks": [
                {
                    "project_id": PROJECT_ID,
                    "title": "Quick Test Task 1",
                    "description": "Test task",
                    "tag": "feature",
                    "priority": "P1",
                    "author_id": AUTHOR_ID
                }
            ],
            "actor_id": AUTHOR_ID
        }
    )

    created_task_ids = []
    if result and result.get("success"):
        created_task_ids = result.get("task_ids", [])
        print(f"Created task IDs: {created_task_ids}")

    if created_task_ids:
        # Test 2: Bulk Update
        await test_endpoint(
            "Bulk Update Tasks",
            "POST",
            "/api/tasks/bulk-update",
            {
                "task_ids": created_task_ids,
                "updates": {"status": "in_progress"},
                "actor_id": AUTHOR_ID
            }
        )

        # Test 3: Bulk Take Ownership
        await test_endpoint(
            "Bulk Take Ownership",
            "POST",
            "/api/tasks/bulk-take-ownership",
            {
                "task_ids": created_task_ids,
                "author_id": AUTHOR_ID,
                "force": False
            }
        )

        # Test 4: Bulk Add Dependencies (skip - need 2+ tasks)
        if len(created_task_ids) >= 2:
            await test_endpoint(
                "Bulk Add Dependencies",
                "POST",
                "/api/tasks/bulk-add-dependencies",
                {
                    "dependencies": [
                        {
                            "blocking_task_id": created_task_ids[0],
                            "blocked_task_id": created_task_ids[1] if len(created_task_ids) > 1 else created_task_ids[0]
                        }
                    ],
                    "actor_id": AUTHOR_ID
                }
            )

        # Test 5: Bulk Delete
        await test_endpoint(
            "Bulk Delete Tasks",
            "POST",
            "/api/tasks/bulk-delete",
            {
                "task_ids": created_task_ids,
                "actor_id": AUTHOR_ID
            }
        )

    print("\n" + "="*60)
    print("Quick test complete")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
