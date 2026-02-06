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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Task tag enum
CREATE TYPE task_tag AS ENUM ('bug', 'feature', 'idea');

-- Task priority enum
CREATE TYPE task_priority AS ENUM ('P0', 'P1');

-- Task status enum
CREATE TYPE task_status AS ENUM ('pending', 'completed');

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    tag task_tag NOT NULL DEFAULT 'feature',
    priority task_priority NOT NULL DEFAULT 'P1',
    status task_status NOT NULL DEFAULT 'pending',
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES authors(id) ON DELETE SET NULL,
    owner_id INTEGER REFERENCES authors(id) ON DELETE SET NULL,
    parent_task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Comments table
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES authors(id) ON DELETE SET NULL,
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

-- Create indexes for better query performance
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_tag ON tasks(tag);
CREATE INDEX idx_tasks_owner_id ON tasks(owner_id);
CREATE INDEX idx_tasks_parent_task_id ON tasks(parent_task_id);
CREATE INDEX idx_comments_task_id ON comments(task_id);
CREATE INDEX idx_task_dependencies_blocking ON task_dependencies(blocking_task_id);
CREATE INDEX idx_task_dependencies_blocked ON task_dependencies(blocked_task_id);

-- Insert a default author for testing
INSERT INTO authors (name, email) VALUES ('Admin', 'admin@example.com');

-- Insert a sample project
INSERT INTO projects (name, description, author_id)
VALUES ('Sample Project', 'A sample project to get started', 1);

-- Insert sample tasks
INSERT INTO tasks (title, description, tag, priority, status, project_id, author_id)
VALUES
    ('Set up CI/CD pipeline', 'Configure GitHub Actions for automated testing and deployment', 'feature', 'P0', 'pending', 1, 1),
    ('Fix login redirect bug', 'Users are not redirected properly after login', 'bug', 'P0', 'pending', 1, 1),
    ('Add dark mode support', 'Implement dark mode toggle in settings', 'idea', 'P1', 'pending', 1, 1);

-- Insert a sample comment
INSERT INTO comments (content, task_id, author_id)
VALUES ('This is a high priority item, need to address ASAP', 1, 1);
