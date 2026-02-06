-- Migration: Add task dependencies and subtasks support
-- Description: Adds parent_task_id column to tasks table and creates task_dependencies table
-- Date: 2026-02-06

-- Add parent_task_id column to tasks table
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS parent_task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE;

-- Create task_dependencies table for blocking relationships
CREATE TABLE IF NOT EXISTS task_dependencies (
    id SERIAL PRIMARY KEY,
    blocking_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    blocked_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(blocking_task_id, blocked_task_id),
    CHECK (blocking_task_id != blocked_task_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_tasks_parent_task_id ON tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_blocking ON task_dependencies(blocking_task_id);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_blocked ON task_dependencies(blocked_task_id);

-- Rollback instructions (for reference):
-- DROP INDEX IF EXISTS idx_task_dependencies_blocked;
-- DROP INDEX IF EXISTS idx_task_dependencies_blocking;
-- DROP INDEX IF EXISTS idx_tasks_parent_task_id;
-- DROP TABLE IF EXISTS task_dependencies;
-- ALTER TABLE tasks DROP COLUMN IF EXISTS parent_task_id;
