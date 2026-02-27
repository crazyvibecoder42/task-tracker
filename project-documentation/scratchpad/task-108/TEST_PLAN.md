# TEST PLAN — Task 108: [sub-proj][5/7] Add frontend API functions and subprojects section to Sidebar

> Tests the `Subproject` API additions to `frontend/lib/api.ts` and the sub-projects filter section in `frontend/components/Sidebar.tsx`, verifying that sub-projects appear only on project pages and correctly drive URL-based filtering.

## Prerequisites

- Development environment running: `make dev-start`
- Navigate to http://localhost:3001 and log in as admin (admin@example.com / admin123)
- At least one project exists with sub-projects. If not, create them via:
  - Use curl to POST to `http://localhost:6002/api/projects/{id}/subprojects` with `{"name":"Sprint 1"}` (X-API-Key header required)
  - Or use the `+` button in the sidebar after this feature is implemented

---

## Test Cases

### TC-001: Sub-projects section does NOT appear on non-project pages

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to http://localhost:3001 (Dashboard)
2. Capture a snapshot of the sidebar
3. Navigate to http://localhost:3001/tasks
4. Capture a snapshot of the sidebar
5. Navigate to http://localhost:3001/kanban
6. Capture a snapshot of the sidebar

**Expected result**: None of the three pages show a "Sub-projects" section or any sub-project entries in the sidebar. The sidebar shows only Dashboard, All Tasks, Kanban Board, Teams, and Projects sections.

---

### TC-002: Sub-projects section appears when navigating to a project page

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to a project page: `http://localhost:3001/projects/{id}` (use a valid project ID that has sub-projects, e.g., the one seeded in Prerequisites)
2. Capture a snapshot of the sidebar

**Expected result**: A sub-projects section appears in the sidebar below the Projects list. It shows at least three entries: "All Tasks" (at top), at least one sub-project name (e.g., "Default"), and "Unassigned" (at bottom).

---

### TC-003: Clicking a sub-project updates the URL and highlights the entry

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to `http://localhost:3001/projects/{id}`
2. In the sub-projects section, click a sub-project entry (e.g., "Default")
3. Capture the current URL and sidebar snapshot
4. Click "All Tasks" entry in the sub-projects section
5. Capture the current URL and sidebar snapshot

**Expected result**:
- After clicking "Default": URL becomes `/projects/{id}?subproject={sp_id}`. The "Default" entry is highlighted with an indigo background (`bg-indigo-50 text-indigo-600`). "All Tasks" is no longer highlighted.
- After clicking "All Tasks": URL returns to `/projects/{id}` (no `subproject` param). "All Tasks" entry is highlighted with indigo background.

---

### TC-004: Unassigned entry links to subproject=0

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to `http://localhost:3001/projects/{id}`
2. Click the "Unassigned" entry at the bottom of the sub-projects section
3. Capture the current URL

**Expected result**: URL becomes `/projects/{id}?subproject=0`. The "Unassigned" entry is highlighted with indigo background.

---

### TC-005: Active vs inactive sub-project visual distinction

**Method**: Playwright MCP (browser)

**Steps**:
1. Ensure there are at least two sub-projects: one with open tasks (is_active=true) and one without (is_active=false)
   - Use curl to verify: `GET http://localhost:6002/api/projects/{id}/subprojects`
2. Use Playwright MCP to navigate to `http://localhost:3001/projects/{id}`
3. Capture a snapshot of the sub-projects section

**Expected result**: Sub-projects with `is_active=true` show a green/colored indicator (dot `●`). Sub-projects with `is_active=false` appear with dimmed styling (grey text or faded dot).

---

### TC-006: Sidebar updates when switching between projects

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to `http://localhost:3001/projects/{project_a_id}`
2. Note the sub-projects shown in the sidebar for Project A
3. Click Project B in the sidebar's Projects section
4. Capture a snapshot of the sub-projects section

**Expected result**: The sub-projects section now shows Project B's sub-projects, not Project A's. The section reflects the currently active project.

---

### TC-007: API functions exist in api.ts (static verification)

**Method**: curl

**Steps**:
1. Use curl to call `GET http://localhost:6002/api/projects/{id}/subprojects` with X-API-Key header
2. Verify the response returns an array of sub-project objects

**Expected result**: HTTP 200 with a JSON array containing objects with fields: `id`, `project_id`, `name`, `subproject_number`, `is_default`, `is_active`, `created_at`. This confirms the API endpoint and the TypeScript interface shape are aligned.

---

### TC-008: Inline sub-project creation via + button

**Method**: Playwright MCP (browser)

**Steps**:
1. Use Playwright MCP to navigate to `http://localhost:3001/projects/{id}`
2. Locate the `+` button next to the sub-projects section header
3. Click the `+` button
4. Type a new sub-project name (e.g., "Sprint 2") into the inline input that appears
5. Press Enter
6. Capture the sidebar snapshot

**Expected result**: The new sub-project "Sprint 2" appears in the sub-projects list. No page reload required — the list refreshes in-place.
