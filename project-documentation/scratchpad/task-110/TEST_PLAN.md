# TEST PLAN — Task 110: Add subproject assignment to task create/edit forms and task list display

> Tests that users can assign tasks to sub-projects during creation, see sub-project badges on tasks, and change sub-project assignment from the task detail page.

## Prerequisites

- Start the development environment: `make dev-start`
- Log in at http://localhost:3001 with `admin@example.com` / `admin123`
- Ensure a project exists with at least two sub-projects (e.g. "Sprint 1" and "Sprint 2"). Create them via the sidebar `+` button if needed.
- Ensure at least two tasks exist in that project (for badge visibility testing)

---

## Test Cases

### TC-001: Sub-project dropdown appears in the new task form

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to the project page (http://localhost:3001/projects/{id})
2. Click the "Add Task" button to expand the new task form
3. Inspect the form for a "Sub-project" dropdown element

**Expected result**: A `<select>` dropdown labeled or containing "No sub-project" as the first option, followed by the names of all sub-projects for that project (e.g. "Sprint 1", "Sprint 2").

---

### TC-002: Creating a task with a sub-project stores the assignment

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to the project page
2. Click "Add Task" to open the form
3. Fill in a title (e.g. "Test subproject task")
4. Select "Sprint 1" from the sub-project dropdown
5. Submit the form by clicking "Create Task"
6. Observe the task list

**Expected result**: The new task appears in the task list with a "Sprint 1" badge (violet/muted chip) visible next to its title or in its metadata row.

---

### TC-003: No sub-project badge shown when sub-project filter is active

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to the project page (all-tasks view — no `?subproject=` query param)
2. Verify that tasks with a sub-project assignment show their sub-project badge
3. Click "Sprint 1" in the sidebar sub-projects list (navigates to `?subproject=<id>`)
4. Observe the task list items

**Expected result**: In step 2, sub-project badges are visible on tasks that have a sub-project. In step 4, the badges are hidden (they are redundant since all shown tasks are already in Sprint 1).

---

### TC-004: Pre-selection when sub-project filter is active

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to the project page filtered to "Sprint 1" (click "Sprint 1" in sidebar)
2. Click "Add Task" to open the new task form
3. Check the sub-project dropdown's selected value

**Expected result**: The sub-project dropdown is pre-selected to "Sprint 1" (the active filter sub-project), not "No sub-project".

---

### TC-005: Task detail page shows current sub-project assignment

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to the detail page for a task that has "Sprint 1" assigned (`/tasks/{id}`)
2. Inspect the task metadata section (not the edit form)

**Expected result**: The task detail page shows the sub-project assignment, e.g. a badge or field labeled "Sub-project" showing "Sprint 1".

---

### TC-006: Edit form on task detail page includes sub-project dropdown

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to a task detail page
2. Click the "Edit" button to enter edit mode
3. Inspect the edit form for a sub-project dropdown

**Expected result**: A sub-project dropdown appears in the edit form with "No sub-project" as one option and all project sub-projects as further options. The currently assigned sub-project is pre-selected.

---

### TC-007: Changing sub-project from edit form saves correctly

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to a task detail page for a task in "Sprint 1"
2. Click "Edit"
3. Change the sub-project dropdown to "Sprint 2"
4. Click "Save Changes"
5. Observe the task detail page after save
6. Navigate back to the project page

**Expected result**: After saving, the task detail page reflects "Sprint 2" as the sub-project. On the project page, the task's badge shows "Sprint 2".

---

### TC-008: Clearing sub-project assignment ("No sub-project") works

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to open a task detail page for a task assigned to any sub-project
2. Click "Edit"
3. Change the sub-project dropdown to "No sub-project" (empty option)
4. Click "Save Changes"
5. Observe the task detail page after save
6. Navigate back to the project page

**Expected result**: The task no longer shows a sub-project badge. On the project page "all-tasks" view, no sub-project badge is shown for that task. When viewing the "Unassigned" sub-project filter, the task appears there.

---

### TC-009: Verify via API that subproject_id is persisted

**Method**: curl

**Steps**:
1. Use curl to GET the task that was modified in TC-007 (GET `/api/tasks/{id}` with `X-API-Key` header)
2. Inspect the `subproject_id` field in the response

**Expected result**: The `subproject_id` field in the API response matches the ID of "Sprint 2" that was selected in TC-007.
