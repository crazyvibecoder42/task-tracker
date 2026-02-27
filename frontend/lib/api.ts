import { isOverdue as isTaskOverdue } from './date-utils';

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:6001';

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
  status: 'backlog' | 'todo' | 'in_progress' | 'blocked' | 'review' | 'done' | 'not_needed';
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
  attachments?: Attachment[];
  external_links?: ExternalLink[];
  custom_metadata?: Record<string, string>;
  subproject_id?: number | null;
  subproject?: Subproject | null;
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

export interface Attachment {
  id: number;
  task_id: number;
  filename: string;
  original_filename: string;
  filepath: string;
  mime_type: string;
  file_size: number;
  uploaded_by: number | null;
  uploader: Author | null;
  created_at: string;
}

export interface ExternalLink {
  url: string;
  label: string | null;
  created_at: string;
}

export interface Subproject {
  id: number;
  project_id: number;
  name: string;
  subproject_number: number;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Team {
  id: number;
  name: string;
  description: string | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface TeamMember {
  id: number;
  team_id: number;
  user_id: number;
  user: Author | null;
  role: 'admin' | 'member';
  created_at: string;
}

export interface TeamWithProjects extends Team {
  projects: Project[];
  members: TeamMember[];
  creator: Author | null;
}

export interface TeamCreate {
  name: string;
  description?: string;
}

export interface TeamUpdate {
  name?: string;
  description?: string;
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  author_id: number | null;
  author: Author | null;
  team_id?: number | null;
  team?: Team | null;
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
  not_needed_tasks: number;
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
  not_needed_tasks: number;
  p0_incomplete: number;
  completion_rate: number;
}

// Helper function to check if a task is overdue (re-exported from date-utils)
export function isOverdue(task: Task): boolean {
  return isTaskOverdue(task);
}

// Get access token from localStorage
function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

// Clear access token and redirect to login
function handleAuthError(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('access_token');
  // Only redirect if not already on login page
  if (!window.location.pathname.startsWith('/login')) {
    window.location.href = '/login';
  }
}

// Try to refresh access token (returns new token or null)
async function tryRefreshToken(): Promise<string | null> {
  console.debug('[API] Attempting token refresh');

  try {
    const response = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      credentials: 'include', // Send refresh token cookie
    });

    if (response.ok) {
      const data = await response.json();
      const newToken = data.access_token;
      localStorage.setItem('access_token', newToken);
      console.info('[API] Token refresh successful');
      return newToken;
    }

    // Refresh failed or not implemented (501)
    console.debug('[API] Token refresh failed:', response.status);
    return null;
  } catch (error) {
    console.error('[API] Token refresh error:', error);
    return null;
  }
}

async function fetchApi<T>(endpoint: string, options?: RequestInit, retryCount = 0): Promise<T> {
  // Add auth headers
  const token = getAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options?.headers as Record<string, string>,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include', // Include cookies for refresh token
  });

  // Handle 401 Unauthorized - try to refresh token once
  if (response.status === 401 && retryCount === 0) {
    console.debug('[API] Received 401, attempting token refresh');

    const newToken = await tryRefreshToken();

    if (newToken) {
      // Retry the original request with new token
      console.debug('[API] Retrying request with new token');
      return fetchApi<T>(endpoint, options, retryCount + 1);
    } else {
      // Refresh failed, redirect to login
      console.info('[API] Token refresh failed, redirecting to login');
      handleAuthError();
      throw new Error('Authentication required');
    }
  }

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP error! status: ${response.status}`);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// Authentication
export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export const changePassword = (data: ChangePasswordRequest) =>
  fetchApi<{ message: string }>('/api/auth/change-password', {
    method: 'PUT',
    body: JSON.stringify(data)
  });

// API Keys
export interface ApiKey {
  id: number;
  name: string;
  key?: string;  // Only present immediately after creation
  expires_at: string | null;
  created_at: string;
  last_used_at: string | null;
  is_active: boolean;
}

export interface CreateApiKeyRequest {
  name: string;
  expires_days?: number;  // 1-365 or omit for never expires
}

export const createApiKey = (data: CreateApiKeyRequest) =>
  fetchApi<ApiKey>('/api/auth/api-keys', {
    method: 'POST',
    body: JSON.stringify(data)
  });

export const listApiKeys = () =>
  fetchApi<ApiKey[]>('/api/auth/api-keys');

export const revokeApiKey = (keyId: number) =>
  fetchApi<void>(`/api/auth/api-keys/${keyId}`, {
    method: 'DELETE'
  });

// Users (renamed from Authors)
export const getAuthors = () => fetchApi<Author[]>('/api/users');
export const createAuthor = (data: { name: string; email: string; password: string }) =>
  fetchApi<Author>('/api/users', { method: 'POST', body: JSON.stringify(data) });
export const deleteAuthor = (id: number) =>
  fetchApi<void>('/api/users/' + id, { method: 'DELETE' });

// Projects
export const getProjects = () => fetchApi<Project[]>('/api/projects');
export const getProject = (id: number) => fetchApi<Project>('/api/projects/' + id);
export const getProjectStats = (id: number) => fetchApi<ProjectStats>('/api/projects/' + id + '/stats');
export const createProject = (data: { name: string; description?: string; team_id?: number }) =>
  fetchApi<Project>('/api/projects', { method: 'POST', body: JSON.stringify(data) });
export const updateProject = (id: number, data: { name?: string; description?: string }) =>
  fetchApi<Project>('/api/projects/' + id, { method: 'PUT', body: JSON.stringify(data) });
export const deleteProject = (id: number) =>
  fetchApi<void>('/api/projects/' + id, { method: 'DELETE' });

// Subprojects
export const getSubprojects = (projectId: number) =>
  fetchApi<Subproject[]>(`/api/projects/${projectId}/subprojects`);

export const createSubproject = (projectId: number, name: string) =>
  fetchApi<Subproject>(`/api/projects/${projectId}/subprojects`, {
    method: 'POST',
    body: JSON.stringify({ name }),
  });

export const updateSubproject = (subprojectId: number, name: string) =>
  fetchApi<Subproject>(`/api/subprojects/${subprojectId}`, {
    method: 'PUT',
    body: JSON.stringify({ name }),
  });

export const deleteSubproject = (subprojectId: number) =>
  fetchApi<void>(`/api/subprojects/${subprojectId}`, { method: 'DELETE' });

// Project Team Transfer
export interface ProjectTeamTransfer {
  team_id: number | null;  // null = convert to personal project
}

export const transferProject = (id: number, data: ProjectTeamTransfer) =>
  fetchApi<Project>('/api/projects/' + id + '/transfer', {
    method: 'PUT',
    body: JSON.stringify(data)
  });

// Project Members
export interface ProjectMember {
  id: number;
  project_id: number;
  user_id: number;
  user: Author;
  role: string;
}
export const getProjectMembers = (projectId: number) =>
  fetchApi<ProjectMember[]>('/api/projects/' + projectId + '/members');

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
  parent_task_id?: number;
  due_date?: string;
  estimated_hours?: number;
}) => fetchApi<Task>('/api/tasks', { method: 'POST', body: JSON.stringify(data) });
export const updateTask = (id: number, data: {
  title?: string;
  description?: string;
  tag?: 'bug' | 'feature' | 'idea';
  priority?: 'P0' | 'P1';
  status?: 'backlog' | 'todo' | 'in_progress' | 'blocked' | 'review' | 'done' | 'not_needed';
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
export const createComment = (taskId: number, data: { content: string }) =>
  fetchApi<Comment>('/api/tasks/' + taskId + '/comments', { method: 'POST', body: JSON.stringify(data) });
export const deleteComment = (id: number) =>
  fetchApi<void>('/api/comments/' + id, { method: 'DELETE' });

// Attachments
export const uploadAttachment = async (taskId: number, file: File, uploadedBy?: number) => {
  const formData = new FormData();
  formData.append('file', file);

  const token = getAccessToken();
  if (!token) {
    throw new Error('Authentication required');
  }

  const url = `${API_BASE}/api/tasks/${taskId}/attachments${uploadedBy ? `?uploaded_by=${uploadedBy}` : ''}`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    credentials: 'include', // Include cookies for refresh token
    body: formData,
  });

  if (!response.ok) {
    // Handle 401 with token refresh
    if (response.status === 401) {
      console.debug('[API] Upload received 401, attempting token refresh');
      const newToken = await tryRefreshToken();  // FIX: Use correct function name
      if (newToken) {
        // Retry upload with new token
        const retryResponse = await fetch(url, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${newToken}`,
          },
          credentials: 'include',
          body: formData,
        });
        if (retryResponse.ok) {
          return retryResponse.json() as Promise<Attachment>;
        }
      }
    }

    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json() as Promise<Attachment>;
};

export const getAttachments = (taskId: number) =>
  fetchApi<Attachment[]>('/api/tasks/' + taskId + '/attachments');

export const deleteAttachment = (taskId: number, attachmentId: number, actorId?: number) =>
  fetchApi<void>(
    '/api/tasks/' + taskId + '/attachments/' + attachmentId + (actorId ? '?actor_id=' + actorId : ''),
    { method: 'DELETE' }
  );

// External Links
export const addExternalLink = (taskId: number, data: { url: string; label?: string }, actorId?: number) =>
  fetchApi<{ message: string; link: ExternalLink }>(
    '/api/tasks/' + taskId + '/links' + (actorId ? '?actor_id=' + actorId : ''),
    { method: 'POST', body: JSON.stringify(data) }
  );

export const removeExternalLink = (taskId: number, url: string, actorId?: number) => {
  const params = new URLSearchParams({ url });
  if (actorId) params.append('actor_id', String(actorId));
  return fetchApi<void>('/api/tasks/' + taskId + '/links?' + params.toString(), { method: 'DELETE' });
};

// Custom Metadata
export const updateMetadata = (taskId: number, data: { key: string; value: string }, actorId?: number) =>
  fetchApi<{ message: string; key: string; value: string }>(
    '/api/tasks/' + taskId + '/metadata' + (actorId ? '?actor_id=' + actorId : ''),
    { method: 'PUT', body: JSON.stringify(data) }
  );

export const deleteMetadata = (taskId: number, key: string, actorId?: number) =>
  fetchApi<void>(
    '/api/tasks/' + taskId + '/metadata/' + encodeURIComponent(key) + (actorId ? '?actor_id=' + actorId : ''),
    { method: 'DELETE' }
  );

// Stats
export const getOverallStats = () => fetchApi<OverallStats>('/api/stats');

// Kanban settings API
export interface KanbanWipLimits {
  todo?: number | null;
  in_progress?: number | null;
  blocked?: number | null;
  review?: number | null;
  backlog?: number | null;
  done?: number | null;
}

export interface KanbanSettings {
  wip_limits: KanbanWipLimits;
  hidden_columns: string[];
}

export const getKanbanSettings = (projectId: number) =>
  fetchApi<KanbanSettings>(`/api/projects/${projectId}/kanban-settings`);

export const updateKanbanSettings = (projectId: number, settings: KanbanSettings) =>
  fetchApi<KanbanSettings>(`/api/projects/${projectId}/kanban-settings`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  });

// Bulk update tasks (for drag-and-drop)
export const bulkUpdateTasks = (taskIds: number[], updates: Partial<Task>) =>
  fetchApi<{success: boolean; processed_count: number}>('/api/tasks/bulk-update', {
    method: 'POST',
    body: JSON.stringify({ task_ids: taskIds, updates }),
  });

// Teams
export const getTeams = () => fetchApi<Team[]>('/api/teams');
export const getTeam = (id: number) => fetchApi<TeamWithProjects>('/api/teams/' + id);
export const createTeam = (data: TeamCreate) =>
  fetchApi<Team>('/api/teams', { method: 'POST', body: JSON.stringify(data) });
export const updateTeam = (id: number, data: TeamUpdate) =>
  fetchApi<Team>('/api/teams/' + id, { method: 'PUT', body: JSON.stringify(data) });
export const deleteTeam = (id: number) =>
  fetchApi<void>('/api/teams/' + id, { method: 'DELETE' });

// Team Members
export const getTeamMembers = (teamId: number) =>
  fetchApi<TeamMember[]>('/api/teams/' + teamId + '/members');
export const getAvailableUsersForTeam = (teamId: number) =>
  fetchApi<Author[]>('/api/teams/' + teamId + '/available-users');
export const addTeamMember = (teamId: number, data: { user_id: number; role: 'admin' | 'member' }) =>
  fetchApi<TeamMember>('/api/teams/' + teamId + '/members', {
    method: 'POST',
    body: JSON.stringify(data)
  });
export const updateTeamMember = (teamId: number, userId: number, data: { role: 'admin' | 'member' }) =>
  fetchApi<TeamMember>('/api/teams/' + teamId + '/members/' + userId, {
    method: 'PUT',
    body: JSON.stringify(data)
  });
export const removeTeamMember = (teamId: number, userId: number) =>
  fetchApi<void>('/api/teams/' + teamId + '/members/' + userId, { method: 'DELETE' });
