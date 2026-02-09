-- Full-text search migration for Task Tracker
-- Adds search_vector columns, indexes, and triggers for tasks, projects, and comments

-- ============== Step 1: Add search_vector columns ==============

-- Add search_vector to tasks table
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Add search_vector to projects table
ALTER TABLE projects ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Add search_vector to comments table
ALTER TABLE comments ADD COLUMN IF NOT EXISTS search_vector tsvector;


-- ============== Step 2: Create update functions ==============

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


-- ============== Step 3: Create triggers ==============

-- Drop existing triggers if they exist (idempotent)
DROP TRIGGER IF EXISTS tasks_search_vector_trigger ON tasks;
DROP TRIGGER IF EXISTS projects_search_vector_trigger ON projects;
DROP TRIGGER IF EXISTS comments_search_vector_trigger ON comments;

-- Create trigger for tasks
CREATE TRIGGER tasks_search_vector_trigger
BEFORE INSERT OR UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION tasks_search_vector_update();

-- Create trigger for projects
CREATE TRIGGER projects_search_vector_trigger
BEFORE INSERT OR UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION projects_search_vector_update();

-- Create trigger for comments
CREATE TRIGGER comments_search_vector_trigger
BEFORE INSERT OR UPDATE ON comments
FOR EACH ROW
EXECUTE FUNCTION comments_search_vector_update();


-- ============== Step 4: Populate existing rows ==============

-- Update existing tasks
UPDATE tasks SET search_vector =
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(tag::text, '')), 'C');

-- Update existing projects
UPDATE projects SET search_vector =
    setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'B');

-- Update existing comments
UPDATE comments SET search_vector =
    setweight(to_tsvector('english', coalesce(content, '')), 'A');


-- ============== Step 5: Create GIN indexes ==============

-- GIN indexes for fast full-text search
CREATE INDEX IF NOT EXISTS idx_tasks_search_vector ON tasks USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_projects_search_vector ON projects USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_comments_search_vector ON comments USING GIN(search_vector);


-- ============== Step 6: Create composite indexes for common filters ==============

-- Composite index for tasks: project + status + search queries
CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project_id, status);

-- Composite index for tasks: status + priority + search queries
CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks(status, priority);

-- Composite index for tasks: owner + status for assigned task queries
CREATE INDEX IF NOT EXISTS idx_tasks_owner_status ON tasks(owner_id, status) WHERE owner_id IS NOT NULL;


-- ============== Verification Queries ==============

-- Verify search_vector columns exist and are populated
-- SELECT COUNT(*) as total_tasks, COUNT(search_vector) as tasks_with_vectors FROM tasks;
-- SELECT COUNT(*) as total_projects, COUNT(search_vector) as projects_with_vectors FROM projects;
-- SELECT COUNT(*) as total_comments, COUNT(search_vector) as comments_with_vectors FROM comments;

-- Test search functionality
-- SELECT id, title, ts_rank(search_vector, to_tsquery('english', 'bug')) as rank
-- FROM tasks
-- WHERE search_vector @@ to_tsquery('english', 'bug')
-- ORDER BY rank DESC;
