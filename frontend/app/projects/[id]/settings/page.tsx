'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import {
  getProject,
  getProjectMembers,
  getTeams,
  getTeam,
  transferProject,
  Project,
  Team,
  TeamMember,
  ProjectTeamTransfer
} from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

export default function ProjectSettings() {
  const params = useParams();
  const router = useRouter();
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [adminTeams, setAdminTeams] = useState<Team[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [transferring, setTransferring] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [canTransfer, setCanTransfer] = useState(false);

  // Ref to store redirect timeout for cleanup
  const redirectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Authentication guard - redirect to login if not authenticated
  useEffect(() => {
    console.debug('[ProjectSettings] Checking authentication status');
    if (!authLoading && !isAuthenticated) {
      console.info('[ProjectSettings] User not authenticated, redirecting to login');
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Load data when authenticated and projectId is available
  useEffect(() => {
    if (isAuthenticated && user?.id) {
      loadData();
    }
  }, [projectId, user?.id, isAuthenticated]);

  // Cleanup redirect timeout on unmount
  useEffect(() => {
    return () => {
      if (redirectTimeoutRef.current) {
        clearTimeout(redirectTimeoutRef.current);
      }
    };
  }, []);

  const loadData = async () => {
    console.debug('[ProjectSettings] Loading project and teams');
    setLoading(true);
    setError('');

    try {
      // Load project
      const projectData = await getProject(projectId);
      setProject(projectData);
      setSelectedTeamId(projectData.team_id ? String(projectData.team_id) : '');

      // Check if user is project owner
      await checkOwnerPermission();

      // Load admin teams
      await loadAdminTeams();
    } catch (err: any) {
      console.error('[ProjectSettings] Failed to load data:', err);
      setError(err.message || 'Failed to load project settings');
    } finally {
      setLoading(false);
    }
  };

  const checkOwnerPermission = async () => {
    console.debug('[ProjectSettings] Checking transfer permission');
    try {
      const members = await getProjectMembers(projectId);
      const userMembership = members.find(m => m.user_id === user?.id);
      const hasOwnerRole = userMembership?.role === 'owner';
      const isGlobalAdmin = user?.role === 'admin';
      const hasTransferPermission = hasOwnerRole || isGlobalAdmin;
      setCanTransfer(hasTransferPermission);
      console.info('[ProjectSettings] User can transfer:', hasTransferPermission, '(owner:', hasOwnerRole, 'admin:', isGlobalAdmin, ')');
    } catch (err) {
      console.error('[ProjectSettings] Failed to check permission:', err);
      setCanTransfer(false);
    }
  };

  const loadAdminTeams = async () => {
    console.debug('[ProjectSettings] Loading admin teams');
    try {
      const data = await getTeams();

      // Load full team details to check membership roles
      // Use allSettled to handle partial failures gracefully
      const teamDetailsPromises = data.map(team => getTeam(team.id));
      const teamDetailsResults = await Promise.allSettled(teamDetailsPromises);

      // Extract successful team fetches, log failures
      const teamDetails = teamDetailsResults
        .filter((result, idx) => {
          if (result.status === 'rejected') {
            console.error(`[ProjectSettings] Failed to load team ${data[idx].id}:`, result.reason);
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
      console.info('[ProjectSettings] User is admin of', userAdminTeams.length, 'teams',
                   isGlobalAdmin ? '(global admin)' : '');
      setAdminTeams(userAdminTeams);
    } catch (err) {
      console.error('[ProjectSettings] Failed to load teams:', err);
    }
  };

  const handleTransfer = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!project) return;

    // Validate that selection has changed
    const currentTeamId = project.team_id ? String(project.team_id) : '';
    if (selectedTeamId === currentTeamId) {
      setError('Please select a different team or "Personal Project"');
      return;
    }

    console.debug('[ProjectSettings] Transferring project to team:', selectedTeamId || 'personal');
    setTransferring(true);
    setError('');
    setSuccess('');

    try {
      const transferData: ProjectTeamTransfer = {
        team_id: selectedTeamId ? Number(selectedTeamId) : null
      };

      await transferProject(projectId, transferData);

      const targetName = selectedTeamId
        ? adminTeams.find(t => t.id === Number(selectedTeamId))?.name || 'team'
        : 'Personal Project';

      console.info('[ProjectSettings] Project transferred successfully to:', targetName);
      setSuccess(`Project transferred to ${targetName} successfully!`);

      // Clear any existing redirect timeout
      if (redirectTimeoutRef.current) {
        clearTimeout(redirectTimeoutRef.current);
      }

      // Redirect after 2 seconds
      redirectTimeoutRef.current = setTimeout(() => {
        router.push(`/projects/${projectId}`);
      }, 2000);
    } catch (err: any) {
      console.error('[ProjectSettings] Transfer failed:', err);

      // Parse error response - fetchApi throws JSON as text
      let errorDetail = '';
      try {
        const errorData = JSON.parse(err.message);
        errorDetail = errorData.detail || err.message;
      } catch {
        // If parsing fails, use the raw message
        errorDetail = err.message || 'Transfer failed';
      }

      console.debug('[ProjectSettings] Parsed error detail:', errorDetail);

      // Match error patterns to provide user-friendly messages
      if (errorDetail.toLowerCase().includes('permission') || errorDetail.toLowerCase().includes('forbidden')) {
        setError('Permission denied. You must be a project owner and an admin of the target team.');
      } else if (errorDetail.toLowerCase().includes('not found')) {
        setError('Project or team not found.');
      } else if (errorDetail.toLowerCase().includes('task owners') || errorDetail.toLowerCase().includes('cannot transfer')) {
        // Show validation errors as-is (they're already user-friendly)
        setError(errorDetail);
      } else {
        setError(errorDetail);
      }
    } finally {
      setTransferring(false);
    }
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  // Don't render anything if not authenticated (will redirect)
  if (!isAuthenticated || !user) {
    return null;
  }

  // Show loading state while fetching project data
  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-8">
        <p className="text-gray-500">Project not found</p>
        <Link href="/" className="text-indigo-600 hover:text-indigo-700">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl">
      <Link
        href={`/projects/${projectId}`}
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Project
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-8">Project Settings</h1>

      {/* Permission Guard */}
      {!canTransfer && (
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800 mb-6">
          Only project owners and global admins can modify settings.
        </div>
      )}

      {/* Current Team Display */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Current Team</h2>
        {project.team ? (
          <div className="flex items-center gap-2">
            <Link
              href={`/teams/${project.team.id}`}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-indigo-50 text-indigo-700 rounded-md hover:bg-indigo-100 border border-indigo-200"
            >
              {project.team.name}
            </Link>
          </div>
        ) : (
          <span className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-50 text-gray-700 rounded-md border border-gray-200">
            Personal Project
          </span>
        )}
      </div>

      {/* Team Transfer Form */}
      {canTransfer && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Transfer Project</h2>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 mb-4">
              {error}
            </div>
          )}

          {success && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-700 mb-4">
              {success}
            </div>
          )}

          <form onSubmit={handleTransfer} className="space-y-4">
            <div>
              <label htmlFor="team" className="block text-sm font-medium text-gray-700 mb-2">
                Transfer to Team
              </label>
              <select
                id="team"
                value={selectedTeamId}
                onChange={(e) => setSelectedTeamId(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                disabled={transferring}
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

            <button
              type="submit"
              disabled={transferring || selectedTeamId === (project.team_id ? String(project.team_id) : '')}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {transferring ? 'Transferring...' : 'Transfer Project'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
