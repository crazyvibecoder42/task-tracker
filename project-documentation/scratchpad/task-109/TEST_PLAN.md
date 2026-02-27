# TEST PLAN — Task 109: [sub-proj][6/7] Implement subproject task filtering in project page

> Tests that the project page reads the `?subproject=` URL param, applies it to task fetching, shows a dismissable filter chip, and stacks correctly with the existing status filter.

## Prerequisites

- Run `make dev-start` to bring up the development environment
- Log in at http://localhost:3001
- Navigate to a project that has at least two sub-projects with tasks assigned to each (set up via the Sidebar `+` button or the API)
- Ensure at least one task is **unassigned** (no sub-project) and at least one task belongs to a named sub-project (e.g. "Sprint 1")

---

## Test Cases

### TC-001: Filter chip appears when sub-project is selected

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to a project page (e.g. `/projects/17`)
2. In the Sidebar, find the sub-projects section and click a named sub-project (e.g. "Default")
3. Observe the URL — it should change to `/projects/17?subproject=<id>`
4. Observe the task list header area

**Expected result**: A chip appears next to the "Tasks" heading showing the sub-project name (e.g. "Default ×"). Only tasks belonging to that sub-project are shown in the list below.

---

### TC-002: Clicking × on the filter chip clears the filter

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to a project with a `?subproject=<id>` URL param active
2. Verify the chip is visible with the sub-project name
3. Click the `×` button on the chip

**Expected result**: The URL changes to `/projects/{id}` (no `?subproject` param). The chip disappears. All tasks for the project are shown (unfiltered).

---

### TC-003: Unassigned filter shows chip labeled "Unassigned"

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to a project page
2. In the Sidebar, click the "Unassigned" entry in the sub-projects section (sets `?subproject=0`)
3. Observe the task list header and the task list

**Expected result**: A chip labeled "Unassigned ×" appears next to "Tasks". Only tasks with no sub-project assignment are shown.

---

### TC-004: All Tasks view (no param) shows all tasks

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate directly to `/projects/{id}` (no `?subproject` param)
2. Observe the task list header and task list

**Expected result**: No filter chip appears. All project tasks are shown regardless of sub-project.

---

### TC-005: Status filter and sub-project filter stack

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to a project page and click a sub-project in the Sidebar to activate the filter
2. Verify the sub-project chip is visible and the task list is filtered
3. Click the "In Progress" status filter button in the task list header
4. Observe the task list

**Expected result**: Only tasks that are **both** in the selected sub-project **and** have status "In Progress" are shown. Both the sub-project chip and the "In Progress" status button remain visually active.

---

### TC-006: Search within a sub-project filter

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to activate a sub-project filter (click sub-project in Sidebar)
2. Type a search query in the search bar
3. Observe the task list

**Expected result**: Only tasks matching the search query **within** the selected sub-project are shown (server-side filtering combines both). Results are narrower than searching without a sub-project filter.

---

### TC-007: Changing sub-project clears the search query

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to a project page
2. Type a search term in the search bar
3. Click a different sub-project in the Sidebar
4. Observe the search bar

**Expected result**: The search bar is cleared (empty) after selecting the sub-project. The task list shows the filtered sub-project tasks without any search restriction.

---

### TC-008: Browser back navigation restores previous filter

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to a project page (no filter)
2. Click "Default" sub-project in the Sidebar
3. Click "Sprint 1" sub-project in the Sidebar
4. Press the browser back button

**Expected result**: The URL changes back to `?subproject=<Default id>`. The chip shows "Default ×". The task list shows only Default sub-project tasks.
