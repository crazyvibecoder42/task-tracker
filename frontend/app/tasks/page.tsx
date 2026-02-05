'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Bug, CheckCircle2, Circle, Filter, Lightbulb, MessageSquare, Sparkles } from 'lucide-react';
import { getTasks, updateTask, Task } from '@/lib/api';

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [tagFilter, setTagFilter] = useState<string>('');

  useEffect(() => {
    loadTasks();
  }, [statusFilter, priorityFilter, tagFilter]);

  const loadTasks = async () => {
    try {
      const data = await getTasks({
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        tag: tagFilter || undefined
      });
      setTasks(data);
    } catch (error) {
      console.error('Failed to load tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (task: Task) => {
    try {
      await updateTask(task.id, {
        status: task.status === 'pending' ? 'completed' : 'pending'
      });
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
  };

  const hasFilters = statusFilter || priorityFilter || tagFilter;

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
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 text-gray-600">
            <Filter className="w-4 h-4" />
            <span className="text-sm font-medium">Filters:</span>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
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
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="text-sm text-indigo-600 hover:text-indigo-700"
            >
              Clear filters
            </button>
          )}
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
                <button
                  onClick={() => handleToggleStatus(task)}
                  className={`mt-1 flex-shrink-0 ${
                    task.status === 'completed' ? 'text-green-600' : 'text-gray-400'
                  }`}
                >
                  {task.status === 'completed' ? (
                    <CheckCircle2 className="w-5 h-5" />
                  ) : (
                    <Circle className="w-5 h-5" />
                  )}
                </button>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <Link
                      href={`/tasks/${task.id}`}
                      className={`font-medium hover:text-indigo-600 ${
                        task.status === 'completed' ? 'line-through text-gray-500' : 'text-gray-900'
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
