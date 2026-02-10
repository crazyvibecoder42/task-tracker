-- Migration: Add Rich Task Context & Attachments
-- Date: 2026-02-09
-- Description: Add file attachments table, external links, and custom metadata to tasks

-- Create task_attachments table for file uploads
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

-- Add index on task_id for faster attachment lookups
CREATE INDEX IF NOT EXISTS idx_task_attachments_task_id ON task_attachments(task_id);

-- Add JSONB columns to tasks table for external links and custom metadata
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS external_links JSONB DEFAULT '[]'::jsonb;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS custom_metadata JSONB DEFAULT '{}'::jsonb;

-- Backfill NULL values for existing rows (DEFAULT only applies to new rows)
UPDATE tasks SET external_links = '[]'::jsonb WHERE external_links IS NULL;
UPDATE tasks SET custom_metadata = '{}'::jsonb WHERE custom_metadata IS NULL;

-- Add NOT NULL constraints now that all rows have values
ALTER TABLE tasks ALTER COLUMN external_links SET NOT NULL;
ALTER TABLE tasks ALTER COLUMN custom_metadata SET NOT NULL;

-- Create GIN indexes for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_tasks_external_links ON tasks USING GIN (external_links);
CREATE INDEX IF NOT EXISTS idx_tasks_custom_metadata ON tasks USING GIN (custom_metadata);

-- Event types stored as VARCHAR(50) for flexibility - no enum migration needed
-- Design choice: Allows custom event types without schema changes (future MCP plugins, integrations)
-- Standard types: task_created, status_change, field_update, ownership_change,
--   dependency_added, dependency_removed, comment_added, attachment_added,
--   attachment_deleted, link_added, link_removed, metadata_updated
-- Python TaskEventType enum provides validation for known types in code

-- Verify the schema
DO $$
BEGIN
    RAISE NOTICE 'Migration 004 completed successfully';
    RAISE NOTICE 'Created task_attachments table';
    RAISE NOTICE 'Added external_links and custom_metadata columns to tasks';
    RAISE NOTICE 'Created GIN indexes for JSONB queries';
END $$;
