'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { AlertCircle, Clock, FolderKanban, TrendingUp, Inbox, Circle, PlayCircle, XCircle, Eye, CheckCircle2, Users } from 'lucide-react';
import { getOverallStats, getProjects, getTasks, getOverdueTasks, getUpcomingTasks, OverallStats, Project, Task } from '@/lib/api';
import { STATUS_CONFIG } from '@/components/StatusConfig';
import { formatDistanceToNow } from 'date-fns';
import { useAuth } from '@/contexts/AuthContext';

export default function Dashboard() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [stats, setStats] = useState<OverallStats | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [recentTasks, setRecentTasks] = useState<Task[]>([]);
  const [overdueTasks, setOverdueTasks] = useState<Task[]>([]);
  const [upcomingTasks, setUpcomingTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // CRITICAL: Only load data if user is authenticated
    // This prevents API calls during logout/redirect
    if (isAuthenticated && !authLoading) {
      loadData();
    } else if (!authLoading && !isAuthenticated) {
      // Not authenticated - redirect to login
      // This handles cases where middleware let through stale/invalid tokens
      window.location.href = '/login';
    }
  }, [isAuthenticated, authLoading]);

  const loadData = async () => {
    try {
      const [statsData, projectsData, tasksData, overdueData, upcomingData] = await Promise.all([
        getOverallStats(),
        getProjects(),
        getTasks(),
        getOverdueTasks(5),
        getUpcomingTasks(7, 5)
      ]);
      setStats(statsData);
      setProjects(projectsData);
      setRecentTasks(tasksData.slice(0, 5));
      setOverdueTasks(overdueData);
      setUpcomingTasks(upcomingData);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Overview of your projects and tasks</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Projects</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.total_projects || 0}</p>
            </div>
            <div className="p-3 bg-indigo-50 rounded-lg">
              <FolderKanban className="w-6 h-6 text-indigo-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Backlog</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.backlog_tasks || 0}</p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <Inbox className="w-6 h-6 text-gray-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">To Do</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.todo_tasks || 0}</p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg">
              <Circle className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">In Progress</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.in_progress_tasks || 0}</p>
            </div>
            <div className="p-3 bg-yellow-50 rounded-lg">
              <PlayCircle className="w-6 h-6 text-yellow-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Blocked</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.blocked_tasks || 0}</p>
            </div>
            <div className="p-3 bg-red-50 rounded-lg">
              <XCircle className="w-6 h-6 text-red-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Review</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.review_tasks || 0}</p>
            </div>
            <div className="p-3 bg-purple-50 rounded-lg">
              <Eye className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Done</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.done_tasks || 0}</p>
            </div>
            <div className="p-3 bg-green-50 rounded-lg">
              <CheckCircle2 className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">P0 Incomplete</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.p0_incomplete || 0}</p>
            </div>
            <div className="p-3 bg-red-50 rounded-lg">
              <AlertCircle className="w-6 h-6 text-red-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Completion Rate */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Completion Rate</h2>
          <div className="flex items-center gap-2 text-green-600">
            <TrendingUp className="w-4 h-4" />
            <span className="font-medium">{stats?.completion_rate || 0}%</span>
          </div>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-green-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${stats?.completion_rate || 0}%` }}
          ></div>
        </div>
      </div>

      {/* Upcoming & Overdue */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Upcoming & Overdue</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Overdue Tasks */}
          <div className="bg-red-50 rounded-xl border border-red-200 shadow-sm">
            <div className="p-6 border-b border-red-200 flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertCircle className="w-5 h-5 text-red-600" />
              </div>
              <h3 className="text-base font-semibold text-red-900">Overdue Tasks</h3>
            </div>
            <div className="divide-y divide-red-100">
              {overdueTasks.length === 0 ? (
                <p className="p-6 text-red-600 text-center text-sm">No overdue tasks</p>
              ) : (
                overdueTasks.map((task) => (
                  <Link
                    key={task.id}
                    href={`/tasks/${task.id}`}
                    className="block p-4 hover:bg-red-100 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-red-900 truncate">{task.title}</p>
                        {task.due_date && (
                          <p className="text-xs text-red-600 mt-1">
                            Due {formatDistanceToNow(new Date(task.due_date), { addSuffix: true })}
                          </p>
                        )}
                      </div>
                      <span
                        className={`shrink-0 px-2 py-0.5 text-xs rounded-full font-medium ${
                          task.priority === 'P0'
                            ? 'bg-red-200 text-red-900'
                            : 'bg-red-100 text-red-700'
                        }`}
                      >
                        {task.priority}
                      </span>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>

          {/* Upcoming Tasks */}
          <div className="bg-yellow-50 rounded-xl border border-yellow-200 shadow-sm">
            <div className="p-6 border-b border-yellow-200 flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Clock className="w-5 h-5 text-yellow-600" />
              </div>
              <h3 className="text-base font-semibold text-yellow-900">Upcoming Tasks</h3>
            </div>
            <div className="divide-y divide-yellow-100">
              {upcomingTasks.length === 0 ? (
                <p className="p-6 text-yellow-600 text-center text-sm">No upcoming tasks</p>
              ) : (
                upcomingTasks.map((task) => (
                  <Link
                    key={task.id}
                    href={`/tasks/${task.id}`}
                    className="block p-4 hover:bg-yellow-100 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-yellow-900 truncate">{task.title}</p>
                        {task.due_date && (
                          <p className="text-xs text-yellow-600 mt-1">
                            Due {formatDistanceToNow(new Date(task.due_date), { addSuffix: true })}
                          </p>
                        )}
                      </div>
                      <span
                        className={`shrink-0 px-2 py-0.5 text-xs rounded-full font-medium ${
                          task.priority === 'P0'
                            ? 'bg-yellow-200 text-yellow-900'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {task.priority}
                      </span>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Tasks */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="p-6 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">Recent Tasks</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {recentTasks.length === 0 ? (
              <p className="p-6 text-gray-500 text-center">No tasks yet</p>
            ) : (
              recentTasks.map((task) => (
                <Link
                  key={task.id}
                  href={`/tasks/${task.id}`}
                  className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {(() => {
                      const StatusIcon = STATUS_CONFIG[task.status].icon;
                      const statusColor = task.status === 'done' ? 'text-green-500' :
                                         task.status === 'in_progress' ? 'text-yellow-500' :
                                         task.status === 'blocked' ? 'text-red-500' :
                                         task.status === 'review' ? 'text-purple-500' :
                                         task.status === 'todo' ? 'text-blue-500' :
                                         'text-gray-500';
                      return <StatusIcon className={`w-4 h-4 ${statusColor}`} />;
                    })()}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-gray-500">#{task.id}</span>
                        <p className="font-medium text-gray-900">{task.title}</p>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span
                          className={`px-2 py-0.5 text-xs rounded-full ${
                            task.tag === 'bug'
                              ? 'bg-red-100 text-red-700'
                              : task.tag === 'feature'
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-purple-100 text-purple-700'
                          }`}
                        >
                          {task.tag}
                        </span>
                        <span
                          className={`px-2 py-0.5 text-xs rounded-full ${
                            task.priority === 'P0'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {task.priority}
                        </span>
                      </div>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
          {recentTasks.length > 0 && (
            <div className="p-4 border-t border-gray-100">
              <Link
                href="/tasks"
                className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
              >
                View all tasks →
              </Link>
            </div>
          )}
        </div>

        {/* Projects */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="p-6 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">Projects</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {projects.length === 0 ? (
              <p className="p-6 text-gray-500 text-center">No projects yet</p>
            ) : (
              projects.map((project) => (
                <Link
                  key={project.id}
                  href={`/projects/${project.id}`}
                  className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-50 rounded-lg">
                      <FolderKanban className="w-4 h-4 text-indigo-600" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-gray-900">{project.name}</p>
                        {project.team && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-indigo-100 text-indigo-700 rounded-full">
                            <Users className="w-3 h-3" />
                            {project.team.name}
                          </span>
                        )}
                      </div>
                      {project.description && (
                        <p className="text-sm text-gray-500 truncate max-w-xs">
                          {project.description}
                        </p>
                      )}
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
          <div className="p-4 border-t border-gray-100">
            <Link
              href="/projects/new"
              className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
            >
              Create new project →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
