'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FolderKanban, Grid3x3, LayoutDashboard, ListTodo, Plus, Users } from 'lucide-react';
import { getProjects, getTeams, Project, Team } from '@/lib/api';
import UserMenu from '@/components/UserMenu';
import { useAuth } from '@/contexts/AuthContext';

export default function Sidebar() {
  const pathname = usePathname();
  const { hasRole } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);

  useEffect(() => {
    loadProjects();
    loadTeams();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await getProjects();
      setProjects(data);
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
  };

  const loadTeams = async () => {
    try {
      const data = await getTeams();
      setTeams(data);
    } catch (error) {
      console.error('Failed to load teams:', error);
    }
  };

  const isActive = (path: string) => pathname === path;

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <Link href="/" className="flex items-center gap-2">
          <ListTodo className="w-6 h-6 text-indigo-600" />
          <span className="text-xl font-bold text-gray-900">Task Tracker</span>
        </Link>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        <Link
          href="/"
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            isActive('/')
              ? 'bg-indigo-50 text-indigo-600'
              : 'text-gray-700 hover:bg-gray-100'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          Dashboard
        </Link>

        <Link
          href="/tasks"
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            isActive('/tasks')
              ? 'bg-indigo-50 text-indigo-600'
              : 'text-gray-700 hover:bg-gray-100'
          }`}
        >
          <ListTodo className="w-4 h-4" />
          All Tasks
        </Link>

        <Link
          href="/kanban"
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            pathname === '/kanban' || pathname?.startsWith('/projects/') && pathname?.includes('/board')
              ? 'bg-indigo-50 text-indigo-600'
              : 'text-gray-700 hover:bg-gray-100'
          }`}
        >
          <Grid3x3 className="w-4 h-4" />
          Kanban Board
        </Link>

        {/* Admin-only: Authors/Users Management */}
        {hasRole('admin') && (
          <Link
            href="/authors"
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              isActive('/authors')
                ? 'bg-indigo-50 text-indigo-600'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <Users className="w-4 h-4" />
            Authors
          </Link>
        )}

        {/* Teams Section */}
        <div className="pt-4">
          <div className="flex items-center justify-between px-3 mb-2">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Teams
            </span>
            <Link
              href="/teams/new"
              className="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700"
              title="Create Team"
            >
              <Plus className="w-4 h-4" />
            </Link>
          </div>

          <div className="space-y-1">
            {teams.map((team) => (
              <Link
                key={team.id}
                href={`/teams/${team.id}`}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  pathname === `/teams/${team.id}`
                    ? 'bg-indigo-50 text-indigo-600'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Users className="w-4 h-4" />
                <span className="truncate">{team.name}</span>
              </Link>
            ))}

            {teams.length === 0 && (
              <p className="px-3 py-2 text-sm text-gray-500">No teams yet</p>
            )}
          </div>
        </div>

        <div className="pt-4">
          <div className="flex items-center justify-between px-3 mb-2">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Projects
            </span>
            <Link
              href="/projects/new"
              className="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700"
              title="New Project"
            >
              <Plus className="w-4 h-4" />
            </Link>
          </div>

          <div className="space-y-1">
            {projects.map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  pathname === `/projects/${project.id}`
                    ? 'bg-indigo-50 text-indigo-600'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <FolderKanban className="w-4 h-4" />
                <span className="truncate">{project.name}</span>
              </Link>
            ))}

            {projects.length === 0 && (
              <p className="px-3 py-2 text-sm text-gray-500">No projects yet</p>
            )}
          </div>
        </div>
      </nav>

      <UserMenu />
    </aside>
  );
}
