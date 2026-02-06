'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { AlertCircle, CheckCircle2, Clock, FolderKanban, TrendingUp } from 'lucide-react';
import { getOverallStats, getProjects, getTasks, OverallStats, Project, Task } from '@/lib/api';

export default function Dashboard() {
  const [stats, setStats] = useState<OverallStats | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [recentTasks, setRecentTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [statsData, projectsData, tasksData] = await Promise.all([
        getOverallStats(),
        getProjects(),
        getTasks()
      ]);
      setStats(statsData);
      setProjects(projectsData);
      setRecentTasks(tasksData.slice(0, 5));
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
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
              <p className="text-sm text-gray-500">Pending Tasks</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.pending_tasks || 0}</p>
            </div>
            <div className="p-3 bg-yellow-50 rounded-lg">
              <Clock className="w-6 h-6 text-yellow-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Completed Tasks</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.completed_tasks || 0}</p>
            </div>
            <div className="p-3 bg-green-50 rounded-lg">
              <CheckCircle2 className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">P0 Pending</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.p0_pending || 0}</p>
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
                    <span
                      className={`w-2 h-2 rounded-full ${
                        task.status === 'completed' ? 'bg-green-500' : 'bg-yellow-500'
                      }`}
                    ></span>
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
                      <p className="font-medium text-gray-900">{project.name}</p>
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
