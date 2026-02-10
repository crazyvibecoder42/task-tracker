'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCorners
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { Task, Author, getProject, updateTask, getKanbanSettings, getAuthors, KanbanSettings } from '@/lib/api';
import { groupTasks, getColumnLabel, GroupingType, STATUS_ORDER } from '@/lib/kanban-utils';
import KanbanColumn from '@/components/KanbanColumn';
import KanbanCard from '@/components/KanbanCard';
import { ArrowLeft, Grid3x3, Users, Flag, Eye, EyeOff } from 'lucide-react';
import Link from 'next/link';

const LOG_LEVEL = process.env.NEXT_PUBLIC_LOG_LEVEL || 'INFO';

function log(level: string, message: string, data?: any) {
  const levels = ['DEBUG', 'INFO', 'CRITICAL'];
  const currentLevelIndex = levels.indexOf(LOG_LEVEL);
  const messageLevelIndex = levels.indexOf(level);

  if (messageLevelIndex >= currentLevelIndex) {
    const logMessage = `[${level}] [KanbanBoard] ${message}`;
    if (data) {
      console.log(logMessage, data);
    } else {
      console.log(logMessage);
    }
  }
}

export default function KanbanBoardPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = parseInt(params.id as string);

  const [project, setProject] = useState<any>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [authors, setAuthors] = useState<Author[]>([]);
  const [kanbanSettings, setKanbanSettings] = useState<KanbanSettings>({
    wip_limits: {},
    hidden_columns: ['backlog', 'done']
  });
  const [groupBy, setGroupBy] = useState<GroupingType>('status');
  const [showHidden, setShowHidden] = useState(false);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 }
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates
    })
  );

  // Load data
  useEffect(() => {
    log('DEBUG', 'Initializing Kanban board', { projectId });
    loadData();
    loadKanbanSettings();

    // Load groupBy preference from localStorage
    const savedGroupBy = localStorage.getItem(`kanban-groupby-${projectId}`);
    if (savedGroupBy) {
      log('DEBUG', 'Loaded groupBy preference from localStorage', { savedGroupBy });
      setGroupBy(savedGroupBy as GroupingType);
    }
  }, [projectId]);

  const loadData = async () => {
    try {
      log('DEBUG', 'Loading project data', { projectId });
      const [data, authorsData] = await Promise.all([
        getProject(projectId),
        getAuthors()
      ]);
      log('INFO', 'Project data loaded successfully', {
        taskCount: data.tasks?.length || 0,
        projectName: data.name,
        authorCount: authorsData.length
      });
      setProject(data);
      setTasks(data.tasks || []);
      setAuthors(authorsData);
      setError(null);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load project';
      log('CRITICAL', 'Failed to load project data', { error: errorMessage });
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const loadKanbanSettings = async () => {
    try {
      log('DEBUG', 'Loading kanban settings', { projectId });
      const settings = await getKanbanSettings(projectId);
      log('INFO', 'Kanban settings loaded', {
        wipLimits: settings.wip_limits,
        hiddenColumns: settings.hidden_columns
      });
      setKanbanSettings(settings);
    } catch (error) {
      log('INFO', 'Failed to load kanban settings, using defaults', {
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      // Use default settings if API call fails
    }
  };

  // Handle drag start
  const handleDragStart = (event: DragStartEvent) => {
    const taskId = parseInt(event.active.id as string);
    const task = tasks.find(t => t.id === taskId);
    log('DEBUG', 'Drag started', { taskId, taskTitle: task?.title });
    setActiveTask(task || null);
  };

  // Handle drag end
  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTask(null);

    if (!over) {
      log('DEBUG', 'Drag cancelled - no drop target');
      return;
    }

    // Get the column ID from the sortable container, not the dragged item
    // This prevents writing task IDs as status/owner/priority values
    const newColumnId = over.data?.current?.sortable?.containerId ?? (over.id as string);

    // Guard against dropping on a task instead of a column
    const taskId = parseInt(active.id as string);
    if (newColumnId === active.id.toString()) {
      log('DEBUG', 'Drag cancelled - dropped on same position');
      return;
    }

    const task = tasks.find(t => t.id === taskId);

    if (!task) {
      log('INFO', 'Task not found for drag operation', { taskId });
      return;
    }

    // Validate column ID is valid for current grouping mode
    const validColumnIds = Object.keys(groupedTasks);
    if (!validColumnIds.includes(newColumnId)) {
      log('INFO', 'Invalid drop target - not a valid column', {
        newColumnId,
        validColumns: validColumnIds,
        groupBy
      });
      return;
    }

    log('DEBUG', 'Processing drag end', {
      taskId,
      taskTitle: task.title,
      groupBy,
      newColumnId,
      containerId: over.data?.current?.sortable?.containerId
    });

    // Determine what field to update based on grouping
    type TaskUpdate = Parameters<typeof updateTask>[1];
    const updates: TaskUpdate = {};

    if (groupBy === 'status') {
      updates.status = newColumnId as Task['status'];
      log('DEBUG', 'Updating task status', {
        oldStatus: task.status,
        newStatus: newColumnId
      });
    } else if (groupBy === 'owner') {
      updates.owner_id = newColumnId === 'unassigned' ? null : parseInt(newColumnId.replace('owner-', ''));
      log('DEBUG', 'Updating task owner', {
        oldOwner: task.owner_id,
        newOwner: updates.owner_id
      });
    } else if (groupBy === 'priority') {
      updates.priority = newColumnId as Task['priority'];
      log('DEBUG', 'Updating task priority', {
        oldPriority: task.priority,
        newPriority: newColumnId
      });
    }

    // Optimistic update
    setTasks(prevTasks => {
      const updatedTask = { ...task, ...updates };
      const newTasks = prevTasks.map(t => t.id === taskId ? updatedTask : t);
      log('DEBUG', 'Applied optimistic update', { taskId });
      return newTasks;
    });

    // API call
    try {
      log('DEBUG', 'Sending update to backend', { taskId, updates });
      await updateTask(taskId, updates);
      log('CRITICAL', 'Task updated successfully', { taskId, updates });

      // Reload to get server state
      await loadData();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update task';
      log('CRITICAL', 'Failed to update task, rolling back', {
        taskId,
        error: errorMessage
      });
      setError(`Failed to update task: ${errorMessage}`);

      // Rollback on error
      await loadData();
    }
  };

  // Change grouping
  const handleGroupByChange = (newGroupBy: GroupingType) => {
    log('INFO', 'Changing grouping mode', {
      oldGroupBy: groupBy,
      newGroupBy
    });
    setGroupBy(newGroupBy);
    localStorage.setItem(`kanban-groupby-${projectId}`, newGroupBy);
    log('DEBUG', 'Saved groupBy preference to localStorage', { newGroupBy });
  };

  // Toggle hidden columns
  const handleToggleHidden = () => {
    const newShowHidden = !showHidden;
    log('INFO', 'Toggling hidden columns', { showHidden: newShowHidden });
    setShowHidden(newShowHidden);
  };

  // Group tasks
  const groupedTasks = groupTasks(tasks, groupBy, authors);
  const allColumns = Object.keys(groupedTasks);
  const visibleColumns = allColumns.filter(columnId => {
    if (showHidden) return true;
    return !kanbanSettings.hidden_columns.includes(columnId);
  });

  log('DEBUG', 'Rendering board', {
    totalTasks: tasks.length,
    groupBy,
    totalColumns: allColumns.length,
    visibleColumns: visibleColumns.length,
    showHidden
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          <p className="mt-2 text-gray-600">Loading Kanban board...</p>
        </div>
      </div>
    );
  }

  if (error && !project) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 font-medium">Error loading project</p>
          <p className="text-gray-600 mt-2">{error}</p>
          <button
            onClick={() => router.push('/projects')}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            Back to Projects
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="max-w-screen-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href={`/projects/${projectId}`}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              Back to List
            </Link>
            <h1 className="text-2xl font-bold text-gray-900">
              {project?.name || 'Project'} - Board View
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Group By Selector */}
            <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => handleGroupByChange('status')}
                className={`px-3 py-1.5 rounded flex items-center gap-2 text-sm font-medium transition-colors ${
                  groupBy === 'status'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
                title="Group by status"
              >
                <Grid3x3 className="w-4 h-4" />
                Status
              </button>
              <button
                onClick={() => handleGroupByChange('owner')}
                className={`px-3 py-1.5 rounded flex items-center gap-2 text-sm font-medium transition-colors ${
                  groupBy === 'owner'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
                title="Group by owner"
              >
                <Users className="w-4 h-4" />
                Owner
              </button>
              <button
                onClick={() => handleGroupByChange('priority')}
                className={`px-3 py-1.5 rounded flex items-center gap-2 text-sm font-medium transition-colors ${
                  groupBy === 'priority'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
                title="Group by priority"
              >
                <Flag className="w-4 h-4" />
                Priority
              </button>
            </div>

            {/* Show/Hide Columns */}
            <button
              onClick={handleToggleHidden}
              className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded flex items-center gap-2 text-sm font-medium text-gray-700 transition-colors"
              title={showHidden ? 'Hide inactive columns' : 'Show all columns'}
            >
              {showHidden ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              {showHidden ? 'Hide Inactive' : 'Show All'}
            </button>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 p-3">
          <div className="max-w-screen-2xl mx-auto">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Kanban Board */}
      <div className="p-4 overflow-x-auto">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-4 min-w-max">
            {visibleColumns.map(columnId => (
              <KanbanColumn
                key={columnId}
                columnId={columnId}
                title={getColumnLabel(columnId, groupBy, tasks)}
                tasks={groupedTasks[columnId] || []}
                kanbanSettings={kanbanSettings}
                onConfigureWip={(col) => {
                  log('INFO', 'Configure WIP limit clicked', { column: col });
                  alert(`Configure WIP limit for ${col} (feature coming soon)`);
                }}
              />
            ))}
          </div>

          <DragOverlay>
            {activeTask && <KanbanCard task={activeTask} isDragging />}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Empty State */}
      {tasks.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">No tasks in this project yet</p>
          <Link
            href={`/projects/${projectId}`}
            className="mt-4 inline-block px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            View Project Details
          </Link>
        </div>
      )}
    </div>
  );
}
