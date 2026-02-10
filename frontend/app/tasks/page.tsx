'use client';

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { AlertCircle, Bug, Filter, Lightbulb, MessageSquare, Search, Sparkles } from 'lucide-react';
import { getTasks, updateTask, isOverdue, Task } from '@/lib/api';
import { STATUS_CONFIG, TaskStatus } from '@/components/StatusConfig';
import { localDateToUTC } from '@/lib/date-utils';

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [tagFilter, setTagFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [dueAfter, setDueAfter] = useState<string>('');
  const [dueBefore, setDueBefore] = useState<string>('');
  const [overdueOnly, setOverdueOnly] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<string>('');

  // Track request ID to prevent race conditions
  const requestIdRef = useRef(0);

  useEffect(() => {
    loadTasks();
  }, [statusFilter, priorityFilter, tagFilter, searchQuery, dueAfter, dueBefore, overdueOnly, sortBy]);

  const loadTasks = async () => {
    // Increment request ID for this load
    const currentRequestId = ++requestIdRef.current;

    try {
      const data = await getTasks({
        q: searchQuery || undefined,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        tag: tagFilter || undefined,
        due_after: dueAfter ? localDateToUTC(dueAfter, false) : undefined,
        due_before: dueBefore ? localDateToUTC(dueBefore, true) : undefined,
        overdue: overdueOnly || undefined
      });

      // Apply client-side sorting
      let sortedData = [...data];
      if (sortBy === 'due_asc') {
        sortedData.sort((a, b) => {
          if (!a.due_date && !b.due_date) return 0;
          if (!a.due_date) return 1;
          if (!b.due_date) return -1;
          return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
        });
      } else if (sortBy === 'due_desc') {
        sortedData.sort((a, b) => {
          if (!a.due_date && !b.due_date) return 0;
          if (!a.due_date) return 1;
          if (!b.due_date) return -1;
          return new Date(b.due_date).getTime() - new Date(a.due_date).getTime();
        });
      }

      // Only update if this is still the latest request
      if (currentRequestId === requestIdRef.current) {
        setTasks(sortedData);
      }
    } catch (error) {
      console.error('Failed to load tasks:', error);
    } finally {
      // Only update loading state if this is still the latest request
      if (currentRequestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  };

  const handleStatusChange = async (taskId: number, newStatus: TaskStatus) => {
    try {
      await updateTask(taskId, { status: newStatus });
      loadTasks();
    } catch (error) {
      console.error('Failed to update task:', error);
    }
  };

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

  const clearFilters = () => {
    setStatusFilter('');
    setPriorityFilter('');
    setTagFilter('');
    setSearchQuery('');
    setDueAfter('');
    setDueBefore('');
    setOverdueOnly(false);
    setSortBy('');
  };

  const hasFilters = statusFilter || priorityFilter || tagFilter || searchQuery || dueAfter || dueBefore || overdueOnly || sortBy;

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">All Tasks</h1>
        <p className="text-gray-600">View and manage all tasks across projects</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="space-y-4">
          {/* First row - Search and main filters */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2 text-gray-600">
              <Filter className="w-4 h-4" />
              <span className="text-sm font-medium">Filters:</span>
            </div>
            {/* Search Input */}
            <div className="relative flex-1 max-w-md">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-4 w-4 text-gray-400" />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search tasks..."
                className="w-full pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">All Status</option>
              <option value="backlog">Backlog</option>
              <option value="todo">To Do</option>
              <option value="in_progress">In Progress</option>
              <option value="blocked">Blocked</option>
              <option value="review">Review</option>
              <option value="done">Done</option>
            </select>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">All Priority</option>
              <option value="P0">P0</option>
              <option value="P1">P1</option>
            </select>
            <select
              value={tagFilter}
              onChange={(e) => setTagFilter(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">All Tags</option>
              <option value="bug">Bug</option>
              <option value="feature">Feature</option>
              <option value="idea">Idea</option>
            </select>
          </div>
          {/* Second row - Date filters, overdue checkbox, and sort */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">Due After:</label>
              <input
                type="date"
                value={dueAfter}
                onChange={(e) => setDueAfter(e.target.value)}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">Due Before:</label>
              <input
                type="date"
                value={dueBefore}
                onChange={(e) => setDueBefore(e.target.value)}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={overdueOnly}
                onChange={(e) => setOverdueOnly(e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <span className="text-sm text-gray-600">Show Overdue Only</span>
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">Sort by...</option>
              <option value="due_asc">Due Date (Ascending)</option>
              <option value="due_desc">Due Date (Descending)</option>
            </select>
            {hasFilters && (
              <button
                onClick={clearFilters}
                className="ml-auto text-sm text-indigo-600 hover:text-indigo-700 font-medium"
              >
                Clear all filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tasks List */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-4 border-b border-gray-200">
          <p className="text-sm text-gray-600">
            {tasks.length} task{tasks.length !== 1 ? 's' : ''}
            {hasFilters ? ' matching filters' : ''}
          </p>
        </div>
        <div className="divide-y divide-gray-100">
          {tasks.length === 0 ? (
            <p className="p-8 text-center text-gray-500">No tasks found</p>
          ) : (
            tasks.map((task) => (
              <div
                key={task.id}
                className="p-4 flex items-start gap-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-mono text-sm text-gray-500">#{task.id}</span>
                    {isOverdue(task) && (
                      <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" title="Overdue" />
                    )}
                    <Link
                      href={`/tasks/${task.id}`}
                      className={`font-medium hover:text-indigo-600 ${
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
                    <p className="text-sm text-gray-500 mt-1 line-clamp-1">{task.description}</p>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    <Link
                      href={`/projects/${task.project_id}`}
                      className="text-xs text-indigo-600 hover:text-indigo-700"
                    >
                      Project #{task.project_id}
                    </Link>
                    <span className="text-gray-300">•</span>
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
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
