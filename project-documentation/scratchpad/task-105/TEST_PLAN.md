# TEST PLAN — Task 105: [sub-proj][2/7] Implement subproject CRUD API endpoints with Default subproject behavior

> Tests verify that the subproject CRUD API endpoints are correctly implemented and that creating a new project automatically creates a non-deletable "Default" sub-project.

## Prerequisites

- Development environment is running: `make dev-reset && make dev-start`
- Backend is healthy: `curl http://localhost:6002/health` returns `{"status":"ok"}`
- Obtain a JWT token:
  ```
  TOKEN=$(curl -s -X POST http://localhost:6002/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","password":"admin123"}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
  ```

---

## Test Cases

### TC-001: New project auto-creates Default sub-project

**Method**: curl

**Steps**:
1. Use curl to POST a new project to `/api/projects` with a JSON body containing just a name
2. Capture the returned `id` of the created project
3. Use curl to GET `/api/projects/{project_id}/subprojects` using the captured project ID and the Bearer token

**Expected result**: HTTP 200 with a JSON array containing exactly one entry: `{"name":"Default","subproject_number":1,"is_default":true,"is_active":false,...}`. The auto-created Default sub-project must be present immediately after project creation with no extra steps.

---

### TC-002: Create additional sub-projects and verify sequential numbering

**Method**: curl

**Steps**:
1. Use the project ID from TC-001 (or create a fresh project)
2. Use curl to POST to `/api/projects/{project_id}/subprojects` with body `{"name":"Sprint 1"}`
3. Use curl to POST to `/api/projects/{project_id}/subprojects` with body `{"name":"Sprint 2"}`
4. Use curl to GET `/api/projects/{project_id}/subprojects`

**Expected result**: HTTP 200 with a JSON array of 3 entries ordered by `subproject_number`: Default (1), Sprint 1 (2), Sprint 2 (3). Each has the correct `is_default` value (only Default is `true`).

---

### TC-003: is_active reflects active task presence

**Method**: curl

**Steps**:
1. Obtain the `id` of "Sprint 1" sub-project from GET `/api/projects/{project_id}/subprojects`
2. Use curl to POST a new task to `/api/tasks` with `project_id`, `title`, and `subproject_id` set to Sprint 1's ID
3. Use curl to GET `/api/projects/{project_id}/subprojects`

**Expected result**: HTTP 200 with Sprint 1 showing `"is_active":true`; Default and Sprint 2 showing `"is_active":false`. A task in any status except `done` or `not_needed` makes the sub-project active.

---

### TC-004: is_active is false when all tasks are done or not_needed

**Method**: curl

**Steps**:
1. Mark the task created in TC-003 as `done` using PUT `/api/tasks/{task_id}` with `{"status":"done"}`
2. Use curl to GET `/api/projects/{project_id}/subprojects`

**Expected result**: Sprint 1 now shows `"is_active":false` since all its tasks are `done`.

---

### TC-005: Rename a sub-project (including Default)

**Method**: curl

**Steps**:
1. Obtain the `id` of the Default sub-project from GET `/api/projects/{project_id}/subprojects`
2. Use curl to PUT `/api/subprojects/{default_id}` with body `{"name":"Renamed Default"}`
3. Use curl to GET `/api/projects/{project_id}/subprojects` to verify

**Expected result**: HTTP 200 returned by PUT with the updated `SubprojectResponse`. GET confirms the Default sub-project now has `name:"Renamed Default"` but still has `is_default:true`.

---

### TC-006: Delete Default sub-project is blocked with 403

**Method**: curl

**Steps**:
1. Obtain the `id` of the Default (or renamed Default) sub-project
2. Use curl to send DELETE to `/api/subprojects/{default_id}` with the Bearer token

**Expected result**: HTTP 403 response with body `{"detail":"Cannot delete the Default sub-project"}`. The sub-project still exists after the attempt.

---

### TC-007: Delete non-default sub-project; tasks become unassigned

**Method**: curl

**Steps**:
1. Obtain the `id` of "Sprint 2" sub-project
2. Use curl to POST a task assigned to Sprint 2 (POST `/api/tasks` with `subproject_id` set to Sprint 2's ID)
3. Note the task ID from the response
4. Use curl to send DELETE to `/api/subprojects/{sprint2_id}` with the Bearer token
5. Use curl to GET `/api/tasks/{task_id}` to check the task's `subproject_id`

**Expected result**: DELETE returns HTTP 204 with no body. The task still exists but `subproject_id` is `null`.

---

### TC-008: Viewer cannot create or delete sub-projects

**Method**: curl

**Steps**:
1. Create a second user with viewer role on the project (or use a viewer-role token)
2. Use curl to POST to `/api/projects/{project_id}/subprojects` with the viewer's token and body `{"name":"Unauthorized Sprint"}`
3. Use curl to DELETE `/api/subprojects/{sprint1_id}` with the viewer's token

**Expected result**: Both requests return HTTP 403. No sub-project is created or deleted.

---

### TC-009: GET subprojects returns 404 for non-existent project

**Method**: curl

**Steps**:
1. Use curl to GET `/api/projects/999999/subprojects` with the Bearer token

**Expected result**: HTTP 404 response with a detail message indicating the project was not found.
