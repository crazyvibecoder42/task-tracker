'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Plus, Key } from 'lucide-react';
import {
  changePassword,
  ChangePasswordRequest,
  createApiKey,
  listApiKeys,
  revokeApiKey,
  type ApiKey,
} from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import ApiKeyModal from '@/components/ApiKeyModal';
import ApiKeyListItem from '@/components/ApiKeyListItem';
import McpConfigGenerator from '@/components/McpConfigGenerator';

export default function Settings() {
  const router = useRouter();
  const { user, isAuthenticated, loading: authLoading } = useAuth();

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // API Keys state
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [latestRawKey, setLatestRawKey] = useState<string | null>(null);
  const [latestKeyId, setLatestKeyId] = useState<number | null>(null);
  const [latestKeyName, setLatestKeyName] = useState('');
  const [keyName, setKeyName] = useState('');
  const [expiryDays, setExpiryDays] = useState<string>('365');
  const [creatingKey, setCreatingKey] = useState(false);
  const [keyError, setKeyError] = useState('');

  // Authentication guard - redirect to login if not authenticated
  useEffect(() => {
    console.debug('[Settings] Checking authentication status');
    if (!authLoading && !isAuthenticated) {
      console.info('[Settings] User not authenticated, redirecting to login');
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Load API keys on mount
  useEffect(() => {
    if (isAuthenticated && user) {
      console.debug('[Settings] Loading API keys for user:', user.id);
      loadApiKeys();
    }
  }, [isAuthenticated, user]);

  // Load API keys from backend
  const loadApiKeys = async () => {
    setLoadingKeys(true);
    console.debug('[Settings] Fetching API keys');

    try {
      const keys = await listApiKeys();
      setApiKeys(keys);
      setKeyError(''); // Clear any stale errors on success
      console.info('[Settings] Loaded', keys.length, 'API keys');
    } catch (err: any) {
      console.error('[Settings] Failed to load API keys:', err);
      setKeyError('Failed to load API keys');
    } finally {
      setLoadingKeys(false);
    }
  };

  // Create new API key
  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    console.debug('[Settings] Creating API key:', keyName, 'expiry days:', expiryDays);
    setKeyError('');

    if (!keyName.trim()) {
      setKeyError('Key name is required');
      return;
    }

    setCreatingKey(true);

    try {
      const expiryDaysNum = expiryDays ? parseInt(expiryDays, 10) : undefined;

      if (expiryDaysNum !== undefined && (expiryDaysNum < 1 || expiryDaysNum > 365)) {
        setKeyError('Expiry days must be between 1 and 365');
        setCreatingKey(false);
        return;
      }

      const newKey = await createApiKey({
        name: keyName.trim(),
        expires_days: expiryDaysNum,
      });

      console.info('[Settings] API key created successfully:', newKey.id);

      // Store raw key temporarily for modal and config generator
      setLatestRawKey(newKey.key || null);
      setLatestKeyId(newKey.id);
      setLatestKeyName(keyName.trim());
      setShowKeyModal(true);

      // Clear form
      setKeyName('');
      setExpiryDays('365');

      // Reload keys list
      await loadApiKeys();
    } catch (err: any) {
      console.error('[Settings] Failed to create API key:', err);

      let errorDetail = '';
      try {
        const errorData = JSON.parse(err.message);
        errorDetail = errorData.detail || err.message;
      } catch {
        errorDetail = err.message || 'Failed to create API key';
      }

      setKeyError(errorDetail);
    } finally {
      setCreatingKey(false);
    }
  };

  // Close API key modal (keep raw key for config generator)
  const handleCloseKeyModal = () => {
    console.debug('[Settings] Closing API key modal');
    setShowKeyModal(false);
    // Keep latestRawKey for config generator until page refresh
  };

  // Revoke API key
  const handleRevokeKey = async (keyId: number) => {
    console.debug('[Settings] Revoking API key:', keyId);

    try {
      await revokeApiKey(keyId);
      console.info('[Settings] API key revoked successfully:', keyId);

      // Reload keys list
      await loadApiKeys();

      // Clear latest raw key ONLY if the revoked key matches the stored key ID
      if (latestKeyId !== null && keyId === latestKeyId) {
        console.debug('[Settings] Clearing latest raw key after revocation (revoked key ID matches stored key ID)');
        setLatestRawKey(null);
        setLatestKeyId(null);
        setLatestKeyName('');
      }
    } catch (err: any) {
      console.error('[Settings] Failed to revoke API key:', err);
      throw err; // Re-throw to be handled by ApiKeyListItem
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

  // Get role badge color
  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'editor':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'viewer':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // Client-side validation
  const validateForm = (): string | null => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      return 'All fields are required';
    }

    if (newPassword.length < 8) {
      return 'New password must be at least 8 characters';
    }

    if (newPassword !== confirmPassword) {
      return 'New password and confirm password must match';
    }

    return null;
  };

  // Handle password change
  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    console.debug('[Settings] Password change initiated');
    setError('');
    setSuccess('');

    // Client-side validation
    const validationError = validateForm();
    if (validationError) {
      console.info('[Settings] Validation failed:', validationError);
      setError(validationError);
      return;
    }

    setLoading(true);

    try {
      const requestData: ChangePasswordRequest = {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      };

      await changePassword(requestData);

      console.info('[Settings] Password changed successfully');
      setSuccess('Password changed successfully!');

      // Clear form fields on success
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      console.error('[Settings] Password change failed:', err);

      // Parse error response
      let errorDetail = '';
      try {
        const errorData = JSON.parse(err.message);
        errorDetail = errorData.detail || err.message;
      } catch {
        errorDetail = err.message || 'Failed to change password';
      }

      setError(errorDetail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-8">Settings</h1>

      {/* Profile Information (Read-only) */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Profile Information</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <div className="px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-900">
              {user.name}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <div className="px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-900">
              {user.email}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
            <div>
              <span
                className={`inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium border ${getRoleBadgeColor(
                  user.role
                )}`}
              >
                {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Password Change Form */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Change Password</h2>

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

        <form onSubmit={handlePasswordChange} className="space-y-4">
          <div>
            <label htmlFor="current-password" className="block text-sm font-medium text-gray-700 mb-2">
              Current Password
            </label>
            <input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              disabled={loading}
              placeholder="Enter your current password"
            />
          </div>

          <div>
            <label htmlFor="new-password" className="block text-sm font-medium text-gray-700 mb-2">
              New Password
            </label>
            <input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              disabled={loading}
              placeholder="Minimum 8 characters"
            />
          </div>

          <div>
            <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-700 mb-2">
              Confirm New Password
            </label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              disabled={loading}
              placeholder="Re-enter your new password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Changing Password...' : 'Change Password'}
          </button>
        </form>
      </div>

      {/* API Keys Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Key className="w-5 h-5 text-gray-700" />
          <h2 className="text-lg font-semibold text-gray-900">API Keys</h2>
        </div>

        <p className="text-sm text-gray-600 mb-6">
          Create API keys for programmatic access to the Task Tracker API. Use these keys with the MCP server
          or other integrations.
        </p>

        {keyError && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 mb-4">
            {keyError}
          </div>
        )}

        {/* Create API Key Form */}
        <form onSubmit={handleCreateApiKey} className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Create New API Key</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label htmlFor="key-name" className="block text-sm font-medium text-gray-700 mb-2">
                Key Name
              </label>
              <input
                id="key-name"
                type="text"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="e.g., MCP Server Key"
                disabled={creatingKey}
              />
            </div>

            <div>
              <label htmlFor="expiry-days" className="block text-sm font-medium text-gray-700 mb-2">
                Expires in (days)
              </label>
              <input
                id="expiry-days"
                type="number"
                min="1"
                max="365"
                value={expiryDays}
                onChange={(e) => setExpiryDays(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="365"
                disabled={creatingKey}
              />
              <p className="text-xs text-gray-500 mt-1">
                Leave blank for no expiration (1-365 days)
              </p>
            </div>
          </div>

          <button
            type="submit"
            disabled={creatingKey}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Plus className="w-4 h-4" />
            {creatingKey ? 'Creating...' : 'Create API Key'}
          </button>
        </form>

        {/* API Keys List */}
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Your API Keys</h3>

          {loadingKeys ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : apiKeys.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Key className="w-12 h-12 mx-auto mb-2 opacity-20" />
              <p className="text-sm">No API keys yet. Create one above to get started.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {apiKeys.map((apiKey) => (
                <ApiKeyListItem key={apiKey.id} apiKey={apiKey} onRevoke={handleRevokeKey} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* MCP Configuration Generator Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">MCP Configuration Generator</h2>

        <p className="text-sm text-gray-600 mb-6">
          Generate the <code className="bg-gray-100 px-1 rounded">.mcp.json</code> configuration file for
          the Task Tracker MCP server. This file connects Claude Code to your Task Tracker instance.
        </p>

        <McpConfigGenerator
          apiKeys={apiKeys}
          userId={user.id}
          latestRawKey={latestRawKey}
          latestKeyId={latestKeyId}
        />
      </div>

      {/* API Key Modal */}
      {showKeyModal && latestRawKey && (
        <ApiKeyModal
          apiKey={latestRawKey}
          keyName={latestKeyName}
          onClose={handleCloseKeyModal}
        />
      )}
    </div>
  );
}
