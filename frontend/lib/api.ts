import { isOverdue as isTaskOverdue } from './date-utils';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:6001';

export interface Author {
  id: number;
  name: string;
  email: string;
  created_at: string;
}

export interface Comment {
  id: number;
  content: string;
  task_id: number;
  author_id: number | null;
  author: Author | null;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  tag: 'bug' | 'feature' | 'idea';
  priority: 'P0' | 'P1';
  status: 'backlog' | 'todo' | 'in_progress' | 'blocked' | 'review' | 'done';
  project_id: number;
  author_id: number | null;
  author: Author | null;
  owner_id: number | null;
  owner: Author | null;
  comments: Comment[];
  comment_count?: number;
  parent_task_id?: number;
  subtasks?: Task[];
  blocking_tasks?: Task[];
  blocked_tasks?: Task[];
  is_blocked?: boolean;
  due_date: string | null;
  estimated_hours: number | null;
  actual_hours: number | null;
  created_at: string;
  updated_at: string;
}

export interface TaskEvent {
  id: number;
  task_id: number;
  event_type: string;
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  actor_id: number | null;
  actor: Author | null;
  created_at: string;
  metadata: Record<string, any> | null;
}

export interface TaskDependency {
  id: number;
  blocking_task_id: number;
  blocked_task_id: number;
  created_at: string;
}

export interface TaskProgress {
  task_id: number;
  total_subtasks: number;
  completed_subtasks: number;
  completion_percentage: number;
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  author_id: number | null;
  author: Author | null;
  tasks?: Task[];
  created_at: string;
  updated_at: string;
}

export interface ProjectStats {
  id: number;
  name: string;
  total_tasks: number;
  backlog_tasks: number;
  todo_tasks: number;
  in_progress_tasks: number;
  blocked_tasks: number;
  review_tasks: number;
  done_tasks: number;
  p0_tasks: number;
  p1_tasks: number;
  bug_count: number;
  feature_count: number;
  idea_count: number;
}

export interface OverallStats {
  total_projects: number;
  total_tasks: number;
  backlog_tasks: number;
  todo_tasks: number;
  in_progress_tasks: number;
  blocked_tasks: number;
  review_tasks: number;
  done_tasks: number;
  p0_incomplete: number;
  completion_rate: number;
}

// Helper function to check if a task is overdue (re-exported from date-utils)
export function isOverdue(task: Task): boolean {
  return isTaskOverdue(task);
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP error! status: ${response.status}`);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// Authors
export const getAuthors = () => fetchApi<Author[]>('/api/authors');
export const createAuthor = (data: { name: string; email: string }) =>
  fetchApi<Author>('/api/authors', { method: 'POST', body: JSON.stringify(data) });

// Projects
export const getProjects = () => fetchApi<Project[]>('/api/projects');
export const getProject = (id: number) => fetchApi<Project>('/api/projects/' + id);
export const getProjectStats = (id: number) => fetchApi<ProjectStats>('/api/projects/' + id + '/stats');
export const createProject = (data: { name: string; description?: string; author_id?: number }) =>
  fetchApi<Project>('/api/projects', { method: 'POST', body: JSON.stringify(data) });
export const updateProject = (id: number, data: { name?: string; description?: string }) =>
  fetchApi<Project>('/api/projects/' + id, { method: 'PUT', body: JSON.stringify(data) });
export const deleteProject = (id: number) =>
  fetchApi<void>('/api/projects/' + id, { method: 'DELETE' });

// Tasks
export const getTasks = (params?: {
  project_id?: number;
  status?: string;
  priority?: string;
  tag?: string;
  q?: string;
  due_before?: string;
  due_after?: string;
  overdue?: boolean;
}) => {
  const searchParams = new URLSearchParams();
  if (params?.project_id) searchParams.append('project_id', String(params.project_id));
  if (params?.q) searchParams.append('q', params.q);
  if (params?.status) searchParams.append('status', params.status);
  if (params?.priority) searchParams.append('priority', params.priority);
  if (params?.tag) searchParams.append('tag', params.tag);
  if (params?.due_before) searchParams.append('due_before', params.due_before);
  if (params?.due_after) searchParams.append('due_after', params.due_after);
  if (params?.overdue !== undefined) searchParams.append('overdue', String(params.overdue));
  const query = searchParams.toString();
  return fetchApi<Task[]>('/api/tasks' + (query ? '?' + query : ''));
};
export const getTask = (id: number) => fetchApi<Task>('/api/tasks/' + id);
export const getOverdueTasks = (limit: number = 5) =>
  fetchApi<Task[]>('/api/tasks/overdue?limit=' + limit);
export const getUpcomingTasks = (days: number = 7, limit: number = 5) =>
  fetchApi<Task[]>('/api/tasks/upcoming?days=' + days + '&limit=' + limit);
export const createTask = (data: {
  project_id: number;
  title: string;
  description?: string;
  tag?: 'bug' | 'feature' | 'idea';
  priority?: 'P0' | 'P1';
  author_id?: number;
  parent_task_id?: number;
  due_date?: string;
  estimated_hours?: number;
}) => fetchApi<Task>('/api/tasks', { method: 'POST', body: JSON.stringify(data) });
export const updateTask = (id: number, data: {
  title?: string;
  description?: string;
  tag?: 'bug' | 'feature' | 'idea';
  priority?: 'P0' | 'P1';
  status?: 'backlog' | 'todo' | 'in_progress' | 'blocked' | 'review' | 'done';
  owner_id?: number | null;
  parent_task_id?: number;
  due_date?: string | null;
  estimated_hours?: number | null;
  actual_hours?: number | null;
}) => fetchApi<Task>('/api/tasks/' + id, { method: 'PUT', body: JSON.stringify(data) });
export const deleteTask = (id: number) =>
  fetchApi<void>('/api/tasks/' + id, { method: 'DELETE' });

// Task Dependencies and Subtasks
export const getTaskSubtasks = (taskId: number) =>
  fetchApi<Task[]>('/api/tasks/' + taskId + '/subtasks');
export const getTaskDependencies = (taskId: number) =>
  fetchApi<Task>('/api/tasks/' + taskId + '/dependencies');
export const addTaskDependency = (taskId: number, blockingTaskId: number) =>
  fetchApi<TaskDependency>('/api/tasks/' + taskId + '/dependencies', {
    method: 'POST',
    body: JSON.stringify({ blocking_task_id: blockingTaskId })
  });
export const removeTaskDependency = (taskId: number, blockingTaskId: number) =>
  fetchApi<void>('/api/tasks/' + taskId + '/dependencies/' + blockingTaskId, {
    method: 'DELETE'
  });
export const getActionableTasks = (params?: { project_id?: number; owner_id?: number }) => {
  const searchParams = new URLSearchParams();
  if (params?.project_id) searchParams.append('project_id', String(params.project_id));
  if (params?.owner_id) searchParams.append('owner_id', String(params.owner_id));
  const query = searchParams.toString();
  return fetchApi<Task[]>('/api/tasks/actionable' + (query ? '?' + query : ''));
};
export const getTaskProgress = (taskId: number) =>
  fetchApi<TaskProgress>('/api/tasks/' + taskId + '/progress');

// Task Events
export const getTaskEvents = (taskId: number, params?: {
  event_type?: string;
  limit?: number;
  offset?: number;
}) => {
  const searchParams = new URLSearchParams();
  if (params?.event_type) searchParams.append('event_type', params.event_type);
  if (params?.limit) searchParams.append('limit', String(params.limit));
  if (params?.offset) searchParams.append('offset', String(params.offset));
  const query = searchParams.toString();
  return fetchApi<{ events: TaskEvent[]; total_count: number }>(
    '/api/tasks/' + taskId + '/events' + (query ? '?' + query : '')
  );
};

export const getProjectEvents = (projectId: number, params?: {
  event_type?: string;
  limit?: number;
  offset?: number;
}) => {
  const searchParams = new URLSearchParams();
  if (params?.event_type) searchParams.append('event_type', params.event_type);
  if (params?.limit) searchParams.append('limit', String(params.limit));
  if (params?.offset) searchParams.append('offset', String(params.offset));
  const query = searchParams.toString();
  return fetchApi<{ events: TaskEvent[]; total_count: number }>(
    '/api/projects/' + projectId + '/events' + (query ? '?' + query : '')
  );
};

// Comments
export const getComments = (taskId: number) => fetchApi<Comment[]>('/api/tasks/' + taskId + '/comments');
export const createComment = (taskId: number, data: { content: string; author_id?: number }) =>
  fetchApi<Comment>('/api/tasks/' + taskId + '/comments', { method: 'POST', body: JSON.stringify(data) });
export const deleteComment = (id: number) =>
  fetchApi<void>('/api/comments/' + id, { method: 'DELETE' });

// Stats
export const getOverallStats = () => fetchApi<OverallStats>('/api/stats');
