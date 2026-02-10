-- Migration: Add time tracking fields to tasks
-- Description: Adds due_date, estimated_hours, and actual_hours columns to tasks table
-- Date: 2026-02-09

-- Add time tracking columns to tasks table
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS due_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS estimated_hours NUMERIC(10, 2);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS actual_hours NUMERIC(10, 2);

-- Add index for efficient overdue queries
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);

-- Add check constraints for non-negative hours
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'check_estimated_hours_non_negative'
    ) THEN
        ALTER TABLE tasks ADD CONSTRAINT check_estimated_hours_non_negative
          CHECK (estimated_hours IS NULL OR estimated_hours >= 0);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'check_actual_hours_non_negative'
    ) THEN
        ALTER TABLE tasks ADD CONSTRAINT check_actual_hours_non_negative
          CHECK (actual_hours IS NULL OR actual_hours >= 0);
    END IF;
END $$;

-- Rollback instructions (for reference):
-- ALTER TABLE tasks DROP CONSTRAINT IF EXISTS check_actual_hours_non_negative;
-- ALTER TABLE tasks DROP CONSTRAINT IF EXISTS check_estimated_hours_non_negative;
-- DROP INDEX IF EXISTS idx_tasks_due_date;
-- ALTER TABLE tasks DROP COLUMN IF EXISTS actual_hours;
-- ALTER TABLE tasks DROP COLUMN IF EXISTS estimated_hours;
-- ALTER TABLE tasks DROP COLUMN IF EXISTS due_date;
