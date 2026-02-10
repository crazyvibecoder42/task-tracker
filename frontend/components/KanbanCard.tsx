'use client';

import { Task } from '@/lib/api';
import { isOverdue } from '@/lib/date-utils';
import { AlertCircle, MessageSquare, XCircle, Clock, User } from 'lucide-react';
import Link from 'next/link';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface KanbanCardProps {
  task: Task;
  isDragging?: boolean;
}

export default function KanbanCard({ task, isDragging }: KanbanCardProps) {
  // Skip useSortable hook when rendering in DragOverlay to avoid duplicate registration
  const sortable = useSortable({
    id: task.id.toString(),
    disabled: isDragging // Don't register sortable when used in overlay
  });

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isSortableDragging
  } = sortable;

  const style = isDragging ? {} : {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isSortableDragging ? 0.5 : 1,
  };

  const overdue = isOverdue(task);
  const hasProgress = task.estimated_hours != null &&
                      task.estimated_hours > 0 &&
                      task.actual_hours != null;
  const progressPercent = hasProgress ? (task.actual_hours! / task.estimated_hours!) * 100 : 0;

  return (
    <div
      ref={isDragging ? undefined : setNodeRef}
      style={style}
      {...(isDragging ? {} : attributes)}
      {...(isDragging ? {} : listeners)}
      className="bg-white rounded-lg p-3 shadow-sm border border-gray-200 hover:shadow-md transition-shadow cursor-grab active:cursor-grabbing mb-2"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <Link href={`/tasks/${task.id}`} className="text-sm font-medium text-gray-900 hover:text-indigo-600 flex-1">
          {task.title}
        </Link>
        <span className="text-xs text-gray-500 ml-2">#{task.id}</span>
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-1 mb-2">
        {task.priority === 'P0' && (
          <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700 font-medium">P0</span>
        )}

        <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
          task.tag === 'bug' ? 'bg-red-100 text-red-700' :
          task.tag === 'feature' ? 'bg-blue-100 text-blue-700' :
          'bg-purple-100 text-purple-700'
        }`}>
          {task.tag}
        </span>

        {task.is_blocked && (
          <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700 flex items-center gap-1">
            <XCircle className="w-3 h-3" />
            Blocked
          </span>
        )}

        {overdue && (
          <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            Overdue
          </span>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        {task.owner && (
          <div className="flex items-center gap-1">
            <User className="w-3 h-3" />
            <span>{task.owner.name}</span>
          </div>
        )}

        <div className="flex items-center gap-2">
          {task.due_date && (
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>{new Date(task.due_date).toLocaleDateString()}</span>
            </div>
          )}

          {task.comment_count && task.comment_count > 0 && (
            <div className="flex items-center gap-1">
              <MessageSquare className="w-3 h-3" />
              <span>{task.comment_count}</span>
            </div>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {hasProgress && (
        <div className="mt-2">
          <div className="w-full bg-gray-200 rounded-full h-1.5">
            <div
              className={`h-1.5 rounded-full ${progressPercent > 100 ? 'bg-red-500' : 'bg-green-500'}`}
              style={{ width: `${Math.min(progressPercent, 100)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
