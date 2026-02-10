-- Initialize the task tracker database

-- Authors table
CREATE TABLE IF NOT EXISTS authors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    author_id INTEGER REFERENCES authors(id) ON DELETE SET NULL,
    search_vector TSVECTOR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Task tag enum
CREATE TYPE task_tag AS ENUM ('bug', 'feature', 'idea');

-- Task priority enum
CREATE TYPE task_priority AS ENUM ('P0', 'P1');

-- Task status enum (6-status workflow)
CREATE TYPE task_status AS ENUM ('backlog', 'todo', 'in_progress', 'blocked', 'review', 'done');

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    tag task_tag NOT NULL DEFAULT 'feature',
    priority task_priority NOT NULL DEFAULT 'P1',
    status task_status NOT NULL DEFAULT 'backlog',
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES authors(id) ON DELETE SET NULL,
    owner_id INTEGER REFERENCES authors(id) ON DELETE SET NULL,
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
    author_id INTEGER REFERENCES authors(id) ON DELETE SET NULL,
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
    uploaded_by INTEGER REFERENCES authors(id) ON DELETE SET NULL,
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
    actor_id INTEGER REFERENCES authors(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

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

-- Create indexes for better query performance
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

-- Project indexes
CREATE INDEX idx_projects_search_vector ON projects USING GIN (search_vector);

-- Comment indexes
CREATE INDEX idx_comments_task_id ON comments(task_id);
CREATE INDEX idx_comments_search_vector ON comments USING GIN (search_vector);

-- Task dependency indexes
CREATE INDEX idx_task_dependencies_blocking ON task_dependencies(blocking_task_id);
CREATE INDEX idx_task_dependencies_blocked ON task_dependencies(blocked_task_id);

-- Task attachment indexes
CREATE INDEX idx_task_attachments_task_id ON task_attachments(task_id);

-- Task event indexes
CREATE INDEX idx_task_events_task_id ON task_events(task_id);
CREATE INDEX idx_task_events_task_created ON task_events(task_id, created_at DESC);
CREATE INDEX idx_task_events_event_type ON task_events(event_type);
CREATE INDEX idx_task_events_actor_id ON task_events(actor_id);
CREATE INDEX idx_task_events_created_at ON task_events(created_at DESC);

-- Insert a default author for testing
INSERT INTO authors (name, email) VALUES ('Admin', 'admin@example.com');

-- Insert a sample project
INSERT INTO projects (name, description, author_id)
VALUES ('Sample Project', 'A sample project to get started', 1);

-- Insert sample tasks
INSERT INTO tasks (title, description, tag, priority, status, project_id, author_id)
VALUES
    ('Set up CI/CD pipeline', 'Configure GitHub Actions for automated testing and deployment', 'feature', 'P0', 'todo', 1, 1),
    ('Fix login redirect bug', 'Users are not redirected properly after login', 'bug', 'P0', 'todo', 1, 1),
    ('Add dark mode support', 'Implement dark mode toggle in settings', 'idea', 'P1', 'backlog', 1, 1);

-- Insert a sample comment
INSERT INTO comments (content, task_id, author_id)
VALUES ('This is a high priority item, need to address ASAP', 1, 1);
