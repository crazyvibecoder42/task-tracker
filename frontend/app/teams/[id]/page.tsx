'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  FolderKanban,
  Plus,
  Shield,
  Trash2,
  Users,
  UserPlus,
  Edit3,
  Check,
  X
} from 'lucide-react';
import {
  getTeam,
  getAvailableUsersForTeam,
  addTeamMember,
  updateTeamMember,
  removeTeamMember,
  updateTeam,
  deleteTeam,
  TeamWithProjects,
  TeamMember,
  Author
} from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

export default function TeamDetail() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const teamId = Number(params.id);

  const [team, setTeam] = useState<TeamWithProjects | null>(null);
  const [authors, setAuthors] = useState<Author[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'members' | 'projects'>('members');

  // Add member form
  const [showAddMember, setShowAddMember] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedRole, setSelectedRole] = useState<'admin' | 'member'>('member');
  const [addMemberLoading, setAddMemberLoading] = useState(false);
  const [addMemberError, setAddMemberError] = useState('');

  // Edit team
  const [isEditingTeam, setIsEditingTeam] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editLoading, setEditLoading] = useState(false);

  // Compute admin status (must be declared before useEffect that depends on it)
  // Global admins OR team admins have admin privileges
  const isGlobalAdmin = user?.role === 'admin';
  const isTeamAdmin = team?.members.find(m => m.user_id === user?.id)?.role === 'admin';
  const isAdmin = isGlobalAdmin || isTeamAdmin;
  const isLastAdmin = team?.members.filter(m => m.role === 'admin').length === 1 && isTeamAdmin;

  useEffect(() => {
    loadTeam();
  }, [teamId]);

  // Only load authors when user is team admin (needed for Add Member dropdown)
  useEffect(() => {
    if (isAdmin) {
      loadAuthors();
    }
  }, [isAdmin]);

  const loadTeam = async () => {
    console.debug('[TeamDetail] Loading team:', teamId);
    try {
      const data = await getTeam(teamId);
      console.info('[TeamDetail] Team loaded:', data.name);
      setTeam(data);
      setEditName(data.name);
      setEditDescription(data.description || '');
      setError('');
    } catch (err) {
      console.error('[TeamDetail] Failed to load team:', err);
      setError('Failed to load team');
    } finally {
      setLoading(false);
    }
  };

  const loadAuthors = async () => {
    try {
      const data = await getAvailableUsersForTeam(teamId);
      setAuthors(data);
    } catch (err) {
      console.error('[TeamDetail] Failed to load available users:', err);
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId) {
      setAddMemberError('Please select a user');
      return;
    }

    console.debug('[TeamDetail] Adding member:', selectedUserId, selectedRole);
    setAddMemberLoading(true);
    setAddMemberError('');

    try {
      await addTeamMember(teamId, {
        user_id: Number(selectedUserId),
        role: selectedRole
      });
      console.info('[TeamDetail] Member added successfully');
      setShowAddMember(false);
      setSelectedUserId('');
      setSelectedRole('member');
      loadTeam();
      loadAuthors(); // Refresh available users after adding member
    } catch (err: any) {
      console.error('[TeamDetail] Failed to add member:', err);
      setAddMemberError(err.message || 'Failed to add member');
    } finally {
      setAddMemberLoading(false);
    }
  };

  const handlePromoteMember = async (member: TeamMember) => {
    if (!confirm(`Promote ${member.user?.name} to admin?`)) return;

    console.debug('[TeamDetail] Promoting member:', member.user_id);
    try {
      await updateTeamMember(teamId, member.user_id, { role: 'admin' });
      console.info('[TeamDetail] Member promoted successfully');
      loadTeam();
      loadAuthors(); // Refresh available users (though list shouldn't change)
    } catch (err) {
      console.error('[TeamDetail] Failed to promote member:', err);
      alert('Failed to promote member');
    }
  };

  const handleDemoteMember = async (member: TeamMember) => {
    if (isLastAdmin) {
      alert('Cannot demote the last admin. Promote another member to admin first.');
      return;
    }
    if (!confirm(`Demote ${member.user?.name} to member?`)) return;

    console.debug('[TeamDetail] Demoting member:', member.user_id);
    try {
      await updateTeamMember(teamId, member.user_id, { role: 'member' });
      console.info('[TeamDetail] Member demoted successfully');
      loadTeam();
      loadAuthors(); // Refresh available users (though list shouldn't change)
    } catch (err) {
      console.error('[TeamDetail] Failed to demote member:', err);
      alert('Failed to demote member');
    }
  };

  const handleRemoveMember = async (member: TeamMember) => {
    if (member.role === 'admin' && isLastAdmin) {
      alert('Cannot remove the last admin. Transfer admin role to another member first.');
      return;
    }
    if (!confirm(`Remove ${member.user?.name} from this team?`)) return;

    console.debug('[TeamDetail] Removing member:', member.user_id);
    try {
      await removeTeamMember(teamId, member.user_id);
      console.info('[TeamDetail] Member removed successfully');
      loadTeam();
      loadAuthors(); // Refresh available users (removed user should reappear)
    } catch (err) {
      console.error('[TeamDetail] Failed to remove member:', err);
      alert('Failed to remove member');
    }
  };

  const handleEditTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editName.trim()) {
      alert('Team name is required');
      return;
    }

    console.debug('[TeamDetail] Updating team:', editName);
    setEditLoading(true);

    try {
      await updateTeam(teamId, {
        name: editName.trim(),
        description: editDescription.trim() || undefined
      });
      console.info('[TeamDetail] Team updated successfully');
      setIsEditingTeam(false);
      loadTeam();
    } catch (err) {
      console.error('[TeamDetail] Failed to update team:', err);
      alert('Failed to update team');
    } finally {
      setEditLoading(false);
    }
  };

  const handleDeleteTeam = async () => {
    if (!confirm('Are you sure you want to delete this team? This will not delete projects.')) return;

    console.debug('[TeamDetail] Deleting team:', teamId);
    try {
      await deleteTeam(teamId);
      console.info('[TeamDetail] Team deleted successfully');
      router.push('/teams');
    } catch (err) {
      console.error('[TeamDetail] Failed to delete team:', err);
      alert('Failed to delete team');
    }
  };

  const availableUsers = authors.filter(
    author => !team?.members.some(m => m.user_id === author.id)
  );

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!team) {
    return (
      <div className="p-8">
        <p className="text-gray-500">Team not found</p>
        <Link href="/teams" className="text-indigo-600 hover:text-indigo-700">
          Back to Teams
        </Link>
      </div>
    );
  }

  return (
    <div className="p-8">
      <Link
        href="/teams"
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Teams
      </Link>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {/* Team Header */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {isEditingTeam ? (
              <form onSubmit={handleEditTeam} className="space-y-4">
                <div>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="text-2xl font-bold text-gray-900 w-full px-3 py-1 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <textarea
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    rows={2}
                    className="text-gray-600 w-full px-3 py-1 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    placeholder="Team description (optional)"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={editLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                  >
                    <Check className="w-4 h-4" />
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setIsEditingTeam(false);
                      setEditName(team.name);
                      setEditDescription(team.description || '');
                    }}
                    className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    <X className="w-4 h-4" />
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <>
                <h1 className="text-2xl font-bold text-gray-900">{team.name}</h1>
                {team.description && (
                  <p className="text-gray-600 mt-1">{team.description}</p>
                )}
                <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                  <span className="flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    {team.members.length} {team.members.length === 1 ? 'member' : 'members'}
                  </span>
                  <span className="flex items-center gap-1">
                    <FolderKanban className="w-4 h-4" />
                    {team.projects.length} {team.projects.length === 1 ? 'project' : 'projects'}
                  </span>
                </div>
              </>
            )}
          </div>
          {!isEditingTeam && (
            <div className="flex items-center gap-2">
              {isAdmin && (
                <>
                  <button
                    onClick={() => setIsEditingTeam(true)}
                    className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                    title="Edit team"
                  >
                    <Edit3 className="w-5 h-5" />
                  </button>
                  <button
                    onClick={handleDeleteTeam}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                    title="Delete team"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="border-b border-gray-200">
          <div className="flex gap-4 px-6">
            <button
              onClick={() => setActiveTab('members')}
              className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'members'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Members
            </button>
            <button
              onClick={() => setActiveTab('projects')}
              className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'projects'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Projects
            </button>
          </div>
        </div>

        {/* Members Tab */}
        {activeTab === 'members' && (
          <div className="p-6">
            {isAdmin && (
              <div className="mb-6">
                <button
                  onClick={() => setShowAddMember(!showAddMember)}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  <UserPlus className="w-5 h-5" />
                  Add Member
                </button>

                {showAddMember && (
                  <form onSubmit={handleAddMember} className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                    {addMemberError && (
                      <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                        {addMemberError}
                      </div>
                    )}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          User
                        </label>
                        <select
                          value={selectedUserId}
                          onChange={(e) => setSelectedUserId(e.target.value)}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                        >
                          <option value="">Select user</option>
                          {availableUsers.map((author) => (
                            <option key={author.id} value={author.id}>
                              {author.name} ({author.email})
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Role
                        </label>
                        <select
                          value={selectedRole}
                          onChange={(e) => setSelectedRole(e.target.value as 'admin' | 'member')}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                        >
                          <option value="member">Member</option>
                          <option value="admin">Admin</option>
                        </select>
                      </div>
                    </div>
                    <div className="mt-4 flex gap-2">
                      <button
                        type="submit"
                        disabled={addMemberLoading}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                      >
                        {addMemberLoading ? 'Adding...' : 'Add Member'}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setShowAddMember(false);
                          setSelectedUserId('');
                          setAddMemberError('');
                        }}
                        className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                )}
              </div>
            )}

            <div className="space-y-3">
              {team.members.length === 0 ? (
                <p className="text-center text-gray-500 py-8">No members yet</p>
              ) : (
                team.members.map((member) => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-indigo-50 rounded-lg">
                        <Users className="w-5 h-5 text-indigo-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{member.user?.name}</p>
                        <p className="text-sm text-gray-500">{member.user?.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-3 py-1 rounded-full text-sm font-medium ${
                          member.role === 'admin'
                            ? 'bg-purple-100 text-purple-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {member.role === 'admin' && <Shield className="w-3 h-3 inline mr-1" />}
                        {member.role}
                      </span>
                      {isAdmin && member.user_id !== user?.id && (
                        <>
                          {member.role === 'member' ? (
                            <button
                              onClick={() => handlePromoteMember(member)}
                              className="px-3 py-1 text-sm text-indigo-600 hover:bg-indigo-50 rounded-lg"
                            >
                              Promote
                            </button>
                          ) : (
                            <button
                              onClick={() => handleDemoteMember(member)}
                              className="px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
                              disabled={isLastAdmin}
                            >
                              Demote
                            </button>
                          )}
                          <button
                            onClick={() => handleRemoveMember(member)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                            disabled={member.role === 'admin' && isLastAdmin}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Projects Tab */}
        {activeTab === 'projects' && (
          <div className="p-6">
            {isAdmin && (
              <div className="mb-6">
                <Link
                  href={`/projects/new?team=${teamId}`}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 inline-flex"
                >
                  <Plus className="w-5 h-5" />
                  Create Project
                </Link>
              </div>
            )}

            <div className="space-y-3">
              {team.projects.length === 0 ? (
                <p className="text-center text-gray-500 py-8">No projects yet</p>
              ) : (
                team.projects.map((project) => (
                  <Link
                    key={project.id}
                    href={`/projects/${project.id}`}
                    className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-indigo-50 hover:border-indigo-200 transition-all"
                  >
                    <div className="p-2 bg-indigo-50 rounded-lg">
                      <FolderKanban className="w-5 h-5 text-indigo-600" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{project.name}</p>
                      {project.description && (
                        <p className="text-sm text-gray-500 mt-1">{project.description}</p>
                      )}
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
