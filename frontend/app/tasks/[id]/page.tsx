'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  AlertCircle,
  ArrowLeft,
  Bug,
  CheckCircle2,
  Circle,
  Clock,
  GitBranch,
  Info,
  Lightbulb,
  ListTree,
  MessageSquare,
  Send,
  Sparkles,
  Trash2,
  User,
  X
} from 'lucide-react';
import {
  getTask,
  getAuthors,
  updateTask,
  deleteTask,
  createComment,
  deleteComment,
  createTask,
  getTaskSubtasks,
  getTaskProgress,
  getTaskDependencies,
  addTaskDependency,
  removeTaskDependency,
  getTasks,
  Task,
  Author,
  TaskProgress
} from '@/lib/api';

export default function TaskDetail() {
  const params = useParams();
  const router = useRouter();
  const taskId = Number(params.id);

  const [task, setTask] = useState<Task | null>(null);
  const [authors, setAuthors] = useState<Author[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [commentAuthorId, setCommentAuthorId] = useState<number | undefined>();
  const [selectedOwnerId, setSelectedOwnerId] = useState<number | null>(null);

  // Subtasks state
  const [subtasks, setSubtasks] = useState<Task[]>([]);
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [loadingSubtasks, setLoadingSubtasks] = useState(false);
  const [showAddSubtask, setShowAddSubtask] = useState(false);
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');
  const [newSubtaskPriority, setNewSubtaskPriority] = useState<'P0' | 'P1'>('P1');
  const [newSubtaskTag, setNewSubtaskTag] = useState<'bug' | 'feature' | 'idea'>('feature');
  const [submittingSubtask, setSubmittingSubtask] = useState(false);

  // Dependencies state
  const [blockedByTasks, setBlockedByTasks] = useState<Task[]>([]);
  const [blockingTasks, setBlockingTasks] = useState<Task[]>([]);
  const [loadingDependencies, setLoadingDependencies] = useState(false);
  const [availableTasks, setAvailableTasks] = useState<Task[]>([]);
  const [selectedBlockingTaskId, setSelectedBlockingTaskId] = useState<string>('');
  const [submittingDependency, setSubmittingDependency] = useState(false);
  const [dependencyError, setDependencyError] = useState<string>('');

  // Edit form
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editTag, setEditTag] = useState<'bug' | 'feature' | 'idea'>('feature');
  const [editPriority, setEditPriority] = useState<'P0' | 'P1'>('P1');
  const [editStatus, setEditStatus] = useState<'pending' | 'completed'>('pending');

  useEffect(() => {
    loadTask();
    loadSubtasks();
    loadDependencies();
    getAuthors().then(setAuthors).catch(console.error);
  }, [taskId]);

  const loadTask = async () => {
    try {
      const data = await getTask(taskId);
      setTask(data);
      setEditTitle(data.title);
      setEditDescription(data.description || '');
      setEditTag(data.tag);
      setEditPriority(data.priority);
      setEditStatus(data.status);
      setSelectedOwnerId(data.owner_id);
    } catch (error) {
      console.error('Failed to load task:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSubtasks = async () => {
    setLoadingSubtasks(true);
    try {
      const [subtasksData, progressData] = await Promise.all([
        getTaskSubtasks(taskId),
        getTaskProgress(taskId).catch(() => null)
      ]);
      setSubtasks(subtasksData);
      setProgress(progressData);
    } catch (error) {
      console.error('Failed to load subtasks:', error);
    } finally {
      setLoadingSubtasks(false);
    }
  };

  const loadDependencies = async () => {
    setLoadingDependencies(true);
    try {
      const taskWithDeps = await getTaskDependencies(taskId);
      // Fix: Correct the field mapping
      // blocking_tasks = tasks that block THIS task (show in "Blocked By" section)
      // blocked_tasks = tasks that THIS task blocks (show in "Blocks" section)
      setBlockedByTasks(taskWithDeps.blocking_tasks || []);
      setBlockingTasks(taskWithDeps.blocked_tasks || []);

      // Load available tasks from the same project
      // Use taskWithDeps.project_id instead of task.project_id since task might be null
      const projectTasks = await getTasks({ project_id: taskWithDeps.project_id });
      // Filter out current task and existing dependencies
      const existingDepIds = new Set([
        taskId,
        ...(taskWithDeps.blocking_tasks || []).map(t => t.id),
        ...(taskWithDeps.blocked_tasks || []).map(t => t.id)
      ]);
      setAvailableTasks(projectTasks.filter(t => !existingDepIds.has(t.id)));
    } catch (error) {
      console.error('Failed to load dependencies:', error);
    } finally {
      setLoadingDependencies(false);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateTask(taskId, {
        title: editTitle,
        description: editDescription || undefined,
        tag: editTag,
        priority: editPriority,
        status: editStatus
      });
      setEditing(false);
      loadTask();
    } catch (error) {
      console.error('Failed to update task:', error);
    }
  };

  const handleToggleStatus = async () => {
    if (!task) return;
    try {
      await updateTask(taskId, {
        status: task.status === 'pending' ? 'completed' : 'pending'
      });
      loadTask();
    } catch (error) {
      console.error('Failed to update task:', error);
    }
  };

  const handleOwnerChange = async (newOwnerId: number | null) => {
    try {
      await updateTask(taskId, {
        owner_id: newOwnerId
      });
      setSelectedOwnerId(newOwnerId);
      loadTask();
    } catch (error) {
      console.error('Failed to update owner:', error);
    }
  };

  const handleDelete = async () => {
    if (!task || !confirm('Are you sure you want to delete this task?')) return;
    try {
      await deleteTask(taskId);
      router.push(`/projects/${task.project_id}`);
    } catch (error) {
      console.error('Failed to delete task:', error);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    try {
      await createComment(taskId, {
        content: newComment.trim(),
        author_id: commentAuthorId
      });
      setNewComment('');
      loadTask();
    } catch (error) {
      console.error('Failed to add comment:', error);
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    if (!confirm('Delete this comment?')) return;
    try {
      await deleteComment(commentId);
      loadTask();
    } catch (error) {
      console.error('Failed to delete comment:', error);
    }
  };

  const handleAddSubtask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSubtaskTitle.trim() || !task) return;

    setSubmittingSubtask(true);
    try {
      await createTask({
        project_id: task.project_id,
        title: newSubtaskTitle.trim(),
        tag: newSubtaskTag,
        priority: newSubtaskPriority,
        parent_task_id: taskId
      });
      setNewSubtaskTitle('');
      setNewSubtaskPriority('P1');
      setNewSubtaskTag('feature');
      setShowAddSubtask(false);
      loadSubtasks();
    } catch (error) {
      console.error('Failed to add subtask:', error);
      alert('Failed to add subtask. Please try again.');
    } finally {
      setSubmittingSubtask(false);
    }
  };

  const handleToggleSubtaskStatus = async (subtaskId: number, currentStatus: string) => {
    try {
      await updateTask(subtaskId, {
        status: currentStatus === 'pending' ? 'completed' : 'pending'
      });
      loadSubtasks();
    } catch (error) {
      console.error('Failed to toggle subtask status:', error);
      alert('Failed to update subtask. Please try again.');
    }
  };

  const handleAddDependency = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBlockingTaskId) return;

    setSubmittingDependency(true);
    setDependencyError('');
    try {
      await addTaskDependency(taskId, Number(selectedBlockingTaskId));
      setSelectedBlockingTaskId('');
      loadDependencies();
      loadTask(); // Reload task to update is_blocked status
    } catch (error: any) {
      console.error('Failed to add dependency:', error);
      if (error.message && error.message.includes('circular')) {
        setDependencyError('Cannot add dependency: This would create a circular dependency.');
      } else {
        setDependencyError('Failed to add dependency. Please try again.');
      }
    } finally {
      setSubmittingDependency(false);
    }
  };

  const handleRemoveDependency = async (blockingTaskId: number) => {
    if (!confirm('Remove this dependency?')) return;
    try {
      // Endpoint semantics: DELETE /api/tasks/{blocked_task}/dependencies/{blocking_task}
      // When removing from "Blocked By" list: current task is blocked, blockingTaskId is the blocker
      // Call: removeTaskDependency(currentTask, blockingTask)
      await removeTaskDependency(taskId, blockingTaskId);
      loadDependencies();
      loadTask(); // Reload task to update is_blocked status
    } catch (error) {
      console.error('Failed to remove dependency:', error);
      alert('Failed to remove dependency. Please try again.');
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="p-8">
        <p className="text-gray-500">Task not found</p>
        <Link href="/" className="text-indigo-600 hover:text-indigo-700">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl">
      <Link
        href={`/projects/${task.project_id}`}
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Project
      </Link>

      <div className="bg-white rounded-xl border border-gray-200">
        {/* Task Header */}
        <div className="p-6 border-b border-gray-200">
          {editing ? (
            <form onSubmit={handleUpdate} className="space-y-4">
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full text-xl font-bold px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={3}
                placeholder="Description"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
              <div className="flex gap-4">
                <select
                  value={editTag}
                  onChange={(e) => setEditTag(e.target.value as any)}
                  className="px-4 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="feature">Feature</option>
                  <option value="bug">Bug</option>
                  <option value="idea">Idea</option>
                </select>
                <select
                  value={editPriority}
                  onChange={(e) => setEditPriority(e.target.value as any)}
                  className="px-4 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="P1">P1</option>
                  <option value="P0">P0</option>
                </select>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value as any)}
                  className="px-4 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="pending">Pending</option>
                  <option value="completed">Completed</option>
                </select>
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  Save Changes
                </button>
                <button
                  type="button"
                  onClick={() => setEditing(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <>
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <button
                    onClick={handleToggleStatus}
                    className={`mt-1 ${
                      task.status === 'completed' ? 'text-green-600' : 'text-gray-400'
                    }`}
                  >
                    {task.status === 'completed' ? (
                      <CheckCircle2 className="w-6 h-6" />
                    ) : (
                      <Circle className="w-6 h-6" />
                    )}
                  </button>
                  <div>
                    <div className="mb-2">
                      <span className="text-sm font-mono text-gray-500">#{task.id}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <h1
                        className={`text-2xl font-bold ${
                          task.status === 'completed'
                            ? 'line-through text-gray-500'
                            : 'text-gray-900'
                        }`}
                      >
                        {task.title}
                      </h1>
                      {progress && progress.total_subtasks > 0 && (
                        <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
                          {progress.completed_subtasks}/{progress.total_subtasks}
                        </span>
                      )}
                    </div>

                    {/* Progress Bar */}
                    {progress && progress.total_subtasks > 0 && (
                      <div className="mt-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700">
                            {Math.round(progress.completion_percentage)}% Complete
                          </span>
                          <span className="text-xs text-gray-500">
                            {progress.completed_subtasks} / {progress.total_subtasks} subtasks completed
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2.5">
                          <div
                            className="bg-gradient-to-r from-blue-500 to-blue-600 h-2.5 rounded-full transition-all duration-300"
                            style={{ width: `${progress.completion_percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    )}

                    {/* Owner Dropdown */}
                    <div className="mt-3 flex items-center gap-2">
                      <span className="text-sm text-gray-600">Owner:</span>
                      <select
                        value={selectedOwnerId || ''}
                        onChange={(e) => handleOwnerChange(e.target.value ? Number(e.target.value) : null)}
                        className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white hover:border-indigo-400 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      >
                        <option value="">Unassigned</option>
                        {authors.map((author) => (
                          <option key={author.id} value={author.id}>
                            {author.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="flex items-center gap-3 mt-3">
                      <span
                        className={`inline-flex items-center gap-1 px-3 py-1 text-sm rounded-full ${
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
                        className={`px-3 py-1 text-sm rounded-full font-medium ${
                          task.priority === 'P0'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {task.priority}
                      </span>
                      <span
                        className={`px-3 py-1 text-sm rounded-full ${
                          task.status === 'completed'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {task.status}
                      </span>
                      {task.is_blocked && (
                        <span className="inline-flex items-center gap-1 px-3 py-1 text-sm rounded-full bg-red-100 text-red-700 border border-red-300">
                          <AlertCircle className="w-4 h-4" />
                          Blocked
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setEditing(true)}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Edit
                  </button>
                  <button
                    onClick={handleDelete}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
              {task.description && (
                <p className="mt-4 text-gray-700 whitespace-pre-wrap">{task.description}</p>
              )}
              <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
                {task.author && (
                  <span className="flex items-center gap-1">
                    <User className="w-4 h-4" />
                    Created by {task.author.name}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {formatDate(task.created_at)}
                </span>
              </div>
            </>
          )}
        </div>

        {/* Dependencies Section */}
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <GitBranch className="w-5 h-5" />
            Dependencies
          </h2>

          {loadingDependencies ? (
            <div className="flex items-center justify-center py-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Blocked By Section (Red) */}
              <div className="border-2 border-red-200 rounded-lg p-4 bg-red-50">
                <div className="flex items-center gap-2 mb-3">
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  <h3 className="font-semibold text-red-900">Blocked By</h3>
                  {blockedByTasks.length > 0 && (
                    <span className="px-2 py-0.5 text-xs font-medium bg-red-200 text-red-800 rounded-full">
                      {blockedByTasks.length}
                    </span>
                  )}
                </div>

                {blockedByTasks.length === 0 ? (
                  <p className="text-sm text-red-700">This task is not blocked by any other tasks.</p>
                ) : (
                  <>
                    <p className="text-sm text-red-700 mb-3 font-medium">
                      This task is blocked and cannot be completed until the following tasks are done:
                    </p>
                    <div className="space-y-2">
                      {blockedByTasks.map((blockingTask) => (
                        <div
                          key={blockingTask.id}
                          className="flex items-center justify-between bg-white rounded-lg p-3 border border-red-200"
                        >
                          <div className="flex items-center gap-3 flex-1">
                            <span className="font-mono text-sm text-gray-500">#{blockingTask.id}</span>
                            <Link
                              href={`/tasks/${blockingTask.id}`}
                              className="font-medium text-gray-900 hover:text-indigo-600"
                            >
                              {blockingTask.title}
                            </Link>
                            <div className="flex items-center gap-2">
                              <span
                                className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                                  blockingTask.priority === 'P0'
                                    ? 'bg-red-100 text-red-700'
                                    : 'bg-gray-100 text-gray-700'
                                }`}
                              >
                                {blockingTask.priority}
                              </span>
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full ${
                                  blockingTask.tag === 'bug'
                                    ? 'bg-red-100 text-red-700'
                                    : blockingTask.tag === 'feature'
                                    ? 'bg-blue-100 text-blue-700'
                                    : 'bg-purple-100 text-purple-700'
                                }`}
                              >
                                {getTagIcon(blockingTask.tag)}
                                {blockingTask.tag}
                              </span>
                            </div>
                          </div>
                          <button
                            onClick={() => handleRemoveDependency(blockingTask.id)}
                            className="p-1.5 text-red-600 hover:bg-red-100 rounded-lg transition-colors"
                            title="Remove dependency"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>

              {/* Blocks Section (Blue) */}
              <div className="border-2 border-blue-200 rounded-lg p-4 bg-blue-50">
                <div className="flex items-center gap-2 mb-3">
                  <Info className="w-5 h-5 text-blue-600" />
                  <h3 className="font-semibold text-blue-900">Blocks</h3>
                  {blockingTasks.length > 0 && (
                    <span className="px-2 py-0.5 text-xs font-medium bg-blue-200 text-blue-800 rounded-full">
                      {blockingTasks.length}
                    </span>
                  )}
                </div>

                {blockingTasks.length === 0 ? (
                  <p className="text-sm text-blue-700">This task does not block any other tasks.</p>
                ) : (
                  <div className="space-y-2">
                    {blockingTasks.map((blockedTask) => (
                      <div
                        key={blockedTask.id}
                        className="flex items-center gap-3 bg-white rounded-lg p-3 border border-blue-200"
                      >
                        <span className="font-mono text-sm text-gray-500">#{blockedTask.id}</span>
                        <Link
                          href={`/tasks/${blockedTask.id}`}
                          className="font-medium text-gray-900 hover:text-indigo-600"
                        >
                          {blockedTask.title}
                        </Link>
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                              blockedTask.priority === 'P0'
                                ? 'bg-red-100 text-red-700'
                                : 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            {blockedTask.priority}
                          </span>
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full ${
                              blockedTask.tag === 'bug'
                                ? 'bg-red-100 text-red-700'
                                : blockedTask.tag === 'feature'
                                ? 'bg-blue-100 text-blue-700'
                                : 'bg-purple-100 text-purple-700'
                            }`}
                          >
                            {getTagIcon(blockedTask.tag)}
                            {blockedTask.tag}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Add Blocking Task Dropdown */}
              <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                <h3 className="font-semibold text-gray-900 mb-3">Add Blocking Task</h3>
                <form onSubmit={handleAddDependency} className="space-y-3">
                  <div>
                    <select
                      value={selectedBlockingTaskId}
                      onChange={(e) => {
                        setSelectedBlockingTaskId(e.target.value);
                        setDependencyError('');
                      }}
                      disabled={submittingDependency || availableTasks.length === 0}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <option value="">
                        {availableTasks.length === 0
                          ? 'No available tasks in this project'
                          : 'Select a task that blocks this one...'}
                      </option>
                      {availableTasks.map((t) => (
                        <option key={t.id} value={t.id}>
                          #{t.id} - {t.title} ({t.priority}, {t.tag})
                        </option>
                      ))}
                    </select>
                  </div>

                  {dependencyError && (
                    <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                      <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                      <p className="text-sm text-red-700">{dependencyError}</p>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={!selectedBlockingTaskId || submittingDependency}
                    className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {submittingDependency ? 'Adding...' : 'Add Dependency'}
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>

        {/* Subtasks Section */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <ListTree className="w-5 h-5 text-indigo-600" />
              Subtasks ({subtasks.length})
            </h2>
            <button
              onClick={() => setShowAddSubtask(!showAddSubtask)}
              className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              {showAddSubtask ? 'Cancel' : '+ Add Subtask'}
            </button>
          </div>

          {/* Add Subtask Form */}
          {showAddSubtask && (
            <form onSubmit={handleAddSubtask} className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="space-y-3">
                <input
                  type="text"
                  value={newSubtaskTitle}
                  onChange={(e) => setNewSubtaskTitle(e.target.value)}
                  placeholder="Subtask title..."
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  autoFocus
                />
                <div className="flex gap-3">
                  <select
                    value={newSubtaskPriority}
                    onChange={(e) => setNewSubtaskPriority(e.target.value as 'P0' | 'P1')}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  >
                    <option value="P1">P1</option>
                    <option value="P0">P0</option>
                  </select>
                  <select
                    value={newSubtaskTag}
                    onChange={(e) => setNewSubtaskTag(e.target.value as 'bug' | 'feature' | 'idea')}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  >
                    <option value="feature">Feature</option>
                    <option value="bug">Bug</option>
                    <option value="idea">Idea</option>
                  </select>
                  <button
                    type="submit"
                    disabled={!newSubtaskTitle.trim() || submittingSubtask}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                  >
                    {submittingSubtask ? 'Adding...' : 'Add'}
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* Subtasks List */}
          {loadingSubtasks ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
            </div>
          ) : subtasks.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No subtasks yet</p>
          ) : (
            <div className="space-y-2">
              {subtasks.map((subtask) => (
                <div
                  key={subtask.id}
                  className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
                >
                  <button
                    onClick={() => handleToggleSubtaskStatus(subtask.id, subtask.status)}
                    className={`flex-shrink-0 ${
                      subtask.status === 'completed' ? 'text-green-600' : 'text-gray-400'
                    }`}
                  >
                    {subtask.status === 'completed' ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : (
                      <Circle className="w-5 h-5" />
                    )}
                  </button>
                  <Link
                    href={`/tasks/${subtask.id}`}
                    className={`flex-1 hover:text-indigo-600 ${
                      subtask.status === 'completed'
                        ? 'line-through text-gray-500'
                        : 'text-gray-900'
                    }`}
                  >
                    <span className="text-sm font-mono text-gray-400 mr-2">#{subtask.id}</span>
                    {subtask.title}
                  </Link>
                  <span
                    className={`px-2 py-1 text-xs rounded-full font-medium ${
                      subtask.priority === 'P0'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    {subtask.priority}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full ${
                      subtask.tag === 'bug'
                        ? 'bg-red-100 text-red-700'
                        : subtask.tag === 'feature'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-purple-100 text-purple-700'
                    }`}
                  >
                    {getTagIcon(subtask.tag)}
                    {subtask.tag}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Comments Section */}
        <div className="p-6">
          <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <MessageSquare className="w-5 h-5" />
            Comments ({task.comments?.length || 0})
          </h2>

          {/* Add Comment Form */}
          <form onSubmit={handleAddComment} className="mb-6">
            <div className="flex gap-2 mb-2">
              <select
                value={commentAuthorId || ''}
                onChange={(e) =>
                  setCommentAuthorId(e.target.value ? Number(e.target.value) : undefined)
                }
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
              >
                <option value="">Comment as...</option>
                {authors.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex gap-2">
              <textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Write a comment..."
                rows={2}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
              <button
                type="submit"
                disabled={!newComment.trim()}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed self-end"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </form>

          {/* Comments List */}
          <div className="space-y-4">
            {(!task.comments || task.comments.length === 0) ? (
              <p className="text-gray-500 text-center py-4">No comments yet</p>
            ) : (
              task.comments.map((comment) => (
                <div
                  key={comment.id}
                  className="bg-gray-50 rounded-lg p-4 relative group"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
                        <User className="w-4 h-4 text-indigo-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">
                          {comment.author?.name || 'Anonymous'}
                        </p>
                        <p className="text-xs text-gray-500">{formatDate(comment.created_at)}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteComment(comment.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-600 transition-opacity"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <p className="text-gray-700 whitespace-pre-wrap ml-10">{comment.content}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
