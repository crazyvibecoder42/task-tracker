'use client';

import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Trash2 } from 'lucide-react';
import type { ApiKey } from '@/lib/api';

interface ApiKeyListItemProps {
  apiKey: ApiKey;
  onRevoke: (keyId: number) => void;
}

export default function ApiKeyListItem({ apiKey, onRevoke }: ApiKeyListItemProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [revoking, setRevoking] = useState(false);

  const isExpired = apiKey.expires_at && new Date(apiKey.expires_at) < new Date();
  const isActive = apiKey.is_active && !isExpired;

  // Determine key status with proper precedence: Revoked > Expired > Active
  const getStatus = () => {
    if (!apiKey.is_active) return { label: 'Revoked', color: 'bg-red-100 text-red-800 border-red-200' };
    if (isExpired) return { label: 'Expired', color: 'bg-gray-100 text-gray-800 border-gray-200' };
    return { label: 'Active', color: 'bg-green-100 text-green-800 border-green-200' };
  };

  const status = getStatus();

  const handleRevoke = async () => {
    console.debug('[ApiKeyListItem] Revoking API key:', apiKey.id, apiKey.name);
    setRevoking(true);

    try {
      await onRevoke(apiKey.id);
      console.info('[ApiKeyListItem] API key revoked successfully:', apiKey.id);
    } catch (error) {
      console.error('[ApiKeyListItem] Failed to revoke API key:', error);
      alert('Failed to revoke API key. Please try again.');
    } finally {
      setRevoking(false);
      setShowConfirm(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    try {
      return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="p-4 bg-white border border-gray-200 rounded-lg hover:border-gray-300 transition-colors">
      <div className="flex items-start justify-between gap-4">
        {/* Key Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="font-semibold text-gray-900 truncate">
              {apiKey.name}
            </h3>
            <span
              className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${status.color}`}
            >
              {status.label}
            </span>
          </div>

          <div className="space-y-1 text-sm text-gray-600">
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Created:</span>
              <span>{formatDate(apiKey.created_at)}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Expires:</span>
              <span>
                {apiKey.expires_at ? (
                  <span className={isExpired ? 'text-red-600 font-medium' : ''}>
                    {formatDate(apiKey.expires_at)}
                  </span>
                ) : (
                  'Never'
                )}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Last used:</span>
              <span>{formatDate(apiKey.last_used_at)}</span>
            </div>
          </div>
        </div>

        {/* Revoke Button */}
        <div className="flex-shrink-0">
          {!showConfirm ? (
            <button
              onClick={() => {
                console.debug('[ApiKeyListItem] Revoke button clicked for:', apiKey.id);
                setShowConfirm(true);
              }}
              disabled={revoking}
              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
              title="Revoke API key"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={handleRevoke}
                disabled={revoking}
                className="px-3 py-1 bg-red-600 text-white text-sm rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                {revoking ? 'Revoking...' : 'Confirm'}
              </button>
              <button
                onClick={() => {
                  console.debug('[ApiKeyListItem] Revoke cancelled for:', apiKey.id);
                  setShowConfirm(false);
                }}
                disabled={revoking}
                className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded-md hover:bg-gray-200 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
