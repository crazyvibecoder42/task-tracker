-- Task Tracker Database Schema
-- This is the complete database schema for fresh deployments.
-- All schema changes have been consolidated into this single file.
-- For existing databases, apply this schema using: psql -U taskuser -d tasktracker -f init.sql

-- Users table (formerly authors, renamed in migration 006)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- Nullable for migrated users
    role VARCHAR(50) NOT NULL DEFAULT 'editor' CHECK (role IN ('admin', 'editor', 'viewer')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Team members table
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_id, user_id)
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    search_vector TSVECTOR,
    kanban_settings JSONB DEFAULT '{
        "wip_limits": {
            "todo": null,
            "in_progress": 5,
            "review": 3
        },
        "hidden_columns": ["backlog", "done"]
    }'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Task tag enum
CREATE TYPE task_tag AS ENUM ('bug', 'feature', 'idea');

-- Task priority enum
CREATE TYPE task_priority AS ENUM ('P0', 'P1');

-- Task status enum (6-status workflow)
CREATE TYPE task_status AS ENUM ('backlog', 'todo', 'in_progress', 'blocked', 'review', 'done', 'not_needed');

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    tag task_tag NOT NULL DEFAULT 'feature',
    priority task_priority NOT NULL DEFAULT 'P1',
    status task_status NOT NULL DEFAULT 'todo',
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    parent_task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    search_vector TSVECTOR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Time tracking fields
    due_date TIMESTAMP WITH TIME ZONE,
    estimated_hours NUMERIC(10, 2) CHECK (estimated_hours IS NULL OR estimated_hours >= 0),
    actual_hours NUMERIC(10, 2) CHECK (actual_hours IS NULL OR actual_hours >= 0),
    -- Rich context fields
    external_links JSONB NOT NULL DEFAULT '[]'::jsonb,
    custom_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Comments table
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    search_vector TSVECTOR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Task dependencies table for blocking relationships
CREATE TABLE IF NOT EXISTS task_dependencies (
    id SERIAL PRIMARY KEY,
    blocking_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    blocked_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(blocking_task_id, blocked_task_id),
    CHECK (blocking_task_id != blocked_task_id)
);

-- Task attachments table for file uploads
CREATE TABLE IF NOT EXISTS task_attachments (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(512) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Task events table for audit trail
CREATE TABLE IF NOT EXISTS task_events (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Project members table for project-level permissions
CREATE TABLE IF NOT EXISTS project_members (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'editor' CHECK (role IN ('owner', 'editor', 'viewer')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);

-- API keys table for programmatic access
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    project_ids JSONB DEFAULT '[]',
    permissions JSONB DEFAULT '[]',
    rate_limit INTEGER,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Refresh tokens table for JWT token management
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============== Sub-Projects ==============
-- To apply to live environments without a full reset, run:
--   ALTER TABLE subprojects ... (table creation cannot be done with ALTER; use CREATE TABLE below)
--   ALTER TABLE tasks ADD COLUMN IF NOT EXISTS subproject_id INTEGER REFERENCES subprojects(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS subprojects (
    id                 SERIAL PRIMARY KEY,
    project_id         INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name               VARCHAR(255) NOT NULL,
    subproject_number  INTEGER NOT NULL,
    is_default         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (project_id, subproject_number)
);

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS subproject_id INTEGER REFERENCES subprojects(id) ON DELETE SET NULL;

-- ============== Full-Text Search Setup ==============

-- Function to update task search vector
-- Combines title (weight A), description (weight B), and tag (weight C)
CREATE OR REPLACE FUNCTION tasks_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(NEW.tag::text, '')), 'C');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

-- Function to update project search vector
-- Combines name (weight A) and description (weight B)
CREATE OR REPLACE FUNCTION projects_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

-- Function to update comment search vector
-- Uses content only (weight A)
CREATE OR REPLACE FUNCTION comments_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.content, '')), 'A');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

-- Create triggers for automatic search_vector updates
CREATE TRIGGER tasks_search_vector_trigger
BEFORE INSERT OR UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION tasks_search_vector_update();

CREATE TRIGGER projects_search_vector_trigger
BEFORE INSERT OR UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION projects_search_vector_update();

CREATE TRIGGER comments_search_vector_trigger
BEFORE INSERT OR UPDATE ON comments
FOR EACH ROW
EXECUTE FUNCTION comments_search_vector_update();

-- ============== Indexes for Performance ==============

-- User indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Team indexes
CREATE INDEX idx_teams_created_by ON teams(created_by);
CREATE INDEX idx_teams_name ON teams(name);

-- Team member indexes
CREATE INDEX idx_team_members_team_id ON team_members(team_id);
CREATE INDEX idx_team_members_user_id ON team_members(user_id);
CREATE INDEX idx_team_members_team_role ON team_members(team_id, role);

-- Project indexes
CREATE INDEX idx_projects_author_id ON projects(author_id);
CREATE INDEX idx_projects_team_id ON projects(team_id);
CREATE INDEX idx_projects_search_vector ON projects USING GIN (search_vector);
CREATE INDEX idx_projects_kanban_settings ON projects USING GIN (kanban_settings);

-- Task indexes
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_tag ON tasks(tag);
CREATE INDEX idx_tasks_owner_id ON tasks(owner_id);
CREATE INDEX idx_tasks_parent_task_id ON tasks(parent_task_id);
CREATE INDEX idx_tasks_project_status ON tasks(project_id, status);
CREATE INDEX idx_tasks_status_priority ON tasks(status, priority);
CREATE INDEX idx_tasks_owner_status ON tasks(owner_id, status) WHERE owner_id IS NOT NULL;
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_tasks_search_vector ON tasks USING GIN (search_vector);
CREATE INDEX idx_tasks_external_links ON tasks USING GIN (external_links);
CREATE INDEX idx_tasks_custom_metadata ON tasks USING GIN (custom_metadata);

-- Comment indexes
CREATE INDEX idx_comments_task_id ON comments(task_id);
CREATE INDEX idx_comments_author_id ON comments(author_id);
CREATE INDEX idx_comments_search_vector ON comments USING GIN (search_vector);

-- Task dependency indexes
CREATE INDEX idx_task_dependencies_blocking ON task_dependencies(blocking_task_id);
CREATE INDEX idx_task_dependencies_blocked ON task_dependencies(blocked_task_id);

-- Task attachment indexes
CREATE INDEX idx_task_attachments_task_id ON task_attachments(task_id);
CREATE INDEX idx_task_attachments_uploaded_by ON task_attachments(uploaded_by);

-- Task event indexes
CREATE INDEX idx_task_events_task_id ON task_events(task_id);
CREATE INDEX idx_task_events_task_created ON task_events(task_id, created_at DESC);
CREATE INDEX idx_task_events_event_type ON task_events(event_type);
CREATE INDEX idx_task_events_actor_id ON task_events(actor_id);
CREATE INDEX idx_task_events_created_at ON task_events(created_at DESC);

-- Project member indexes
CREATE INDEX idx_project_members_project_id ON project_members(project_id);
CREATE INDEX idx_project_members_user_id ON project_members(user_id);

-- API key indexes
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);

-- Refresh token indexes
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_jti ON refresh_tokens(token_jti);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- ============== Sample Data ==============

-- Note: Admin user is now created by backend startup event (main.py)
-- This ensures the password can be configured via ADMIN_PASSWORD env var
-- Default: admin@example.com / admin123 (for local dev only)
-- Production: Set ADMIN_PASSWORD env var to use custom password

-- Note: Sample data (projects, tasks, comments) is now created by backend startup event
-- This ensures proper foreign key relationships after admin user creation
