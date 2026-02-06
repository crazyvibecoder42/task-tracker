'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Bug,
  CheckCircle2,
  Circle,
  Lightbulb,
  MessageSquare,
  Plus,
  Sparkles,
  Trash2
} from 'lucide-react';
import {
  getProject,
  getProjectStats,
  getAuthors,
  createTask,
  updateTask,
  deleteTask,
  deleteProject,
  Project,
  ProjectStats,
  Task,
  Author
} from '@/lib/api';

export default function ProjectDetail() {
  const params = useParams();
  const router = useRouter();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [authors, setAuthors] = useState<Author[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewTask, setShowNewTask] = useState(false);
  const [filter, setFilter] = useState<'all' | 'pending' | 'completed'>('all');

  // New task form
  const [newTitle, setNewTitle] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newTag, setNewTag] = useState<'bug' | 'feature' | 'idea'>('feature');
  const [newPriority, setNewPriority] = useState<'P0' | 'P1'>('P1');
  const [newAuthorId, setNewAuthorId] = useState<number | undefined>();

  useEffect(() => {
    loadProject();
    getAuthors().then(setAuthors).catch(console.error);
  }, [projectId]);

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
        author_id: newAuthorId
      });
      setNewTitle('');
      setNewDescription('');
      setNewTag('feature');
      setNewPriority('P1');
      setNewAuthorId(undefined);
      setShowNewTask(false);
      loadProject();
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  const handleToggleStatus = async (task: Task) => {
    try {
      await updateTask(task.id, {
        status: task.status === 'pending' ? 'completed' : 'pending'
      });
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

  const filteredTasks = (project?.tasks?.filter((task) => {
    if (filter === 'all') return true;
    return task.status === filter;
  }) || []).sort((a, b) => {
    // Sort by updated_at descending (most recent first)
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
          {project.author && (
            <p className="text-sm text-gray-500 mt-2">
              Created by {project.author.name}
            </p>
          )}
        </div>
        <button
          onClick={handleDeleteProject}
          className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
          title="Delete project"
        >
          <Trash2 className="w-5 h-5" />
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-500">Total Tasks</p>
            <p className="text-xl font-bold">{stats.total_tasks}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-500">Pending</p>
            <p className="text-xl font-bold text-yellow-600">{stats.pending_tasks}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-500">Completed</p>
            <p className="text-xl font-bold text-green-600">{stats.completed_tasks}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-500">P0 Tasks</p>
            <p className="text-xl font-bold text-red-600">{stats.p0_tasks}</p>
          </div>
        </div>
      )}

      {/* Tasks Section */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold">Tasks</h2>
            <div className="flex gap-1">
              {['all', 'pending', 'completed'].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f as any)}
                  className={`px-3 py-1 text-sm rounded-lg ${
                    filter === f
                      ? 'bg-indigo-100 text-indigo-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={() => setShowNewTask(!showNewTask)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            <Plus className="w-4 h-4" />
            Add Task
          </button>
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
                <select
                  value={newAuthorId || ''}
                  onChange={(e) => setNewAuthorId(e.target.value ? Number(e.target.value) : undefined)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Author</option>
                  {authors.map((a) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
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
              No tasks {filter !== 'all' ? `with status "${filter}"` : ''} yet
            </p>
          ) : (
            filteredTasks.map((task) => (
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
                    <span className="font-mono text-sm text-gray-500">#{task.id}</span>
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
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">{task.description}</p>
                  )}
                  <div className="flex items-center gap-2 mt-2">
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
                <button
                  onClick={() => handleDeleteTask(task.id)}
                  className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
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
