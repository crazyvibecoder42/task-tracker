'use client';

import { useState, useEffect, useRef } from 'react';
import { Check, Copy, AlertTriangle } from 'lucide-react';
import { copyToClipboard } from '@/lib/clipboard';

interface ApiKeyModalProps {
  apiKey: string;
  keyName: string;
  onClose: () => void;
}

export default function ApiKeyModal({ apiKey, keyName, onClose }: ApiKeyModalProps) {
  const [confirmed, setConfirmed] = useState(false);
  const [copied, setCopied] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  // Trap focus within modal
  useEffect(() => {
    console.debug('[ApiKeyModal] Mounting modal for key:', keyName);

    const handleKeyDown = (e: KeyboardEvent) => {
      // Disable Escape key until confirmed
      if (e.key === 'Escape' && !confirmed) {
        e.preventDefault();
        e.stopPropagation();
        console.debug('[ApiKeyModal] Escape key blocked - confirmation required');
      }

      // Tab key focus trap
      if (e.key === 'Tab' && modalRef.current) {
        const focusableElements = modalRef.current.querySelectorAll(
          'button:not([disabled]), input[type="checkbox"]'
        );
        const firstElement = focusableElements[0] as HTMLElement;
        const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement?.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement?.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      console.debug('[ApiKeyModal] Unmounting modal');
    };
  }, [confirmed, keyName]);

  const handleCopy = async () => {
    console.debug('[ApiKeyModal] Copy button clicked');
    const success = await copyToClipboard(apiKey);

    if (success) {
      setCopied(true);
      console.info('[ApiKeyModal] API key copied to clipboard successfully');

      // Reset copy indicator after 2 seconds
      setTimeout(() => {
        setCopied(false);
        console.debug('[ApiKeyModal] Copy indicator reset');
      }, 2000);
    } else {
      console.error('[ApiKeyModal] Failed to copy API key to clipboard');
      alert('Failed to copy to clipboard. Please copy the key manually.');
    }
  };

  const handleClose = () => {
    if (!confirmed) {
      console.debug('[ApiKeyModal] Close blocked - confirmation required');
      return;
    }

    console.info('[ApiKeyModal] Closing modal after confirmation');
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div
        ref={modalRef}
        className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Header */}
        <div className="mb-4">
          <h2 id="modal-title" className="text-xl font-bold text-gray-900 mb-2">
            API Key Created Successfully
          </h2>
          <p className="text-sm text-gray-600">
            Key Name: <span className="font-semibold">{keyName}</span>
          </p>
        </div>

        {/* Security Warning */}
        <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg mb-4">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-900 mb-1">
              This key will only be shown once. Save it securely.
            </p>
            <p className="text-xs text-amber-800">
              You won't be able to view this key again. If you lose it, you'll need to create a new one.
            </p>
          </div>
        </div>

        {/* API Key Display */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Your API Key
          </label>
          <div className="relative">
            <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm font-mono border border-gray-700">
              {apiKey}
            </pre>
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 p-2 bg-gray-800 hover:bg-gray-700 rounded-md transition-colors border border-gray-600"
              title="Copy to clipboard"
            >
              {copied ? (
                <Check className="w-4 h-4 text-green-400" />
              ) : (
                <Copy className="w-4 h-4 text-gray-300" />
              )}
            </button>
          </div>
          {copied && (
            <p className="text-xs text-green-600 mt-2 flex items-center gap-1">
              <Check className="w-3 h-3" />
              Copied to clipboard
            </p>
          )}
        </div>

        {/* Confirmation Checkbox */}
        <div className="mb-6">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => {
                setConfirmed(e.target.checked);
                console.debug('[ApiKeyModal] Confirmation checkbox:', e.target.checked);
              }}
              className="mt-1 w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-2 focus:ring-indigo-500"
            />
            <span className="text-sm text-gray-700">
              I have saved this key securely and understand that I won't be able to view it again
            </span>
          </label>
        </div>

        {/* Close Button */}
        <div className="flex justify-end">
          <button
            onClick={handleClose}
            disabled={!confirmed}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
