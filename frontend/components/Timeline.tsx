'use client';

import { useEffect, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  PlusCircle,
  ArrowRightCircle,
  Edit,
  UserPlus,
  Link,
  Unlink,
  MessageCircle,
  ChevronDown,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { TaskEvent, getTaskEvents, getProjectEvents } from '@/lib/api';
import { STATUS_CONFIG } from './StatusConfig';

interface TimelineProps {
  taskId?: number;
  projectId?: number;
  limit?: number;
  showFilters?: boolean;
}

type EventType = 'task_created' | 'status_change' | 'field_update' | 'ownership_change' | 'dependency_added' | 'dependency_removed' | 'comment_added';

const EVENT_TYPE_CONFIG: Record<EventType, { icon: any; color: string; label: string }> = {
  task_created: {
    icon: PlusCircle,
    color: 'bg-blue-100 text-blue-700 border-blue-300',
    label: 'Task Created'
  },
  status_change: {
    icon: ArrowRightCircle,
    color: 'bg-purple-100 text-purple-700 border-purple-300',
    label: 'Status Changed'
  },
  field_update: {
    icon: Edit,
    color: 'bg-gray-100 text-gray-700 border-gray-300',
    label: 'Field Updated'
  },
  ownership_change: {
    icon: UserPlus,
    color: 'bg-green-100 text-green-700 border-green-300',
    label: 'Ownership Changed'
  },
  dependency_added: {
    icon: Link,
    color: 'bg-indigo-100 text-indigo-700 border-indigo-300',
    label: 'Dependency Added'
  },
  dependency_removed: {
    icon: Unlink,
    color: 'bg-red-100 text-red-700 border-red-300',
    label: 'Dependency Removed'
  },
  comment_added: {
    icon: MessageCircle,
    color: 'bg-teal-100 text-teal-700 border-teal-300',
    label: 'Comment Added'
  }
};

export default function Timeline({ taskId, projectId, limit = 20, showFilters = false }: TimelineProps) {
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [selectedEventType, setSelectedEventType] = useState<string>('');
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    loadEvents(true);
  }, [taskId, projectId, selectedEventType]);

  const loadEvents = async (reset = false) => {
    try {
      if (reset) {
        setLoading(true);
        setOffset(0);
      } else {
        setLoadingMore(true);
      }

      const currentOffset = reset ? 0 : offset;
      const params = {
        limit,
        offset: currentOffset,
        ...(selectedEventType && { event_type: selectedEventType })
      };

      let result;
      if (taskId) {
        result = await getTaskEvents(taskId, params);
      } else if (projectId) {
        result = await getProjectEvents(projectId, params);
      } else {
        throw new Error('Either taskId or projectId must be provided');
      }

      if (reset) {
        setEvents(result.events);
      } else {
        setEvents((prev) => [...prev, ...result.events]);
      }

      setTotalCount(result.total_count);
      setOffset(currentOffset + result.events.length);
      setError(null);
    } catch (err) {
      console.error('Failed to load events:', err);
      setError(err instanceof Error ? err.message : 'Failed to load events');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const handleLoadMore = () => {
    loadEvents(false);
  };

  const formatFieldName = (fieldName: string): string => {
    return fieldName
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const formatFieldValue = (value: string | null, fieldName: string | null): string => {
    if (!value) return 'None';

    // Format status values
    if (fieldName === 'status' && value in STATUS_CONFIG) {
      return STATUS_CONFIG[value as keyof typeof STATUS_CONFIG].label;
    }

    return value;
  };

  const renderEventContent = (event: TaskEvent) => {
    const EventIcon = EVENT_TYPE_CONFIG[event.event_type as EventType]?.icon || AlertCircle;
    const eventConfig = EVENT_TYPE_CONFIG[event.event_type as EventType];
    const actorName = event.actor ? event.actor.name : 'System';

    let description = '';
    let detail = null;

    switch (event.event_type) {
      case 'task_created':
        description = `${actorName} created this task`;
        break;

      case 'status_change':
        description = `${actorName} changed status`;
        detail = (
          <div className="mt-1 flex items-center gap-2 text-sm">
            <span className="font-medium text-gray-600">{formatFieldValue(event.old_value, 'status')}</span>
            <ArrowRightCircle className="w-4 h-4 text-gray-400" />
            <span className="font-medium text-gray-900">{formatFieldValue(event.new_value, 'status')}</span>
          </div>
        );
        break;

      case 'field_update':
        description = `${actorName} updated ${event.field_name ? formatFieldName(event.field_name) : 'a field'}`;
        if (event.old_value || event.new_value) {
          detail = (
            <div className="mt-1 flex items-center gap-2 text-sm">
              <span className="font-medium text-gray-600">{formatFieldValue(event.old_value, event.field_name)}</span>
              <ArrowRightCircle className="w-4 h-4 text-gray-400" />
              <span className="font-medium text-gray-900">{formatFieldValue(event.new_value, event.field_name)}</span>
            </div>
          );
        }
        break;

      case 'ownership_change':
        description = `${actorName} ${event.new_value ? 'assigned to' : 'removed'} ${event.new_value || 'ownership'}`;
        break;

      case 'dependency_added':
        description = `${actorName} added a blocking dependency`;
        if (event.metadata?.blocking_task_id) {
          detail = <span className="text-sm text-gray-600 mt-1">Task #{event.metadata.blocking_task_id}</span>;
        }
        break;

      case 'dependency_removed':
        description = `${actorName} removed a blocking dependency`;
        if (event.metadata?.blocking_task_id) {
          detail = <span className="text-sm text-gray-600 mt-1">Task #{event.metadata.blocking_task_id}</span>;
        }
        break;

      case 'comment_added':
        description = `${actorName} added a comment`;
        if (event.metadata?.comment_preview) {
          detail = (
            <div className="mt-1 text-sm text-gray-600 italic line-clamp-2">
              "{event.metadata.comment_preview}"
            </div>
          );
        }
        break;

      default:
        description = `${actorName} performed an action`;
    }

    return (
      <div className="flex gap-3 items-start">
        <div className={`flex-shrink-0 w-8 h-8 rounded-full border flex items-center justify-center ${eventConfig?.color || 'bg-gray-100 text-gray-700 border-gray-300'}`}>
          <EventIcon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-900">{description}</p>
          {detail}
          <p
            className="text-xs text-gray-500 mt-1"
            title={new Date(event.created_at).toLocaleString()}
          >
            {formatDistanceToNow(new Date(event.created_at), { addSuffix: true })}
          </p>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-red-900">Failed to load timeline</h3>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {showFilters && (
        <div className="flex items-center gap-3">
          <label htmlFor="event-filter" className="text-sm font-medium text-gray-700">
            Filter by:
          </label>
          <div className="relative">
            <select
              id="event-filter"
              value={selectedEventType}
              onChange={(e) => setSelectedEventType(e.target.value)}
              className="appearance-none bg-white border border-gray-300 rounded-lg px-4 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">All Events</option>
              {Object.entries(EVENT_TYPE_CONFIG).map(([type, config]) => (
                <option key={type} value={type}>
                  {config.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          </div>
        </div>
      )}

      {events.length === 0 ? (
        <div className="text-center py-12">
          <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No events to display</p>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {events.map((event) => (
              <div key={event.id} className="border-l-2 border-gray-200 pl-4 pb-4 last:pb-0">
                {renderEventContent(event)}
              </div>
            ))}
          </div>

          {offset < totalCount && (
            <div className="flex justify-center pt-2">
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    Load More
                    <span className="text-gray-500">({totalCount - offset} remaining)</span>
                  </>
                )}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
