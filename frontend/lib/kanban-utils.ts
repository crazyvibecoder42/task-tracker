import { Task, Author } from './api';

export type GroupingType = 'status' | 'owner' | 'priority';

export const STATUS_ORDER = ['backlog', 'todo', 'in_progress', 'blocked', 'review', 'done'];
export const PRIORITY_ORDER = ['P0', 'P1'];

/**
 * Group tasks by specified field
 * @param authors - Optional list of authors to pre-seed owner columns (used for owner grouping)
 */
export function groupTasks(tasks: Task[], groupBy: GroupingType, authors?: Author[]): Record<string, Task[]> {
  const groups: Record<string, Task[]> = {};

  if (groupBy === 'status') {
    STATUS_ORDER.forEach(status => { groups[status] = []; });
    tasks.forEach(task => {
      // Defensive: Initialize group if status is unexpected (new enum value)
      if (!groups[task.status]) {
        groups[task.status] = [];
      }
      groups[task.status].push(task);
    });
  } else if (groupBy === 'owner') {
    // Always initialize unassigned column first
    groups.unassigned = [];

    // Pre-seed columns for all authors if provided
    if (authors) {
      authors.forEach(author => {
        groups[`owner-${author.id}`] = [];
      });
    }

    // Distribute tasks into columns
    tasks.forEach(task => {
      const key = task.owner_id ? `owner-${task.owner_id}` : 'unassigned';
      if (!groups[key]) groups[key] = [];
      groups[key].push(task);
    });
  } else if (groupBy === 'priority') {
    PRIORITY_ORDER.forEach(priority => { groups[priority] = []; });
    tasks.forEach(task => {
      // Defensive: Initialize group if priority is unexpected (new enum value)
      if (!groups[task.priority]) {
        groups[task.priority] = [];
      }
      groups[task.priority].push(task);
    });
  }

  return groups;
}

/**
 * Get column header label based on grouping type
 */
export function getColumnLabel(columnId: string, groupBy: GroupingType, tasks: Task[]): string {
  if (groupBy === 'status') {
    const statusLabels: Record<string, string> = {
      backlog: 'Backlog',
      todo: 'To Do',
      in_progress: 'In Progress',
      blocked: 'Blocked',
      review: 'Review',
      done: 'Done'
    };
    return statusLabels[columnId] || columnId;
  } else if (groupBy === 'owner') {
    if (columnId === 'unassigned') return 'Unassigned';
    const task = tasks.find(t => t.owner_id?.toString() === columnId.replace('owner-', ''));
    return task?.owner?.name || 'Unknown Owner';
  } else {
    return columnId;
  }
}

/**
 * Calculate WIP limit status (green/yellow/red)
 */
export function getWipStatus(taskCount: number, limit: number | null): 'ok' | 'warning' | 'exceeded' | 'none' {
  if (limit == null) return 'none';
  const percentage = (taskCount / limit) * 100;
  if (percentage >= 100) return 'exceeded';
  if (percentage >= 80) return 'warning';
  return 'ok';
}
