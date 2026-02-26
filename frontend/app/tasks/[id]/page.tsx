'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import {
  AlertCircle,
  ArrowLeft,
  Bug,
  Clock,
  Download,
  ExternalLink as ExternalLinkIcon,
  FileText,
  GitBranch,
  Info,
  Lightbulb,
  Link as LinkIcon,
  ListTree,
  MessageSquare,
  Send,
  Sparkles,
  Tag,
  Trash2,
  Upload,
  User,
  X,
  History
} from 'lucide-react';
import {
  getTask,
  getProjectMembers,
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
  isOverdue,
  uploadAttachment,
  deleteAttachment,
  addExternalLink,
  removeExternalLink,
  updateMetadata,
  deleteMetadata,
  API_BASE,
  Task,
  Author,
  TaskProgress
} from '@/lib/api';
import { STATUS_CONFIG, TaskStatus } from '@/components/StatusConfig';
import Timeline from '@/components/Timeline';
import MarkdownRenderer from '@/components/MarkdownRenderer';
import { utcToLocalInput, localInputToUTC, formatDate } from '@/lib/date-utils';

// Sanitize external link URLs to prevent XSS (defense in depth)
function sanitizeExternalUrl(url: string): string {
  if (!url) return '';

  // Allow only safe protocols
  const allowedProtocols = ['http:', 'https:', 'mailto:'];
  try {
    const parsedUrl = new URL(url, window.location.href);
    if (allowedProtocols.includes(parsedUrl.protocol)) {
      return url;
    }
  } catch {
    // Invalid URL - return empty to be safe
    return '';
  }

  // Unsafe protocol detected - return empty string
  return '';
}

export default function TaskDetail() {
  const params = useParams();
  const router = useRouter();
  const taskId = Number(params.id);

  const [task, setTask] = useState<Task | null>(null);
  const [authors, setAuthors] = useState<Author[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [newComment, setNewComment] = useState('');
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

  // Rich Context state
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string>('');
  const [showAddLink, setShowAddLink] = useState(false);
  const [newLinkUrl, setNewLinkUrl] = useState('');
  const [newLinkLabel, setNewLinkLabel] = useState('');
  const [submittingLink, setSubmittingLink] = useState(false);
  const [showAddMetadata, setShowAddMetadata] = useState(false);
  const [newMetadataKey, setNewMetadataKey] = useState('');
  const [newMetadataValue, setNewMetadataValue] = useState('');
  const [submittingMetadata, setSubmittingMetadata] = useState(false);

  // Edit form
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editTag, setEditTag] = useState<'bug' | 'feature' | 'idea'>('feature');
  const [editPriority, setEditPriority] = useState<'P0' | 'P1'>('P1');
  const [editStatus, setEditStatus] = useState<TaskStatus>('todo');
  const [editDueDate, setEditDueDate] = useState('');
  const [editEstimatedHours, setEditEstimatedHours] = useState('');
  const [editActualHours, setEditActualHours] = useState('');

  useEffect(() => {
    loadTask();
    loadSubtasks();
    loadDependencies();
  }, [taskId]);

  // Load project members after task is loaded (requires viewer access, not admin)
  useEffect(() => {
    if (task?.project_id) {
      getProjectMembers(task.project_id)
        .then(members => setAuthors(members.map(m => m.user)))
        .catch(() => setAuthors([])); // Graceful degradation on error
    }
  }, [task?.project_id]);

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
      // Format due_date for datetime-local input (if it exists)
      setEditDueDate(data.due_date ? utcToLocalInput(data.due_date) : '');
      setEditEstimatedHours(data.estimated_hours?.toString() || '');
      setEditActualHours(data.actual_hours?.toString() || '');
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
        status: editStatus,
        due_date: editDueDate ? localInputToUTC(editDueDate) : null,
        estimated_hours: editEstimatedHours !== '' ? parseFloat(editEstimatedHours) : null,
        actual_hours: editActualHours !== '' ? parseFloat(editActualHours) : null
      });
      setEditing(false);
      loadTask();
    } catch (error) {
      console.error('Failed to update task:', error);
    }
  };

  const handleStatusChange = async (newStatus: TaskStatus) => {
    if (!task) return;
    try {
      await updateTask(taskId, { status: newStatus });
      loadTask();
      loadSubtasks();
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
        content: newComment.trim()
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

  const handleToggleSubtaskStatus = async (subtaskId: number, currentStatus: TaskStatus) => {
    try {
      const nextStatus = currentStatus === 'done' ? 'todo' : 'done';
      await updateTask(subtaskId, { status: nextStatus });
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

  // Rich Context handlers
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError('');

    try {
      await uploadAttachment(taskId, file);
      await loadTask(); // Reload task to show new attachment
      e.target.value = ''; // Reset file input
    } catch (error: any) {
      console.error('Failed to upload file:', error);
      setUploadError(error.message || 'Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteAttachment = async (attachmentId: number) => {
    if (!confirm('Are you sure you want to delete this attachment?')) return;

    try {
      await deleteAttachment(taskId, attachmentId);
      await loadTask();
    } catch (error) {
      console.error('Failed to delete attachment:', error);
      alert('Failed to delete attachment');
    }
  };

  const handleAddLink = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLinkUrl.trim()) return;

    setSubmittingLink(true);
    try {
      await addExternalLink(taskId, { url: newLinkUrl, label: newLinkLabel || undefined });
      await loadTask();
      setNewLinkUrl('');
      setNewLinkLabel('');
      setShowAddLink(false);
    } catch (error) {
      console.error('Failed to add link:', error);
      alert('Failed to add link');
    } finally {
      setSubmittingLink(false);
    }
  };

  const handleRemoveLink = async (url: string) => {
    if (!confirm('Are you sure you want to remove this link?')) return;

    try {
      await removeExternalLink(taskId, url);
      await loadTask();
    } catch (error) {
      console.error('Failed to remove link:', error);
      alert('Failed to remove link');
    }
  };

  const handleAddMetadata = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMetadataKey.trim() || !newMetadataValue.trim()) return;

    setSubmittingMetadata(true);
    try {
      await updateMetadata(taskId, { key: newMetadataKey, value: newMetadataValue });
      await loadTask();
      setNewMetadataKey('');
      setNewMetadataValue('');
      setShowAddMetadata(false);
    } catch (error) {
      console.error('Failed to add metadata:', error);
      alert('Failed to add metadata');
    } finally {
      setSubmittingMetadata(false);
    }
  };

  const handleDeleteMetadata = async (key: string) => {
    if (!confirm(`Are you sure you want to delete the "${key}" metadata?`)) return;

    try {
      await deleteMetadata(taskId, key);
      await loadTask();
    } catch (error) {
      console.error('Failed to delete metadata:', error);
      alert('Failed to delete metadata');
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
                  onChange={(e) => setEditStatus(e.target.value as TaskStatus)}
                  className="px-4 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="backlog">Backlog</option>
                  <option value="todo">To Do</option>
                  <option value="in_progress">In Progress</option>
                  <option value="blocked">Blocked</option>
                  <option value="review">Review</option>
                  <option value="done">Done</option>
                  <option value="not_needed">Not Needed</option>
                </select>
              </div>
              {/* Time Tracking Fields */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Due Date
                  </label>
                  <input
                    type="datetime-local"
                    value={editDueDate}
                    onChange={(e) => setEditDueDate(e.target.value)}
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
                    value={editEstimatedHours}
                    onChange={(e) => setEditEstimatedHours(e.target.value)}
                    placeholder="5.5"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Actual Hours
                  </label>
                  <input
                    type="number"
                    step="0.25"
                    min="0"
                    value={editActualHours}
                    onChange={(e) => setEditActualHours(e.target.value)}
                    placeholder="4.75"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
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
                  <div>
                    <div className="mb-2">
                      <span className="text-sm font-mono text-gray-500">#{task.id}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <h1
                        className={`text-2xl font-bold ${
                          task.status === 'done'
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

                    {/* Status and Owner Controls */}
                    <div className="mt-3 flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-600">Status:</span>
                        <select
                          value={task.status}
                          onChange={(e) => handleStatusChange(e.target.value as TaskStatus)}
                          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white hover:border-indigo-400 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        >
                          <option value="backlog">Backlog</option>
                          <option value="todo">To Do</option>
                          <option value="in_progress">In Progress</option>
                          <option value="blocked">Blocked</option>
                          <option value="review">Review</option>
                          <option value="done">Done</option>
                          <option value="not_needed">Not Needed</option>
                        </select>
                      </div>
                      <div className="flex items-center gap-2">
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
                      {(() => {
                        const StatusIcon = STATUS_CONFIG[task.status].icon;
                        return (
                          <span className={`inline-flex items-center gap-1.5 px-3 py-1 text-sm rounded-full border ${STATUS_CONFIG[task.status].color}`}>
                            <StatusIcon className="w-4 h-4" />
                            {STATUS_CONFIG[task.status].label}
                          </span>
                        );
                      })()}
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
                <div className="mt-4">
                  <MarkdownRenderer content={task.description} />
                </div>
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

              {/* Time Tracking Display Section */}
              {(task.due_date || task.estimated_hours !== null || task.actual_hours !== null) && (
                <div className="mt-6 border-t border-gray-200 pt-6">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Clock className="w-5 h-5 text-indigo-600" />
                    Time Tracking
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Due Date Section */}
                    {task.due_date && (
                      <div>
                        <p className="text-sm font-medium text-gray-700 mb-2">Due Date</p>
                        <div className="flex items-center gap-2">
                          <p className="text-gray-900">
                            {new Date(task.due_date).toLocaleString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                              hour: 'numeric',
                              minute: '2-digit'
                            })}
                          </p>
                          <span className="text-sm text-gray-500">
                            ({formatDistanceToNow(new Date(task.due_date), { addSuffix: true })})
                          </span>
                        </div>
                        {isOverdue(task) && (
                          <div className="mt-2 inline-flex items-center gap-1 px-3 py-1 bg-red-100 text-red-700 rounded-full border border-red-300">
                            <AlertCircle className="w-4 h-4" />
                            <span className="text-sm font-medium">OVERDUE</span>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Hours Tracking Section */}
                    {(task.estimated_hours !== null || task.actual_hours !== null) && (
                      <div>
                        <p className="text-sm font-medium text-gray-700 mb-2">Hours Tracking</p>
                        <div className="space-y-2">
                          {task.estimated_hours !== null && (
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">Estimated:</span>
                              <span className="font-medium text-gray-900">
                                {task.estimated_hours}h
                              </span>
                            </div>
                          )}
                          {task.actual_hours !== null && (
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">Actual:</span>
                              <span className="font-medium text-gray-900">
                                {task.actual_hours}h
                              </span>
                            </div>
                          )}
                          {task.estimated_hours !== null && task.actual_hours !== null && (
                            <div className="mt-3">
                              <div className="flex justify-between text-xs text-gray-600 mb-1">
                                <span>Progress</span>
                                <span>
                                  {task.estimated_hours > 0
                                    ? `${Math.round((task.actual_hours / task.estimated_hours) * 100)}%`
                                    : 'N/A'}
                                </span>
                              </div>
                              {task.estimated_hours > 0 ? (
                                <>
                                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                                    <div
                                      className={`h-2.5 rounded-full transition-all duration-300 ${
                                        task.actual_hours <= task.estimated_hours
                                          ? 'bg-green-500'
                                          : 'bg-red-500'
                                      }`}
                                      style={{
                                        width: `${Math.min((task.actual_hours / task.estimated_hours) * 100, 100)}%`
                                      }}
                                    ></div>
                                  </div>
                                  {task.actual_hours > task.estimated_hours && (
                                    <p className="mt-1 text-xs text-red-600">
                                      Over budget by {(task.actual_hours - task.estimated_hours).toFixed(2)}h
                                    </p>
                                  )}
                                  {task.actual_hours <= task.estimated_hours && (
                                    <p className="mt-1 text-xs text-green-600">
                                      Under budget by {(task.estimated_hours - task.actual_hours).toFixed(2)}h
                                    </p>
                                  )}
                                </>
                              ) : (
                                <p className="mt-1 text-xs text-gray-600">
                                  Cannot calculate progress (estimated hours is 0)
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Rich Context & Attachments Section */}
        {!editing && (
          <div className="p-6 border-t border-gray-200">
            <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
              <FileText className="w-5 h-5" />
              Attachments & Links
            </h2>

            <div className="space-y-6">
              {/* File Attachments */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-gray-900">File Attachments</h3>
                  <label className="px-3 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 cursor-pointer text-sm flex items-center gap-2">
                    <Upload className="w-4 h-4" />
                    {uploading ? 'Uploading...' : 'Upload File'}
                    <input
                      type="file"
                      className="hidden"
                      onChange={handleFileUpload}
                      disabled={uploading}
                      accept=".pdf,.txt,.md,.doc,.docx,.png,.jpg,.jpeg,.gif,.webp,.json,.xml,.csv,.xlsx,.zip,.tar,.gz"
                    />
                  </label>
                </div>

                {uploadError && (
                  <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600">
                    {uploadError}
                  </div>
                )}

                {task.attachments && task.attachments.length > 0 ? (
                  <div className="space-y-2">
                    {task.attachments.map((attachment) => (
                      <div
                        key={attachment.id}
                        className="flex items-center justify-between bg-gray-50 rounded-lg p-3 border border-gray-200"
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <FileText className="w-5 h-5 text-gray-400 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <a
                              href={`${API_BASE}${attachment.filepath}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-indigo-600 hover:text-indigo-800 hover:underline font-medium truncate block"
                            >
                              {attachment.original_filename}
                            </a>
                            <p className="text-xs text-gray-500">
                              {(attachment.file_size / 1024).toFixed(2)} KB
                              {attachment.uploader && ` • Uploaded by ${attachment.uploader.name}`}
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteAttachment(attachment.id)}
                          className="ml-2 p-1 text-red-600 hover:text-red-800 flex-shrink-0"
                          title="Delete attachment"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 italic">No attachments yet</p>
                )}
              </div>

              {/* External Links */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-gray-900">External Links</h3>
                  <button
                    onClick={() => setShowAddLink(!showAddLink)}
                    className="px-3 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm flex items-center gap-2"
                  >
                    <LinkIcon className="w-4 h-4" />
                    Add Link
                  </button>
                </div>

                {showAddLink && (
                  <form onSubmit={handleAddLink} className="mb-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="space-y-2">
                      <input
                        type="url"
                        value={newLinkUrl}
                        onChange={(e) => setNewLinkUrl(e.target.value)}
                        placeholder="https://example.com"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        required
                      />
                      <input
                        type="text"
                        value={newLinkLabel}
                        onChange={(e) => setNewLinkLabel(e.target.value)}
                        placeholder="Label (optional)"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      />
                      <div className="flex gap-2">
                        <button
                          type="submit"
                          disabled={submittingLink}
                          className="px-3 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm disabled:opacity-50"
                        >
                          {submittingLink ? 'Adding...' : 'Add'}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setShowAddLink(false);
                            setNewLinkUrl('');
                            setNewLinkLabel('');
                          }}
                          className="px-3 py-1 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 text-sm"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  </form>
                )}

                {task.external_links && task.external_links.length > 0 ? (
                  <div className="space-y-2">
                    {task.external_links.map((link, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between bg-gray-50 rounded-lg p-3 border border-gray-200"
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <ExternalLinkIcon className="w-5 h-5 text-gray-400 flex-shrink-0" />
                          <a
                            href={sanitizeExternalUrl(link.url)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-indigo-600 hover:text-indigo-800 hover:underline truncate block"
                          >
                            {link.label || link.url}
                          </a>
                        </div>
                        <button
                          onClick={() => handleRemoveLink(link.url)}
                          className="ml-2 p-1 text-red-600 hover:text-red-800 flex-shrink-0"
                          title="Remove link"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 italic">No external links yet</p>
                )}
              </div>

              {/* Custom Metadata */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-gray-900">Custom Metadata</h3>
                  <button
                    onClick={() => setShowAddMetadata(!showAddMetadata)}
                    className="px-3 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm flex items-center gap-2"
                  >
                    <Tag className="w-4 h-4" />
                    Add Metadata
                  </button>
                </div>

                {showAddMetadata && (
                  <form onSubmit={handleAddMetadata} className="mb-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={newMetadataKey}
                        onChange={(e) => setNewMetadataKey(e.target.value)}
                        placeholder="Key (e.g., sprint, team, version)"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        required
                      />
                      <input
                        type="text"
                        value={newMetadataValue}
                        onChange={(e) => setNewMetadataValue(e.target.value)}
                        placeholder="Value"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        required
                      />
                      <div className="flex gap-2">
                        <button
                          type="submit"
                          disabled={submittingMetadata}
                          className="px-3 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm disabled:opacity-50"
                        >
                          {submittingMetadata ? 'Adding...' : 'Add'}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setShowAddMetadata(false);
                            setNewMetadataKey('');
                            setNewMetadataValue('');
                          }}
                          className="px-3 py-1 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 text-sm"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  </form>
                )}

                {task.custom_metadata && Object.keys(task.custom_metadata).length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {Object.entries(task.custom_metadata).map(([key, value]) => (
                      <div
                        key={key}
                        className="flex items-center justify-between bg-gray-50 rounded-lg p-3 border border-gray-200"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">{key}</p>
                          <p className="text-sm text-gray-600 truncate">{value}</p>
                        </div>
                        <button
                          onClick={() => handleDeleteMetadata(key)}
                          className="ml-2 p-1 text-red-600 hover:text-red-800 flex-shrink-0"
                          title="Delete metadata"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 italic">No custom metadata yet</p>
                )}
              </div>
            </div>
          </div>
        )}

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
              {subtasks.map((subtask) => {
                const SubtaskStatusIcon = STATUS_CONFIG[subtask.status].icon;
                return (
                  <div
                    key={subtask.id}
                    className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
                  >
                    <button
                      onClick={() => handleToggleSubtaskStatus(subtask.id, subtask.status)}
                      className="flex-shrink-0"
                    >
                      <SubtaskStatusIcon className={`w-5 h-5 ${subtask.status === 'done' ? 'text-green-600' : 'text-gray-400'}`} />
                    </button>
                    <Link
                      href={`/tasks/${subtask.id}`}
                      className={`flex-1 hover:text-indigo-600 ${
                        subtask.status === 'done'
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
              );
              })}
            </div>
          )}
        </div>

        {/* Comments Section */}
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <MessageSquare className="w-5 h-5" />
            Comments ({task.comments?.length || 0})
          </h2>

          {/* Add Comment Form */}
          <form onSubmit={handleAddComment} className="mb-6">
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

        {/* Timeline Section */}
        <div className="p-6">
          <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <History className="w-5 h-5" />
            Activity Timeline
          </h2>
          <Timeline taskId={taskId} limit={50} showFilters={true} />
        </div>
      </div>
    </div>
  );
}
