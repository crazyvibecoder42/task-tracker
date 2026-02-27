# TEST PLAN — Task 107: Add subproject MCP tools and update existing tool parameters

> Tests that the MCP server exposes all subproject tools and that the four updated existing tools
> correctly accept an optional `subproject_id` parameter, both with and without backward-compatibility calls.

## Prerequisites

- Development backend running and healthy:
  ```
  make dev-restart
  curl http://localhost:6002/health
  ```
- MCP server configured pointing at development backend (`.mcp.dev.json` set up).
- At least one project exists. Note its `project_id` (e.g. `17`).
- Claude Code restarted after any MCP config changes.

---

## Test Cases

### TC-001: list_subprojects returns all sub-projects for a project

**Method**: MCP tool call via Claude Code

**Steps**:
1. Call `mcp__task-tracker__list_subprojects` with `project_id=<your_project_id>`.

**Expected result**: HTTP 200 response; JSON array of sub-project objects, each containing at minimum `id`, `name`, `subproject_number`, `is_default`, and `is_active` fields. The "Default" sub-project is present.

---

### TC-002: create_subproject creates a new sub-project with auto-incremented number

**Method**: MCP tool call via Claude Code

**Steps**:
1. Call `mcp__task-tracker__create_subproject` with `project_id=<id>` and `name="MCP Sprint"`.
2. Call `mcp__task-tracker__list_subprojects` with `project_id=<id>` to verify the new sub-project appears.

**Expected result**: Step 1 returns a new sub-project object with `subproject_number > 1` (auto-incremented) and `is_default=false`. Step 2 shows the new sub-project in the list.

---

### TC-003: update_subproject renames a sub-project

**Method**: MCP tool call via Claude Code

**Steps**:
1. From TC-002, note the `id` of the "MCP Sprint" sub-project.
2. Call `mcp__task-tracker__update_subproject` with `subproject_id=<id>` and `name="MCP Sprint Renamed"`.
3. Call `mcp__task-tracker__list_subprojects` with `project_id=<id>` to verify the rename.

**Expected result**: Step 2 returns the updated sub-project with `name="MCP Sprint Renamed"`. Step 3 confirms the new name appears in the list.

---

### TC-004: delete_subproject removes a non-default sub-project

**Method**: MCP tool call via Claude Code

**Steps**:
1. Use the sub-project from TC-003 (`"MCP Sprint Renamed"`).
2. Call `mcp__task-tracker__delete_subproject` with `subproject_id=<id>`.
3. Call `mcp__task-tracker__list_subprojects` with `project_id=<id>` to verify deletion.

**Expected result**: Step 2 returns `{"success": true}`. Step 3 no longer includes the deleted sub-project.

---

### TC-005: delete_subproject rejects deletion of the Default sub-project

**Method**: MCP tool call via Claude Code

**Steps**:
1. From TC-001, note the `id` of the "Default" sub-project (`is_default=true`).
2. Call `mcp__task-tracker__delete_subproject` with `subproject_id=<default_id>`.

**Expected result**: Response contains an `error` field (HTTP 4xx from the backend). The Default sub-project remains when listing.

---

### TC-006: list_active_subprojects returns only sub-projects with open tasks

**Method**: MCP tool call via Claude Code

**Steps**:
1. Create a sub-project via `mcp__task-tracker__create_subproject` named "Active SP".
2. Create a task with `mcp__task-tracker__create_task` using `project_id=<id>`, `title="Active task"`, and `subproject_id=<new_sp_id>`.
3. Call `mcp__task-tracker__list_active_subprojects` with `project_id=<id>`.

**Expected result**: Step 3 returns only sub-projects that have at least one non-done, non-not_needed task. "Active SP" is in the list. `is_active=true` for all returned objects.

---

### TC-007: list_actionable_tasks_in_subproject returns filtered tasks

**Method**: MCP tool call via Claude Code

**Steps**:
1. Use the sub-project and task created in TC-006.
2. Call `mcp__task-tracker__list_actionable_tasks_in_subproject` with `project_id=<id>` and `subproject_id=<new_sp_id>`.

**Expected result**: Returns a list including only the task created in TC-006 with status `todo`/`in_progress`/`review`. No tasks from other sub-projects appear.

---

### TC-008: list_tasks accepts optional subproject_id filter

**Method**: MCP tool call via Claude Code

**Steps**:
1. Using the sub-project from TC-006 that has a task assigned to it, call `mcp__task-tracker__list_tasks` with `project_id=<id>` and `subproject_id=<sp_id>`.
2. Call `mcp__task-tracker__list_tasks` with `project_id=<id>` only (no subproject_id) to confirm backward compatibility.

**Expected result**: Step 1 returns only tasks assigned to that sub-project. Step 2 returns all tasks with no error.

---

### TC-009: list_actionable_tasks accepts optional subproject_id filter

**Method**: MCP tool call via Claude Code

**Steps**:
1. Call `mcp__task-tracker__list_actionable_tasks` with `project_id=<id>` and `subproject_id=<sp_id>`.
2. Call `mcp__task-tracker__list_actionable_tasks` with `project_id=<id>` only (no subproject_id).

**Expected result**: Step 1 returns only actionable tasks in that sub-project. Step 2 returns all actionable tasks with no error.

---

### TC-010: create_task with subproject_id assigns the task to the sub-project

**Method**: MCP tool call via Claude Code

**Steps**:
1. Call `mcp__task-tracker__create_task` with `project_id=<id>`, `title="Subproject task"`, and `subproject_id=<sp_id>`.
2. Call `mcp__task-tracker__get_task` with the returned task ID.

**Expected result**: The task returned in step 2 has `subproject_id` matching `<sp_id>` and a nested `subproject` object with the sub-project name.

---

### TC-011: update_task reassigns a task to a different subproject

**Method**: MCP tool call via Claude Code

**Steps**:
1. Use the task from TC-010.
2. Create another sub-project via `mcp__task-tracker__create_subproject` named "Target SP".
3. Call `mcp__task-tracker__update_task` with `task_id=<task_id>` and `subproject_id=<target_sp_id>`.
4. Call `mcp__task-tracker__get_task` to verify.

**Expected result**: Step 3 returns the task with the new `subproject_id`. Step 4 confirms the `subproject.name` is "Target SP".

---

### TC-012: update_task with subproject_id=0 unassigns the task

**Method**: MCP tool call via Claude Code

**Steps**:
1. Use the task from TC-010 (currently assigned to a sub-project).
2. Call `mcp__task-tracker__update_task` with `task_id=<task_id>` and `subproject_id=0`.
3. Call `mcp__task-tracker__get_task` to verify.

**Expected result**: Step 3 shows `subproject_id=null` and `subproject=null` on the task.

---

### TC-013: Backward compatibility — existing callers without subproject_id still work

**Method**: MCP tool call via Claude Code

**Steps**:
1. Call `mcp__task-tracker__list_tasks` with only `project_id=<id>` (no subproject_id).
2. Call `mcp__task-tracker__list_actionable_tasks` with only `project_id=<id>`.
3. Call `mcp__task-tracker__create_task` with only `project_id=<id>` and `title="Compat test"`.
4. Call `mcp__task-tracker__update_task` with only `task_id=<any_id>` and `status="todo"`.

**Expected result**: All four calls succeed with no errors. No `subproject_id` required.
