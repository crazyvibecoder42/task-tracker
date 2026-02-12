'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { createProject, getTeams, getTeam, Team, TeamMember } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

export default function NewProject() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [teamId, setTeamId] = useState('');
  const [teams, setTeams] = useState<Team[]>([]);
  const [adminTeams, setAdminTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Only load teams when user is available (auth loaded)
    if (user?.id) {
      loadTeams();
    }
    // Pre-select team from query param
    const teamParam = searchParams.get('team');
    if (teamParam) {
      setTeamId(teamParam);
    }
  }, [searchParams, user?.id]);

  const loadTeams = async () => {
    console.debug('[NewProject] Loading teams');
    try {
      const data = await getTeams();
      setTeams(data);

      // Load full team details to check membership roles
      // Use allSettled to handle partial failures gracefully
      const teamDetailsPromises = data.map(team => getTeam(team.id));
      const teamDetailsResults = await Promise.allSettled(teamDetailsPromises);

      // Extract successful team fetches, log failures
      const teamDetails = teamDetailsResults
        .filter((result, idx) => {
          if (result.status === 'rejected') {
            console.error(`[NewProject] Failed to load team ${data[idx].id}:`, result.reason);
            return false;
          }
          return true;
        })
        .map(result => (result as PromiseFulfilledResult<any>).value);

      // Filter teams where user is admin (global admins OR team admins)
      const isGlobalAdmin = user?.role === 'admin';
      const userAdminTeams = teamDetails.filter(team =>
        isGlobalAdmin || team.members.some((m: TeamMember) => m.user_id === user?.id && m.role === 'admin')
      );
      console.info('[NewProject] User is admin of', userAdminTeams.length, 'teams',
                   isGlobalAdmin ? '(global admin)' : '');
      setAdminTeams(userAdminTeams);
    } catch (err) {
      console.error('[NewProject] Failed to load teams:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Project name is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const projectData: { name: string; description?: string; team_id?: number } = {
        name: name.trim(),
        description: description.trim() || undefined,
        team_id: teamId ? Number(teamId) : undefined
      };

      console.debug('[NewProject] Creating project:', projectData);
      const project = await createProject(projectData);
      console.info('[NewProject] Project created:', project.id);
      router.push(`/projects/${project.id}`);
    } catch (err) {
      console.error('[NewProject] Failed to create project:', err);
      setError('Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-6">Create New Project</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
            Project Name *
          </label>
          <input
            type="text"
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="Enter project name"
          />
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
            Description
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="Enter project description"
          />
        </div>

        <div>
          <label htmlFor="team" className="block text-sm font-medium text-gray-700 mb-2">
            Team (Optional)
          </label>
          <select
            id="team"
            value={teamId}
            onChange={(e) => setTeamId(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">Personal Project (No Team)</option>
            {adminTeams.map((team) => (
              <option key={team.id} value={team.id}>
                {team.name}
              </option>
            ))}
          </select>
          <p className="mt-1 text-sm text-gray-500">
            Only teams where you are an admin are shown
          </p>
        </div>

        <div className="flex gap-4">
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Creating...' : 'Create Project'}
          </button>
          <Link
            href="/"
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
