'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Bug,
  CheckCircle2,
  Circle,
  Clock,
  Lightbulb,
  MessageSquare,
  Send,
  Sparkles,
  Trash2,
  User
} from 'lucide-react';
import {
  getTask,
  getAuthors,
  updateTask,
  deleteTask,
  createComment,
  deleteComment,
  Task,
  Author
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

  // Edit form
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editTag, setEditTag] = useState<'bug' | 'feature' | 'idea'>('feature');
  const [editPriority, setEditPriority] = useState<'P0' | 'P1'>('P1');
  const [editStatus, setEditStatus] = useState<'pending' | 'completed'>('pending');

  useEffect(() => {
    loadTask();
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
                    <h1
                      className={`text-2xl font-bold ${
                        task.status === 'completed'
                          ? 'line-through text-gray-500'
                          : 'text-gray-900'
                      }`}
                    >
                      {task.title}
                    </h1>

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
