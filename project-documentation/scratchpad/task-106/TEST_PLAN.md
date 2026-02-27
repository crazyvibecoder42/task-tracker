# TEST PLAN — Task 106: [sub-proj][3/7] Add subproject_id filter to task endpoints and active subprojects endpoint

> Tests that `GET /api/tasks` and `GET /api/tasks/actionable` correctly filter by `subproject_id`, that the sentinel `subproject_id=0` returns unassigned tasks, and that the new `GET /api/projects/{id}/subprojects/active` endpoint returns only sub-projects with open tasks.

## Prerequisites

- Development environment running (backend at http://localhost:6002)
- Obtain a JWT token:
  ```
  curl -s -X POST http://localhost:6002/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","password":"admin123"}'
  ```
  Save the `access_token` as `$TOKEN`.
- Create a fresh test project and sub-projects (see setup commands in task description).

---

## Test Cases

### TC-001: Filter tasks by sub-project ID

**Method**: curl

**Steps**:
1. Using curl, create a test project (POST /api/projects), get its ID as `$PROJECT`.
2. Using curl, list sub-projects for that project (GET /api/projects/$PROJECT/subprojects), get the Default sub-project ID as `$DEFAULT_SP`.
3. Using curl, create a second sub-project named "Sprint 1" (POST /api/projects/$PROJECT/subprojects), get its ID as `$SPRINT_SP`.
4. Using curl, create a task in the Default sub-project: POST /api/tasks with `{"project_id": $PROJECT, "title": "Default task", "subproject_id": $DEFAULT_SP}`.
5. Using curl, create a task in Sprint 1: POST /api/tasks with `{"project_id": $PROJECT, "title": "Sprint task", "subproject_id": $SPRINT_SP}`.
6. Using curl, fetch `GET /api/tasks?project_id=$PROJECT&subproject_id=$SPRINT_SP` with the Bearer token.

**Expected result**: Response contains exactly one task with title "Sprint task". The "Default task" does not appear.

---

### TC-002: Filter tasks for unassigned (subproject_id=0 sentinel)

**Method**: curl

**Steps**:
1. Continue from TC-001 setup (project and sub-projects already created).
2. Using curl, create a third task with no `subproject_id`: POST /api/tasks with `{"project_id": $PROJECT, "title": "Unassigned task"}`.
3. Using curl, fetch `GET /api/tasks?project_id=$PROJECT&subproject_id=0` with the Bearer token.

**Expected result**: Response contains exactly one task with title "Unassigned task". Neither "Default task" nor "Sprint task" appear.

---

### TC-003: Actionable tasks filter by sub-project ID

**Method**: curl

**Steps**:
1. Continue from TC-001 setup.
2. Using curl, fetch `GET /api/tasks/actionable?project_id=$PROJECT&subproject_id=$SPRINT_SP` with the Bearer token.

**Expected result**: Response contains only "Sprint task". The "Default task" and "Unassigned task" do not appear.

---

### TC-004: Actionable tasks with subproject_id=0 sentinel

**Method**: curl

**Steps**:
1. Continue from TC-002 setup.
2. Using curl, fetch `GET /api/tasks/actionable?project_id=$PROJECT&subproject_id=0` with the Bearer token.

**Expected result**: Response contains only "Unassigned task".

---

### TC-005: Active subprojects endpoint returns only subprojects with open tasks

**Method**: curl

**Steps**:
1. Continue from TC-001 setup (both Default and Sprint sub-projects have at least one open task).
2. Using curl, fetch `GET /api/projects/$PROJECT/subprojects/active` with the Bearer token.

**Expected result**: HTTP 200. Response is a JSON array containing both the Default and Sprint 1 sub-projects. All items have `"is_active": true`.

---

### TC-006: Active subprojects excludes subprojects with no open tasks

**Method**: curl

**Steps**:
1. Continue from TC-001 setup.
2. Using curl, mark the "Sprint task" as done: PUT /api/tasks/$SPRINT_TASK_ID with `{"status": "done"}`.
3. Using curl, fetch `GET /api/projects/$PROJECT/subprojects/active` with the Bearer token.

**Expected result**: HTTP 200. Response contains only the Default sub-project. Sprint 1 does NOT appear (it has no open tasks).

---

### TC-007: Cross-project subproject_id validation on task create

**Method**: curl

**Steps**:
1. Using curl, create a second project: POST /api/projects with `{"name": "Other Project"}`, get its ID as `$PROJECT2`.
2. Using curl, attempt to create a task in $PROJECT2 but with Sprint 1's `subproject_id` from $PROJECT: POST /api/tasks with `{"project_id": $PROJECT2, "title": "Bad task", "subproject_id": $SPRINT_SP}`.

**Expected result**: HTTP 400 response with an error message indicating the subproject does not belong to the specified project.

---

### TC-008: Cross-project validation when filtering GET /api/tasks

**Method**: curl

**Steps**:
1. Continue from TC-007 setup ($PROJECT2 exists).
2. Using curl, create a task in $PROJECT2 with no subproject_id: POST /api/tasks with `{"project_id": $PROJECT2, "title": "Other task"}`.
3. Using curl, fetch `GET /api/tasks?project_id=$PROJECT2&subproject_id=$SPRINT_SP` (using Sprint SP from $PROJECT1, but filtering $PROJECT2).

**Expected result**: HTTP 400 response indicating the subproject_id does not belong to the specified project_id.

---

### TC-009: Task responses include subproject_id and nested subproject object

**Method**: curl

**Steps**:
1. Continue from TC-001 setup.
2. Using curl, fetch `GET /api/tasks?project_id=$PROJECT&subproject_id=$SPRINT_SP`.

**Expected result**: Each task in the response includes both `"subproject_id": $SPRINT_SP` (integer) and a nested `"subproject"` object with `id`, `name`, `project_id`, `is_default`, `is_active`, and `subproject_number` fields.

---

### TC-010: GET /api/tasks without subproject_id returns all tasks (backward compatibility)

**Method**: curl

**Steps**:
1. Continue from TC-001 and TC-002 setup (three tasks exist: Default task, Sprint task, Unassigned task).
2. Using curl, fetch `GET /api/tasks?project_id=$PROJECT` (no subproject_id param).

**Expected result**: HTTP 200. Response contains all three tasks regardless of their subproject assignment. No filtering applied.
