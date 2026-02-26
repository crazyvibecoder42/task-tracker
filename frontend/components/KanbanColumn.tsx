'use client';

import { Task, KanbanSettings } from '@/lib/api';
import { getWipStatus } from '@/lib/kanban-utils';
import KanbanCard from './KanbanCard';
import { Settings, Circle, Clock, CheckCircle, XCircle, AlertCircle, Archive, MinusCircle } from 'lucide-react';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';

interface KanbanColumnProps {
  columnId: string;
  title: string;
  tasks: Task[];
  kanbanSettings: KanbanSettings;
  onConfigureWip: (columnId: string) => void;
}

// Status icons mapping
const STATUS_ICONS: Record<string, any> = {
  backlog: Archive,
  todo: Circle,
  in_progress: Clock,
  blocked: XCircle,
  review: AlertCircle,
  done: CheckCircle,
  not_needed: MinusCircle
};

export default function KanbanColumn({
  columnId,
  title,
  tasks,
  kanbanSettings,
  onConfigureWip
}: KanbanColumnProps) {
  const { setNodeRef } = useDroppable({ id: columnId });

  const wipLimit = kanbanSettings.wip_limits[columnId as keyof typeof kanbanSettings.wip_limits];
  const wipStatus = getWipStatus(tasks.length, wipLimit ?? null);

  const Icon = STATUS_ICONS[columnId] || Circle;

  const wipColors = {
    ok: 'text-green-600',
    warning: 'text-yellow-600',
    exceeded: 'text-red-600',
    none: 'text-gray-400'
  };

  return (
    <div className="flex-shrink-0 w-80 bg-gray-50 rounded-lg p-3">
      {/* Column Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-gray-600" />
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <span className={`text-sm font-medium ${wipColors[wipStatus]}`}>
            {tasks.length}
            {wipLimit != null && ` / ${wipLimit}`}
          </span>
        </div>

        <button
          onClick={() => onConfigureWip(columnId)}
          className="p-1 hover:bg-gray-200 rounded"
          title="Configure WIP limit"
        >
          <Settings className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      {/* Task Cards */}
      <div
        ref={setNodeRef}
        className="min-h-[400px] max-h-[calc(100vh-280px)] overflow-y-auto space-y-2"
      >
        <SortableContext
          id={columnId}
          items={tasks.map(t => t.id.toString())}
          strategy={verticalListSortingStrategy}
        >
          {tasks.map(task => (
            <KanbanCard key={task.id} task={task} />
          ))}
        </SortableContext>

        {tasks.length === 0 && (
          <div className="text-center text-gray-400 text-sm py-8">
            No tasks
          </div>
        )}
      </div>
    </div>
  );
}
