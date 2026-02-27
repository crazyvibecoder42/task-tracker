'use client';

import { useEffect, useState, useRef, Suspense } from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { FolderKanban, Grid3x3, LayoutDashboard, ListTodo, Plus, Users } from 'lucide-react';
import { getProjects, getTeams, getSubprojects, createSubproject, Project, Team, Subproject } from '@/lib/api';
import UserMenu from '@/components/UserMenu';
import { useAuth } from '@/contexts/AuthContext';

function SubprojectSection({
  activeProjectId,
  subprojects,
  onSubprojectCreated,
}: {
  activeProjectId: number;
  subprojects: Subproject[];
  onSubprojectCreated: () => void;
}) {
  const searchParams = useSearchParams();
  const activeSubprojectParam = searchParams?.get('subproject'); // null, "0", or numeric string
  const [showInput, setShowInput] = useState(false);
  const [newName, setNewName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = async () => {
    if (!newName.trim() || isCreating) return;
    setIsCreating(true);
    try {
      await createSubproject(activeProjectId, newName.trim());
      setNewName('');
      setShowInput(false);
      onSubprojectCreated();
    } catch (e) {
      console.error('Failed to create subproject:', e);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="pt-3">
      <div className="flex items-center justify-between pl-6 pr-3 mb-1">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Sub-projects
        </span>
        <button
          onClick={() => setShowInput(true)}
          className="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700"
          title="New Sub-project"
        >
          <Plus className="w-3 h-3" />
        </button>
      </div>

      <div className="space-y-0.5">
        {/* All Tasks (no param) */}
        <Link
          href={`/projects/${activeProjectId}`}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            activeSubprojectParam === null
              ? 'bg-indigo-50 text-indigo-600'
              : 'text-gray-700 hover:bg-gray-100'
          }`}
        >
          <span className="text-gray-400">●</span>
          All Tasks
        </Link>

        {/* Sub-project entries */}
        {subprojects.map((sp) => (
          <Link
            key={sp.id}
            href={`/projects/${activeProjectId}?subproject=${sp.id}`}
            className={`flex items-center gap-2 pl-6 pr-3 py-1.5 rounded-lg text-sm transition-colors ${
              activeSubprojectParam === String(sp.id)
                ? 'bg-indigo-50 text-indigo-600 font-medium'
                : sp.is_active
                ? 'text-gray-700 hover:bg-gray-100'
                : 'text-gray-400 hover:bg-gray-50'
            }`}
          >
            <span className={sp.is_active ? 'text-green-500' : 'text-gray-300'}>●</span>
            <span className="truncate">{sp.name}</span>
          </Link>
        ))}

        {/* Inline creation input */}
        {showInput && (
          <div className="pl-6 pr-3 py-1">
            <input
              autoFocus
              type="text"
              value={newName}
              disabled={isCreating}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreate();
                if (e.key === 'Escape') { setShowInput(false); setNewName(''); }
              }}
              onBlur={() => { if (!isCreating) { setShowInput(false); setNewName(''); } }}
              placeholder="Sub-project name…"
              className="w-full text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default function Sidebar() {
  const pathname = usePathname();
  const { hasRole } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [subprojects, setSubprojects] = useState<Subproject[]>([]);
  const subprojectsRequestIdRef = useRef(0);
  const activeProjectIdRef = useRef<number | null>(null);

  const projectMatch = pathname?.match(/^\/projects\/(\d+)/);
  const activeProjectId = projectMatch ? Number(projectMatch[1]) : null;
  activeProjectIdRef.current = activeProjectId; // keep ref current for async callbacks

  useEffect(() => {
    loadProjects();
    loadTeams();
  }, []);

  const fetchSubprojects = (projectId: number) => {
    const requestId = ++subprojectsRequestIdRef.current;
    const guard = () => requestId === subprojectsRequestIdRef.current && projectId === activeProjectIdRef.current;
    getSubprojects(projectId)
      .then(data => { if (guard()) setSubprojects(data); })
      .catch(() => { if (guard()) setSubprojects([]); });
  };

  useEffect(() => {
    if (activeProjectId) {
      fetchSubprojects(activeProjectId);
    } else {
      ++subprojectsRequestIdRef.current; // invalidate any in-flight request
      setSubprojects([]);
    }
  }, [activeProjectId]);

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

  const loadSubprojects = () => {
    if (activeProjectId) fetchSubprojects(activeProjectId);
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
              <div key={project.id}>
                <Link
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
                {activeProjectId === project.id && (
                  <Suspense fallback={null}>
                    <SubprojectSection
                      activeProjectId={activeProjectId}
                      subprojects={subprojects}
                      onSubprojectCreated={loadSubprojects}
                    />
                  </Suspense>
                )}
              </div>
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
