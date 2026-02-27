'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  AlertCircle,
  ArrowLeft,
  Bug,
  Grid3x3,
  Lightbulb,
  MessageSquare,
  Plus,
  Search,
  Settings,
  Sparkles,
  Trash2
} from 'lucide-react';
import { STATUS_CONFIG, TaskStatus } from '@/components/StatusConfig';
import {
  getProject,
  getProjectStats,
  getTasks,
  getProjectMembers,
  getSubprojects,
  createTask,
  updateTask,
  deleteTask,
  deleteProject,
  Project,
  ProjectStats,
  Task,
  Author,
  Subproject
} from '@/lib/api';
import { localInputToUTC } from '@/lib/date-utils';

export default function ProjectDetail() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = Number(params.id);
  const activeSubprojectParam = searchParams?.get('subproject'); // null | '0' | numeric string
  const activeSubprojectId = (() => {
    if (activeSubprojectParam === null) return undefined;
    if (activeSubprojectParam === '0') return 0;
    if (/^[1-9]\d*$/.test(activeSubprojectParam)) return Number(activeSubprojectParam);
    return undefined; // invalid param (e.g. 'abc') — treat as no filter
  })();

  const [project, setProject] = useState<Project | null>(null);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [authors, setAuthors] = useState<Author[]>([]);
  const [subprojects, setSubprojects] = useState<Subproject[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewTask, setShowNewTask] = useState(false);
  const [filter, setFilter] = useState<'all' | TaskStatus>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<Task[] | null>(null);

  // New task form
  const [newTitle, setNewTitle] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newTag, setNewTag] = useState<'bug' | 'feature' | 'idea'>('feature');
  const [newPriority, setNewPriority] = useState<'P0' | 'P1'>('P1');
  const [newDueDate, setNewDueDate] = useState('');
  const [newEstimatedHours, setNewEstimatedHours] = useState('');
  const [newSubprojectId, setNewSubprojectId] = useState<number | null>(null);

  useEffect(() => {
    loadProject();
    // Load project members instead of all system users (requires viewer access, not admin)
    getProjectMembers(projectId)
      .then(members => setAuthors(members.map(m => m.user)))
      .catch(() => setAuthors([])); // Graceful degradation on error
    getSubprojects(projectId)
      .then(setSubprojects)
      .catch(() => {});
  }, [projectId]);

  // Track search request ID to prevent race conditions
  const searchRequestIdRef = useRef(0);

  // Search effect - trigger search when query changes
  useEffect(() => {
    if (searchQuery.trim()) {
      // Increment request ID for this search
      const currentRequestId = ++searchRequestIdRef.current;

      // Perform search
      const performSearch = async () => {
        try {
          const results = await getTasks({
            project_id: projectId,
            subproject_id: activeSubprojectId,
            q: searchQuery.trim()
          });

          // Only update if this is still the latest request
          if (currentRequestId === searchRequestIdRef.current) {
            setSearchResults(results);
          }
        } catch (error) {
          console.error('Failed to search tasks:', error);
          // Only update error state if this is still the latest request
          if (currentRequestId === searchRequestIdRef.current) {
            setSearchResults([]);
          }
        }
      };
      performSearch();
    } else {
      // Clear search results when query is empty
      // Increment request ID to invalidate any in-flight requests
      searchRequestIdRef.current++;
      setSearchResults(null);
    }
  }, [searchQuery, projectId, activeSubprojectId]);

  // Clear search query when sub-project filter changes
  useEffect(() => {
    setSearchQuery('');
  }, [activeSubprojectParam]);

  const loadProject = async () => {
    try {
      const [projectData, statsData] = await Promise.all([
        getProject(projectId),
        getProjectStats(projectId)
      ]);
      setProject(projectData);
      setStats(statsData);
    } catch (error) {
      console.error('Failed to load project:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    try {
      await createTask({
        project_id: projectId,
        title: newTitle.trim(),
        description: newDescription.trim() || undefined,
        tag: newTag,
        priority: newPriority,
        due_date: newDueDate ? localInputToUTC(newDueDate) : undefined,
        estimated_hours: newEstimatedHours !== '' ? parseFloat(newEstimatedHours) : undefined,
        subproject_id: newSubprojectId ?? undefined,
      });
      setNewTitle('');
      setNewDescription('');
      setNewTag('feature');
      setNewPriority('P1');
      setNewDueDate('');
      setNewEstimatedHours('');
      setNewSubprojectId(activeSubprojectId && activeSubprojectId > 0 ? activeSubprojectId : null);
      setShowNewTask(false);
      loadProject();
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  const handleStatusChange = async (taskId: number, newStatus: TaskStatus) => {
    try {
      await updateTask(taskId, { status: newStatus });
      loadProject();
    } catch (error) {
      console.error('Failed to update task:', error);
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    if (!confirm('Are you sure you want to delete this task?')) return;
    try {
      await deleteTask(taskId);
      loadProject();
    } catch (error) {
      console.error('Failed to delete task:', error);
    }
  };

  const handleDeleteProject = async () => {
    if (!confirm('Are you sure you want to delete this project and all its tasks?')) return;
    try {
      await deleteProject(projectId);
      router.push('/');
    } catch (error) {
      console.error('Failed to delete project:', error);
    }
  };

  // Apply subproject filter to a task list
  const filterBySubproject = (tasks: Task[]) => {
    if (activeSubprojectParam === null) return tasks;
    if (activeSubprojectParam === '0') return tasks.filter(t => !t.subproject_id);
    if (!/^[1-9]\d*$/.test(activeSubprojectParam)) return tasks; // invalid param → show all
    return tasks.filter(t => t.subproject_id === Number(activeSubprojectParam));
  };

  // Use search results if searching, otherwise use project tasks; then apply subproject filter
  const tasksToFilter = filterBySubproject(
    searchResults !== null ? searchResults : (project?.tasks || [])
  );

  const filteredTasks = tasksToFilter.filter((task) => {
    if (filter === 'all') return true;
    return task.status === filter;
  }).sort((a, b) => {
    // When searching, results are already sorted by relevance
    // Otherwise, sort by updated_at descending (most recent first)
    if (searchResults !== null) return 0;  // Keep backend relevance order
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });

  const getTagIcon = (tag: string) => {
    switch (tag) {
      case 'bug':
        return <Bug className="w-4 h-4" />;
      case 'feature':
        return <Sparkles className="w-4 h-4" />;
      case 'idea':
        return <Lightbulb className="w-4 h-4" />;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-8">
        <p className="text-gray-500">Project not found</p>
        <Link href="/" className="text-indigo-600 hover:text-indigo-700">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="p-8">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </Link>

      {/* Project Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
          {project.description && (
            <p className="text-gray-600 mt-1">{project.description}</p>
          )}
          {project.team && (
            <div className="flex items-center gap-2 mt-2">
              <span className="text-sm text-gray-500">Team:</span>
              <Link
                href={`/teams/${project.team.id}`}
                className="inline-flex items-center gap-1 px-2 py-1 text-sm bg-indigo-50 text-indigo-700 rounded-md hover:bg-indigo-100"
              >
                {project.team.name}
              </Link>
            </div>
          )}
          {!project.team && (
            <p className="text-sm text-gray-500 mt-2">Personal Project</p>
          )}
          {project.author && (
            <p className="text-sm text-gray-500 mt-2">
              Created by {project.author.name}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={`/projects/${projectId}/board`}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2"
          >
            <Grid3x3 className="w-5 h-5" />
            Board View
          </Link>
          <Link
            href={`/projects/${projectId}/settings`}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2"
          >
            <Settings className="w-5 h-5" />
            Settings
          </Link>
          <button
            onClick={handleDeleteProject}
            className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
            title="Delete project"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-8">
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-500">Total</p>
            <p className="text-xl font-bold">{stats.total_tasks}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-500">Backlog</p>
            <p className="text-xl font-bold text-gray-600">{stats.backlog_tasks}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-500">To Do</p>
            <p className="text-xl font-bold text-blue-600">{stats.todo_tasks}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-500">In Progress</p>
            <p className="text-xl font-bold text-yellow-600">{stats.in_progress_tasks}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-500">Blocked</p>
            <p className="text-xl font-bold text-red-600">{stats.blocked_tasks}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-500">Review</p>
            <p className="text-xl font-bold text-purple-600">{stats.review_tasks}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-500">Done</p>
            <p className="text-xl font-bold text-green-600">{stats.done_tasks}</p>
          </div>
        </div>
      )}

      {/* Tasks Section */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-4 border-b border-gray-200">
          {/* Header row with title and Add Task button */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold">Tasks</h2>
              {activeSubprojectId !== undefined && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-sm bg-indigo-100 text-indigo-700 rounded-full">
                  {activeSubprojectId === 0
                    ? 'Unassigned'
                    : (subprojects.find(sp => sp.id === activeSubprojectId)?.name ?? `Sub-project ${activeSubprojectId}`)
                  }
                  <button
                    onClick={() => router.replace(`/projects/${projectId}`)}
                    className="ml-0.5 font-bold hover:text-indigo-900"
                    title="Clear filter"
                  >
                    ×
                  </button>
                </span>
              )}
            </div>
            <button
              onClick={() => {
                if (!showNewTask) {
                  setNewSubprojectId(activeSubprojectId && activeSubprojectId > 0 ? activeSubprojectId : null);
                }
                setShowNewTask(!showNewTask);
              }}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              <Plus className="w-4 h-4" />
              Add Task
            </button>
          </div>

          {/* Search bar and filters row */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Search Input */}
            <div className="relative flex-1 min-w-[240px] max-w-md">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-4 w-4 text-gray-400" />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search tasks in this project..."
                className="w-full pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            {/* Status filter buttons */}
            <div className="flex gap-1 flex-wrap">
              <button
                onClick={() => setFilter('all')}
                className={`px-3 py-1 text-sm rounded-lg ${
                  filter === 'all'
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                All
              </button>
              {(Object.keys(STATUS_CONFIG) as TaskStatus[]).map((status) => (
                <button
                  key={status}
                  onClick={() => setFilter(status)}
                  className={`px-3 py-1 text-sm rounded-lg ${
                    filter === status
                      ? 'bg-indigo-100 text-indigo-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {STATUS_CONFIG[status].label}
                </button>
              ))}
            </div>

            {/* Clear search button (only show when searching) */}
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
              >
                Clear search
              </button>
            )}
          </div>
        </div>

        {/* New Task Form */}
        {showNewTask && (
          <form onSubmit={handleCreateTask} className="p-4 bg-gray-50 border-b border-gray-200">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="Task title *"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="flex gap-2">
                <select
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value as any)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="feature">Feature</option>
                  <option value="bug">Bug</option>
                  <option value="idea">Idea</option>
                </select>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value as any)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="P1">P1</option>
                  <option value="P0">P0</option>
                </select>
              </div>
            </div>
            <div className="mt-4">
              <textarea
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="Description (optional)"
                rows={2}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            {/* Time Tracking Fields */}
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Due Date
                </label>
                <input
                  type="datetime-local"
                  value={newDueDate}
                  onChange={(e) => setNewDueDate(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Estimated Hours
                </label>
                <input
                  type="number"
                  step="0.25"
                  min="0"
                  value={newEstimatedHours}
                  onChange={(e) => setNewEstimatedHours(e.target.value)}
                  placeholder="5.5"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
            {/* Sub-project Field */}
            {subprojects.length > 0 && (
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Sub-project
                </label>
                <select
                  value={newSubprojectId ?? ''}
                  onChange={(e) => setNewSubprojectId(e.target.value ? Number(e.target.value) : null)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">No sub-project</option>
                  {subprojects.map(sp => (
                    <option key={sp.id} value={sp.id}>{sp.name}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="mt-4 flex gap-2">
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                Create Task
              </button>
              <button
                type="button"
                onClick={() => setShowNewTask(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Task List */}
        <div className="divide-y divide-gray-100">
          {filteredTasks.length === 0 ? (
            <p className="p-8 text-center text-gray-500">
              {searchQuery
                ? `No tasks found matching "${searchQuery}"`
                : `No tasks ${filter !== 'all' ? `with status "${filter}"` : ''} yet`
              }
            </p>
          ) : (
            filteredTasks.map((task) => (
              <div
                key={task.id}
                className="relative p-4 flex items-start gap-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-mono text-sm text-gray-500">#{task.id}</span>
                    <Link
                      href={`/tasks/${task.id}`}
                      className={`font-medium hover:text-indigo-600 before:absolute before:inset-0 ${
                        task.status === 'done' ? 'line-through text-gray-500' : 'text-gray-900'
                      }`}
                    >
                      {task.title}
                    </Link>
                    {task.owner && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-indigo-50 text-indigo-700 rounded-full border border-indigo-200">
                        👤 {task.owner.name}
                      </span>
                    )}
                    {!task.owner && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs text-gray-400 bg-gray-50 rounded-full border border-gray-200">
                        Unassigned
                      </span>
                    )}
                  </div>
                  {task.description && (
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">{task.description}</p>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    {(() => {
                      const StatusIcon = STATUS_CONFIG[task.status].icon;
                      return (
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full border ${STATUS_CONFIG[task.status].color}`}>
                          <StatusIcon className="w-3 h-3" />
                          {STATUS_CONFIG[task.status].label}
                        </span>
                      );
                    })()}
                    <span className="text-gray-300">•</span>
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full ${
                        task.tag === 'bug'
                          ? 'bg-red-100 text-red-700'
                          : task.tag === 'feature'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-purple-100 text-purple-700'
                      }`}
                    >
                      {getTagIcon(task.tag)}
                      {task.tag}
                    </span>
                    <span
                      className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                        task.priority === 'P0'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {task.priority}
                    </span>
                    {task.is_blocked && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700 border border-red-200">
                        <AlertCircle className="w-3 h-3" />
                        Blocked
                      </span>
                    )}
                    {task.subproject && activeSubprojectParam === null && (
                      <span className="inline-flex items-center px-2 py-0.5 text-xs rounded-full bg-violet-100 text-violet-700 border border-violet-200">
                        {task.subproject.name}
                      </span>
                    )}
                    {task.author && (
                      <span className="text-xs text-gray-500">by {task.author.name}</span>
                    )}
                    {(task.comment_count || 0) > 0 && (
                      <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                        <MessageSquare className="w-3 h-3" />
                        {task.comment_count}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteTask(task.id)}
                  className="relative z-10 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
