# TEST PLAN — Task 104: [sub-proj][1/7] Add subprojects table and SQLAlchemy model/schemas

> Verifies that the `subprojects` table is correctly created in the database schema, the `tasks` table has the `subproject_id` FK column, and the SQLAlchemy models plus Pydantic schemas are structured correctly so the backend starts cleanly.

## Prerequisites

- Docker is running and the development environment can be reset
- Ensure no containers are running before the reset (or let `make dev-reset` handle it)
- Have `curl` available on the host machine
- API key for dev environment available (or use `admin@example.com` / `admin123` to obtain one)

---

## Test Cases

### TC-001: Verify `subprojects` table exists with correct schema

**Method**: docker exec

**Steps**:
1. Reset the dev database to apply the updated `init.sql`: run `make dev-reset` and wait for it to complete
2. Use docker exec to run `\d subprojects` against the `tasktracker_dev` database
3. Inspect the output

**Expected result**: Table description shows columns: `id` (serial, PK), `project_id` (integer, NOT NULL, FK → projects), `name` (varchar 255, NOT NULL), `subproject_number` (integer, NOT NULL), `is_default` (boolean, NOT NULL, default false), `created_at` (timestamptz). Also shows a `UNIQUE(project_id, subproject_number)` constraint.

---

### TC-002: Verify `tasks.subproject_id` column exists

**Method**: docker exec

**Steps**:
1. Using the dev database after `make dev-reset` (from TC-001 setup), use docker exec to run `\d tasks` and grep the output for `subproject`
2. Inspect the output

**Expected result**: A line containing `subproject_id | integer` that is nullable, with a FK reference to the `subprojects` table. `ON DELETE SET NULL` behaviour is present.

---

### TC-003: Backend container starts cleanly (no import errors)

**Method**: curl + docker logs

**Steps**:
1. After `make dev-reset`, run `make dev-restart` to restart the backend
2. Wait a few seconds, then use `curl http://localhost:6002/health` to verify the backend responds
3. Optionally view backend logs with `make dev-logs` to confirm no Python import errors related to `Subproject` or schema classes

**Expected result**: `curl http://localhost:6002/health` returns HTTP 200 with `{"status": "ok"}` (or equivalent health response). Logs show no `ImportError`, `AttributeError`, or SQLAlchemy mapping errors.

---

### TC-004: `SubprojectCreate`, `SubprojectUpdate`, `SubprojectResponse` schemas exist

**Method**: docker exec (Python import check)

**Steps**:
1. Use docker exec to run a one-liner Python import test against the running backend container: `python -c "from schemas import SubprojectCreate, SubprojectUpdate, SubprojectResponse; print('OK')"`
2. Inspect the output

**Expected result**: Outputs `OK` with no errors. No `ImportError` or `AttributeError`.

---

### TC-005: `Task` and `TaskSummary` schemas include optional `subproject_id` and `subproject`

**Method**: docker exec (Python import check)

**Steps**:
1. Use docker exec to run a one-liner Python import test against the backend container:
   `python -c "from schemas import Task, TaskSummary; t = Task.__fields__; print('subproject_id' in t, 'subproject' in t)"`
2. Inspect the output

**Expected result**: Outputs `True True` — confirming both `subproject_id` and `subproject` fields are present on both schemas with `None` defaults.

---

### TC-006: `TaskCreate` and `TaskUpdate` include optional `subproject_id`

**Method**: docker exec (Python import check)

**Steps**:
1. Use docker exec to run:
   `python -c "from schemas import TaskCreate, TaskUpdate; print('subproject_id' in TaskCreate.__fields__, 'subproject_id' in TaskUpdate.__fields__)"`
2. Inspect the output

**Expected result**: Outputs `True True`.

---

### TC-007: Creating a task via API still works (no regression)

**Method**: curl

**Steps**:
1. Obtain a JWT token by POSTing to `http://localhost:6002/api/auth/login` with `{"email":"admin@example.com","password":"admin123"}`
2. Use the token to create a project via `POST http://localhost:6002/api/projects` with `{"name":"Test Project"}`
3. Use the returned project ID to create a task via `POST http://localhost:6002/api/tasks` with `{"title":"Regression test","project_id":<id>}`
4. Inspect the response body

**Expected result**: HTTP 200/201 with a task JSON object containing `"subproject_id": null` and `"subproject": null` (the new optional fields, defaulting to null). No 500 errors.
