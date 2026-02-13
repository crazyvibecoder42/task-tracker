'use client';

import { useState, useEffect } from 'react';
import { Check, Copy, Download, ChevronDown, ChevronUp } from 'lucide-react';
import { copyToClipboard } from '@/lib/clipboard';
import type { ApiKey } from '@/lib/api';

interface McpConfigGeneratorProps {
  apiKeys: ApiKey[];
  userId: number;
  latestRawKey?: string | null;
  latestKeyId?: number | null;
}

export default function McpConfigGenerator({ apiKeys, userId, latestRawKey, latestKeyId }: McpConfigGeneratorProps) {
  const [apiUrl, setApiUrl] = useState('');
  const [selectedKeyId, setSelectedKeyId] = useState<number | null>(null);
  const [copiedConfig, setCopiedConfig] = useState(false);
  const [showInstructions, setShowInstructions] = useState(false);

  // Initialize API URL from environment variable
  useEffect(() => {
    const defaultUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:6001';
    console.debug('[McpConfigGenerator] Initializing with API URL:', defaultUrl);
    setApiUrl(defaultUrl);
  }, []);

  // Auto-select the latest key if available
  useEffect(() => {
    if (latestKeyId !== null && latestKeyId !== undefined && apiKeys.length > 0) {
      // Use the stored key ID directly instead of guessing
      console.debug('[McpConfigGenerator] Auto-selecting latest key:', latestKeyId);
      setSelectedKeyId(latestKeyId);
    }
  }, [latestKeyId, apiKeys]);

  // Get active API keys (not expired)
  const activeKeys = apiKeys.filter((key) => {
    const isExpired = key.expires_at && new Date(key.expires_at) < new Date();
    return key.is_active && !isExpired;
  });

  // Determine what key to use in the config
  const getConfigKey = (): string => {
    // If we have a raw key, verify it's still valid before using it
    if (latestRawKey && latestKeyId !== null) {
      const keyStillActive = activeKeys.some(key => key.id === latestKeyId);
      if (keyStillActive) {
        console.debug('[McpConfigGenerator] Using latest raw key in config (key ID:', latestKeyId, ')');
        return latestRawKey;
      } else {
        console.warn('[McpConfigGenerator] Latest key (ID:', latestKeyId, ') is no longer active/valid, using placeholder');
      }
    }

    // Otherwise show placeholder
    return '<PASTE_YOUR_API_KEY_HERE>';
  };

  // Generate MCP config JSON
  const generateConfig = () => {
    const config = {
      mcpServers: {
        'task-tracker': {
          command: 'python3',
          args: ['./mcp-server/stdio_server.py'],
          env: {
            TASK_TRACKER_API_URL: apiUrl,
            TASK_TRACKER_API_KEY: getConfigKey(),
            TASK_TRACKER_USER_ID: userId.toString(),
          },
        },
      },
    };

    return JSON.stringify(config, null, 2);
  };

  const configJson = generateConfig();

  const handleCopyConfig = async () => {
    console.debug('[McpConfigGenerator] Copying config to clipboard');
    const success = await copyToClipboard(configJson);

    if (success) {
      setCopiedConfig(true);
      console.info('[McpConfigGenerator] Config copied to clipboard successfully');

      setTimeout(() => {
        setCopiedConfig(false);
        console.debug('[McpConfigGenerator] Copy indicator reset');
      }, 2000);
    } else {
      console.error('[McpConfigGenerator] Failed to copy config to clipboard');
      alert('Failed to copy to clipboard. Please copy the config manually.');
    }
  };

  const handleDownloadConfig = () => {
    console.debug('[McpConfigGenerator] Downloading config as .mcp.json');
    const blob = new Blob([configJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '.mcp.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    console.info('[McpConfigGenerator] Config downloaded successfully');
  };

  return (
    <div className="space-y-4">
      {/* API URL Input */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          API URL
        </label>
        <input
          type="text"
          value={apiUrl}
          onChange={(e) => {
            console.debug('[McpConfigGenerator] API URL changed:', e.target.value);
            setApiUrl(e.target.value);
          }}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="http://localhost:6001"
        />
        <p className="text-xs text-gray-500 mt-1">
          The backend API URL where the task tracker is running
        </p>
      </div>

      {/* Generated Config */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Generated MCP Configuration
        </label>
        <div className="relative">
          <textarea
            readOnly
            value={configJson}
            className="w-full h-64 px-4 py-3 bg-gray-900 text-green-400 font-mono text-sm rounded-lg border border-gray-700 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          <div className="absolute top-2 right-2 flex gap-2">
            <button
              onClick={handleCopyConfig}
              className="p-2 bg-gray-800 hover:bg-gray-700 rounded-md transition-colors border border-gray-600"
              title="Copy entire config"
            >
              {copiedConfig ? (
                <Check className="w-4 h-4 text-green-400" />
              ) : (
                <Copy className="w-4 h-4 text-gray-300" />
              )}
            </button>
            <button
              onClick={handleDownloadConfig}
              className="p-2 bg-gray-800 hover:bg-gray-700 rounded-md transition-colors border border-gray-600"
              title="Download as .mcp.json"
            >
              <Download className="w-4 h-4 text-gray-300" />
            </button>
          </div>
        </div>
        {copiedConfig && (
          <p className="text-xs text-green-600 mt-2 flex items-center gap-1">
            <Check className="w-3 h-3" />
            Config copied to clipboard
          </p>
        )}
        {!latestRawKey && (
          <p className="text-xs text-amber-600 mt-2">
            Replace <code className="bg-gray-100 px-1 rounded">&lt;PASTE_YOUR_API_KEY_HERE&gt;</code> with your actual API key
          </p>
        )}
      </div>

      {/* Setup Instructions (Expandable) */}
      <div className="border border-gray-200 rounded-lg">
        <button
          onClick={() => {
            console.debug('[McpConfigGenerator] Toggling instructions:', !showInstructions);
            setShowInstructions(!showInstructions);
          }}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 transition-colors"
        >
          <span className="font-medium text-gray-900">Setup Instructions</span>
          {showInstructions ? (
            <ChevronUp className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-500" />
          )}
        </button>

        {showInstructions && (
          <div className="p-4 pt-0 space-y-3 text-sm text-gray-700">
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">1. Create API Key</h4>
              <p>
                If you haven't already, create an API key using the form above. Make sure to save it securely
                as it will only be shown once.
              </p>
            </div>

            <div>
              <h4 className="font-semibold text-gray-900 mb-2">2. Download or Copy Configuration</h4>
              <p>
                Click the "Download" button to save the configuration as <code className="bg-gray-100 px-1 rounded">.mcp.json</code>,
                or copy it using the "Copy" button.
              </p>
            </div>

            <div>
              <h4 className="font-semibold text-gray-900 mb-2">3. Place Configuration File</h4>
              <p>
                Save the <code className="bg-gray-100 px-1 rounded">.mcp.json</code> file in your project root directory
                or in <code className="bg-gray-100 px-1 rounded">~/.claude/</code> directory.
              </p>
            </div>

            <div>
              <h4 className="font-semibold text-gray-900 mb-2">4. Install MCP Server</h4>
              <p className="mb-2">
                Make sure you have the Task Tracker MCP server installed:
              </p>
              <pre className="bg-gray-900 text-green-400 p-3 rounded-lg overflow-x-auto text-xs">
                cd mcp-server{'\n'}
                pip install -r requirements.txt
              </pre>
            </div>

            <div>
              <h4 className="font-semibold text-gray-900 mb-2">5. Restart Claude Code</h4>
              <p>
                After updating the configuration, restart Claude Code for the changes to take effect.
              </p>
            </div>

            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-blue-900 text-xs">
                <strong>Note:</strong> The MCP server requires Python 3.8+ and the MCP SDK.
                See the project README for detailed installation instructions.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
