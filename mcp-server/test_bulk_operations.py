#!/usr/bin/env python3
"""
Integration Test Suite for Bulk Operations

This script tests all bulk operation endpoints and MCP tools for the Task Tracker.

Test Coverage:
1. Successful bulk operations (happy path)
2. Validation failures (blocked tasks, circular dependencies, etc.)
3. Transaction rollback on errors
4. Event creation for bulk operations
5. Performance with 100+ tasks
6. MCP tools integration

Requirements:
- Backend running at http://localhost:6001
- Database accessible
- MCP server operational
"""

import asyncio
import json
import sys
import time
import httpx
from typing import List, Dict, Any
from stdio_server import call_tool

# Test configuration
API_BASE_URL = "http://localhost:6001"
AUTHOR_ID = 1  # aman
PROJECT_ID = 4  # Task Tracker Enhancements - AI Agent Features

class BulkOperationTester:
    """Test suite for bulk operations"""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.created_task_ids = []
        self.client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0)

    async def setup(self):
        """Setup test environment"""
        print("\n" + "=" * 80)
        print("BULK OPERATIONS INTEGRATION TEST SUITE")
        print("=" * 80)

        # Check backend health
        print("\n[SETUP] Checking backend health...")
        try:
            response = await self.client.get("/health")
            if response.status_code == 200:
                print("✅ Backend is healthy")
            else:
                print(f"❌ Backend health check failed: {response.status_code}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Cannot connect to backend: {e}")
            sys.exit(1)

    async def teardown(self):
        """Cleanup test data"""
        print("\n[TEARDOWN] Cleaning up test data...")
        # Delete created tasks if any remain
        if self.created_task_ids:
            try:
                # Use bulk delete to clean up
                await self.client.post("/api/tasks/bulk-delete", json={
                    "task_ids": self.created_task_ids,
                    "actor_id": AUTHOR_ID
                })
                print(f"✅ Cleaned up {len(self.created_task_ids)} test tasks")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")

        await self.client.aclose()

        # Print summary
        print("\n" + "=" * 80)
        print(f"TEST SUMMARY: {self.tests_passed} passed, {self.tests_failed} failed")
        print("=" * 80)

    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        if passed:
            print(f"✅ {test_name}")
            if message:
                print(f"   {message}")
            self.tests_passed += 1
        else:
            print(f"❌ {test_name}")
            if message:
                print(f"   {message}")
            self.tests_failed += 1

    # ========================================================================
    # TEST 1: Bulk Create Tasks (Happy Path)
    # ========================================================================

    async def test_bulk_create_happy_path(self):
        """Test successful bulk task creation"""
        print("\n" + "-" * 80)
        print("TEST 1: Bulk Create Tasks (Happy Path)")
        print("-" * 80)

        try:
            tasks = [
                {
                    "project_id": PROJECT_ID,
                    "title": f"Bulk Test Task {i}",
                    "description": f"Test task created in bulk operation {i}",
                    "tag": "feature" if i % 2 == 0 else "bug",
                    "priority": "P0" if i % 3 == 0 else "P1",
                    "author_id": AUTHOR_ID
                }
                for i in range(1, 11)  # Create 10 tasks
            ]

            response = await self.client.post("/api/tasks/bulk-create", json={
                "tasks": tasks,
                "actor_id": AUTHOR_ID
            })

            result = response.json()

            if response.status_code == 200 and result.get("success"):
                created_count = result.get("processed_count", 0)
                task_ids = result.get("task_ids", [])
                self.created_task_ids.extend(task_ids)

                self.log_test(
                    "Bulk Create (Happy Path)",
                    True,
                    f"Created {created_count} tasks: {task_ids}"
                )
                return task_ids
            else:
                self.log_test(
                    "Bulk Create (Happy Path)",
                    False,
                    f"Failed: {result}"
                )
                return []

        except Exception as e:
            self.log_test("Bulk Create (Happy Path)", False, f"Exception: {e}")
            return []

    # ========================================================================
    # TEST 2: Bulk Update Tasks (Happy Path)
    # ========================================================================

    async def test_bulk_update_happy_path(self, task_ids: List[int]):
        """Test successful bulk task update"""
        print("\n" + "-" * 80)
        print("TEST 2: Bulk Update Tasks (Happy Path)")
        print("-" * 80)

        if not task_ids:
            self.log_test("Bulk Update (Happy Path)", False, "No tasks to update")
            return

        try:
            response = await self.client.post("/api/tasks/bulk-update", json={
                "task_ids": task_ids[:5],  # Update first 5 tasks
                "updates": {
                    "status": "in_progress"
                },
                "actor_id": AUTHOR_ID
            })

            result = response.json()

            if response.status_code == 200 and result.get("success"):
                self.log_test(
                    "Bulk Update (Happy Path)",
                    True,
                    f"Updated {result.get('processed_count')} tasks to in_progress"
                )
            else:
                self.log_test(
                    "Bulk Update (Happy Path)",
                    False,
                    f"Failed: {result}"
                )

        except Exception as e:
            self.log_test("Bulk Update (Happy Path)", False, f"Exception: {e}")

    # ========================================================================
    # TEST 3: Bulk Take Ownership (Happy Path)
    # ========================================================================

    async def test_bulk_take_ownership_happy_path(self, task_ids: List[int]):
        """Test successful bulk ownership assignment"""
        print("\n" + "-" * 80)
        print("TEST 3: Bulk Take Ownership (Happy Path)")
        print("-" * 80)

        if not task_ids:
            self.log_test("Bulk Take Ownership (Happy Path)", False, "No tasks available")
            return

        try:
            response = await self.client.post("/api/tasks/bulk-take-ownership", json={
                "task_ids": task_ids[:3],  # Take ownership of first 3
                "author_id": AUTHOR_ID,
                "force": False
            })

            result = response.json()

            if response.status_code == 200 and result.get("success"):
                self.log_test(
                    "Bulk Take Ownership (Happy Path)",
                    True,
                    f"Took ownership of {result.get('processed_count')} tasks"
                )
            else:
                self.log_test(
                    "Bulk Take Ownership (Happy Path)",
                    False,
                    f"Failed: {result}"
                )

        except Exception as e:
            self.log_test("Bulk Take Ownership (Happy Path)", False, f"Exception: {e}")

    # ========================================================================
    # TEST 4: Bulk Add Dependencies (Happy Path)
    # ========================================================================

    async def test_bulk_add_dependencies_happy_path(self, task_ids: List[int]):
        """Test successful bulk dependency creation"""
        print("\n" + "-" * 80)
        print("TEST 4: Bulk Add Dependencies (Happy Path)")
        print("-" * 80)

        if len(task_ids) < 4:
            self.log_test("Bulk Add Dependencies (Happy Path)", False, "Not enough tasks")
            return

        try:
            # Create dependency chain: task_ids[0] blocks task_ids[1], task_ids[1] blocks task_ids[2]
            dependencies = [
                {"blocking_task_id": task_ids[0], "blocked_task_id": task_ids[1]},
                {"blocking_task_id": task_ids[1], "blocked_task_id": task_ids[2]},
                {"blocking_task_id": task_ids[2], "blocked_task_id": task_ids[3]},
            ]

            response = await self.client.post("/api/tasks/bulk-add-dependencies", json={
                "dependencies": dependencies,
                "actor_id": AUTHOR_ID
            })

            result = response.json()

            if response.status_code == 200 and result.get("success"):
                self.log_test(
                    "Bulk Add Dependencies (Happy Path)",
                    True,
                    f"Created {result.get('processed_count')} dependencies"
                )
            else:
                self.log_test(
                    "Bulk Add Dependencies (Happy Path)",
                    False,
                    f"Failed: {result}"
                )

        except Exception as e:
            self.log_test("Bulk Add Dependencies (Happy Path)", False, f"Exception: {e}")

    # ========================================================================
    # TEST 5: Bulk Delete (Happy Path)
    # ========================================================================

    async def test_bulk_delete_happy_path(self, task_ids: List[int]):
        """Test successful bulk task deletion"""
        print("\n" + "-" * 80)
        print("TEST 5: Bulk Delete Tasks (Happy Path)")
        print("-" * 80)

        if len(task_ids) < 7:
            self.log_test("Bulk Delete (Happy Path)", False, "Not enough tasks")
            return

        try:
            # Delete some tasks (not all, we need some for other tests)
            delete_ids = task_ids[7:10]

            response = await self.client.post("/api/tasks/bulk-delete", json={
                "task_ids": delete_ids,
                "actor_id": AUTHOR_ID
            })

            result = response.json()

            if response.status_code == 200 and result.get("success"):
                deleted_count = result.get("deleted_count", 0)
                # Remove from our tracking list
                for tid in delete_ids:
                    if tid in self.created_task_ids:
                        self.created_task_ids.remove(tid)

                self.log_test(
                    "Bulk Delete (Happy Path)",
                    True,
                    f"Deleted {deleted_count} tasks"
                )
            else:
                self.log_test(
                    "Bulk Delete (Happy Path)",
                    False,
                    f"Failed: {result}"
                )

        except Exception as e:
            self.log_test("Bulk Delete (Happy Path)", False, f"Exception: {e}")

    # ========================================================================
    # TEST 6: Validation - Update Blocked Tasks
    # ========================================================================

    async def test_validation_blocked_tasks(self, task_ids: List[int]):
        """Test that blocked tasks cannot be marked as done"""
        print("\n" + "-" * 80)
        print("TEST 6: Validation - Cannot Complete Blocked Tasks")
        print("-" * 80)

        if len(task_ids) < 4:
            self.log_test("Validation - Blocked Tasks", False, "Not enough tasks")
            return

        try:
            # Try to mark task_ids[3] as done (it's blocked by task_ids[2])
            response = await self.client.post("/api/tasks/bulk-update", json={
                "task_ids": [task_ids[3]],
                "updates": {"status": "done"},
                "actor_id": AUTHOR_ID
            })

            result = response.json()

            # Should fail because task is blocked
            if not result.get("success") and result.get("errors"):
                errors = result.get("errors", [])
                has_blocked_error = any(
                    err.get("error_code") == "BLOCKED" for err in errors
                )

                self.log_test(
                    "Validation - Blocked Tasks",
                    has_blocked_error,
                    "Correctly prevented completing blocked task"
                )
            else:
                self.log_test(
                    "Validation - Blocked Tasks",
                    False,
                    "Should have failed for blocked task"
                )

        except Exception as e:
            self.log_test("Validation - Blocked Tasks", False, f"Exception: {e}")

    # ========================================================================
    # TEST 7: Validation - Circular Dependencies
    # ========================================================================

    async def test_validation_circular_dependencies(self, task_ids: List[int]):
        """Test that circular dependencies are detected"""
        print("\n" + "-" * 80)
        print("TEST 7: Validation - Circular Dependency Detection")
        print("-" * 80)

        if len(task_ids) < 4:
            self.log_test("Validation - Circular Deps", False, "Not enough tasks")
            return

        try:
            # Try to create circular dependency: task_ids[3] blocks task_ids[0]
            # (We already have: 0->1->2->3, so 3->0 would create a cycle)
            dependencies = [
                {"blocking_task_id": task_ids[3], "blocked_task_id": task_ids[0]}
            ]

            response = await self.client.post("/api/tasks/bulk-add-dependencies", json={
                "dependencies": dependencies,
                "actor_id": AUTHOR_ID
            })

            result = response.json()

            # Should fail because it creates a circular dependency
            if not result.get("success") and result.get("errors"):
                errors = result.get("errors", [])
                has_circular_error = any(
                    err.get("error_code") == "CIRCULAR_DEPENDENCY" for err in errors
                )

                self.log_test(
                    "Validation - Circular Deps",
                    has_circular_error,
                    "Correctly detected circular dependency"
                )
            else:
                self.log_test(
                    "Validation - Circular Deps",
                    False,
                    "Should have detected circular dependency"
                )

        except Exception as e:
            self.log_test("Validation - Circular Deps", False, f"Exception: {e}")

    # ========================================================================
    # TEST 8: Transaction Rollback
    # ========================================================================

    async def test_transaction_rollback(self):
        """Test that transaction rolls back on error"""
        print("\n" + "-" * 80)
        print("TEST 8: Transaction Rollback on Error")
        print("-" * 80)

        try:
            # Ensure we have test tasks to work with (never use production data)
            if not self.created_task_ids:
                self.log_test("Transaction Rollback", False,
                             "SKIPPED: No test tasks available. Cannot test rollback without fresh test data.")
                return

            # Use a task we created in this test run (safe to modify)
            valid_task_id = self.created_task_ids[0]

            # Get a guaranteed non-existent task ID by querying max ID
            all_tasks = await self.client.get("/api/tasks")
            task_list = all_tasks.json()
            max_id = max([t["id"] for t in task_list]) if task_list else 0
            invalid_task_id = max_id + 1000  # Use max + offset to ensure non-existence

            response = await self.client.post("/api/tasks/bulk-update", json={
                "task_ids": [valid_task_id, invalid_task_id],
                "updates": {"tag": "idea"},
                "actor_id": AUTHOR_ID
            })

            result = response.json()

            # Check that operation failed
            if not result.get("success"):
                # Verify valid task was NOT updated (rollback worked)
                task_response = await self.client.get(f"/api/tasks/{valid_task_id}")
                task_data = task_response.json()

                # Tag should still be original (not "idea")
                if task_data.get("tag") != "idea":
                    self.log_test(
                        "Transaction Rollback",
                        True,
                        "Transaction correctly rolled back on error"
                    )
                else:
                    self.log_test(
                        "Transaction Rollback",
                        False,
                        "Partial update occurred (rollback failed)"
                    )
            else:
                self.log_test(
                    "Transaction Rollback",
                    False,
                    "Operation should have failed"
                )

        except Exception as e:
            self.log_test("Transaction Rollback", False, f"Exception: {e}")

    # ========================================================================
    # TEST 9: Event Tracking
    # ========================================================================

    async def test_event_tracking(self, task_ids: List[int]):
        """Test that events are created for bulk operations"""
        print("\n" + "-" * 80)
        print("TEST 9: Event Tracking for Bulk Operations")
        print("-" * 80)

        if not task_ids:
            self.log_test("Event Tracking", False, "No tasks available")
            return

        try:
            test_task_id = task_ids[0]

            # Get events before update
            events_before_response = await self.client.get(
                f"/api/tasks/{test_task_id}/events"
            )
            events_before = events_before_response.json()
            before_count = len(events_before["events"])

            # Perform bulk update
            await self.client.post("/api/tasks/bulk-update", json={
                "task_ids": [test_task_id],
                "updates": {"description": "Updated via bulk operation"},
                "actor_id": AUTHOR_ID
            })

            # Get events after update
            events_after_response = await self.client.get(
                f"/api/tasks/{test_task_id}/events"
            )
            events_after = events_after_response.json()
            after_count = len(events_after["events"])

            # Should have at least one new event
            if after_count > before_count:
                # Check if the new event is a field_update
                # Events are ordered newest-first (DESC), so new events are at the beginning
                new_events = events_after["events"][:after_count - before_count]
                has_field_update = any(
                    event.get("event_type") == "field_update"
                    for event in new_events
                )

                self.log_test(
                    "Event Tracking",
                    has_field_update,
                    f"Created {after_count - before_count} event(s)"
                )
            else:
                self.log_test(
                    "Event Tracking",
                    False,
                    "No events created"
                )

        except Exception as e:
            self.log_test("Event Tracking", False, f"Exception: {e}")

    # ========================================================================
    # TEST 10: Performance - 100+ Tasks
    # ========================================================================

    async def test_performance_large_batch(self):
        """Test performance with 100+ tasks"""
        print("\n" + "-" * 80)
        print("TEST 10: Performance with 100+ Tasks")
        print("-" * 80)

        try:
            # Create 100 tasks
            tasks = [
                {
                    "project_id": PROJECT_ID,
                    "title": f"Perf Test Task {i}",
                    "description": f"Performance test task {i}",
                    "tag": "feature",
                    "priority": "P1",
                    "author_id": AUTHOR_ID
                }
                for i in range(1, 101)
            ]

            start_time = time.time()

            response = await self.client.post("/api/tasks/bulk-create", json={
                "tasks": tasks,
                "actor_id": AUTHOR_ID
            })

            create_time = time.time() - start_time

            result = response.json()

            if response.status_code == 200 and result.get("success"):
                perf_task_ids = result.get("task_ids", [])
                self.created_task_ids.extend(perf_task_ids)

                # Now update all 100 tasks
                start_time = time.time()

                update_response = await self.client.post("/api/tasks/bulk-update", json={
                    "task_ids": perf_task_ids,
                    "updates": {"status": "todo"},
                    "actor_id": AUTHOR_ID
                })

                update_time = time.time() - start_time

                # Target: < 2 seconds for 100 tasks
                passed = create_time < 2.0 and update_time < 2.0

                self.log_test(
                    "Performance - 100 Tasks",
                    passed,
                    f"Create: {create_time:.2f}s, Update: {update_time:.2f}s"
                )

                # Clean up performance test tasks
                await self.client.post("/api/tasks/bulk-delete", json={
                    "task_ids": perf_task_ids,
                    "actor_id": AUTHOR_ID
                })

                for tid in perf_task_ids:
                    if tid in self.created_task_ids:
                        self.created_task_ids.remove(tid)
            else:
                self.log_test(
                    "Performance - 100 Tasks",
                    False,
                    f"Failed to create tasks: {result}"
                )

        except Exception as e:
            self.log_test("Performance - 100 Tasks", False, f"Exception: {e}")

    # ========================================================================
    # TEST 11: MCP Tools Integration
    # ========================================================================

    async def test_mcp_tools_integration(self):
        """Test bulk operations via MCP tools"""
        print("\n" + "-" * 80)
        print("TEST 11: MCP Tools Integration")
        print("-" * 80)

        try:
            # Test bulk_create_tasks MCP tool
            result = await call_tool("bulk_create_tasks", {
                "tasks": [
                    {
                        "project_id": PROJECT_ID,
                        "title": "MCP Bulk Test 1",
                        "description": "Created via MCP tool",
                        "tag": "feature",
                        "priority": "P1",
                        "author_id": AUTHOR_ID
                    },
                    {
                        "project_id": PROJECT_ID,
                        "title": "MCP Bulk Test 2",
                        "description": "Created via MCP tool",
                        "tag": "bug",
                        "priority": "P0",
                        "author_id": AUTHOR_ID
                    }
                ],
                "actor_id": AUTHOR_ID
            })

            data = json.loads(result[0].text)

            if data.get("success"):
                mcp_task_ids = data.get("task_ids", [])
                self.created_task_ids.extend(mcp_task_ids)

                self.log_test(
                    "MCP Tools - bulk_create_tasks",
                    True,
                    f"Created {len(mcp_task_ids)} tasks via MCP"
                )

                # Test bulk_update_tasks MCP tool
                update_result = await call_tool("bulk_update_tasks", {
                    "task_ids": mcp_task_ids,
                    "updates": {"status": "in_progress"},
                    "actor_id": AUTHOR_ID
                })

                update_data = json.loads(update_result[0].text)

                if update_data.get("success"):
                    self.log_test(
                        "MCP Tools - bulk_update_tasks",
                        True,
                        f"Updated {update_data.get('processed_count')} tasks via MCP"
                    )
                else:
                    self.log_test(
                        "MCP Tools - bulk_update_tasks",
                        False,
                        f"Failed: {update_data}"
                    )

                # Clean up MCP test tasks
                await call_tool("bulk_delete_tasks", {
                    "task_ids": mcp_task_ids,
                    "actor_id": AUTHOR_ID
                })

                for tid in mcp_task_ids:
                    if tid in self.created_task_ids:
                        self.created_task_ids.remove(tid)
            else:
                self.log_test(
                    "MCP Tools - bulk_create_tasks",
                    False,
                    f"Failed: {data}"
                )

        except Exception as e:
            self.log_test("MCP Tools Integration", False, f"Exception: {e}")


async def main():
    """Run all bulk operation tests"""
    tester = BulkOperationTester()

    try:
        await tester.setup()

        # Phase 1: Happy path tests
        print("\n" + "=" * 80)
        print("PHASE 1: HAPPY PATH TESTS")
        print("=" * 80)

        task_ids = await tester.test_bulk_create_happy_path()
        await tester.test_bulk_update_happy_path(task_ids)
        await tester.test_bulk_take_ownership_happy_path(task_ids)
        await tester.test_bulk_add_dependencies_happy_path(task_ids)
        await tester.test_bulk_delete_happy_path(task_ids)

        # Phase 2: Validation tests
        print("\n" + "=" * 80)
        print("PHASE 2: VALIDATION TESTS")
        print("=" * 80)

        await tester.test_validation_blocked_tasks(task_ids)
        await tester.test_validation_circular_dependencies(task_ids)

        # Phase 3: Transaction and system tests
        print("\n" + "=" * 80)
        print("PHASE 3: TRANSACTION & SYSTEM TESTS")
        print("=" * 80)

        await tester.test_transaction_rollback()
        await tester.test_event_tracking(task_ids)

        # Phase 4: Performance tests
        print("\n" + "=" * 80)
        print("PHASE 4: PERFORMANCE TESTS")
        print("=" * 80)

        await tester.test_performance_large_batch()

        # Phase 5: MCP tools integration
        print("\n" + "=" * 80)
        print("PHASE 5: MCP TOOLS INTEGRATION")
        print("=" * 80)

        await tester.test_mcp_tools_integration()

    finally:
        await tester.teardown()

    # Return exit code based on test results
    return 0 if tester.tests_failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
