import React, { useState, useEffect } from 'react';
import { useFocusTrap } from '@/lib/useFocusTrap';

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ShareModal: React.FC<ShareModalProps> = ({ isOpen, onClose }) => {
  const [password, setPassword] = useState('');
  const [isGenerated, setIsGenerated] = useState(false);
  const [link, setLink] = useState('');
  const modalRef = useFocusTrap(isOpen);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleGenerateLink = () => {
    // Mock generating link
    setLink(`https://review.aivideodirector.com/${Math.random().toString(36).substring(7)}`);
    setIsGenerated(true);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(link).catch(console.error);
    // Could add a toast notification here
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div 
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-modal-title"
        className="bg-gray-900 border border-gray-700 rounded-lg shadow-xl w-full max-w-md p-6"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-6">
          <h2 id="share-modal-title" className="text-xl font-semibold text-gray-100">Share for Review</h2>
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
            aria-label="Close modal"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Password Protection (Optional)
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              className="w-full bg-gray-800 border border-gray-700 rounded-md p-2 text-gray-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {!isGenerated ? (
            <button
              onClick={handleGenerateLink}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
            >
              Generate Review Link
            </button>
          ) : (
            <div className="space-y-3">
              <div className="p-3 bg-gray-800 border border-gray-700 rounded-md flex items-center justify-between">
                <span className="text-sm text-gray-300 truncate mr-2">{link}</span>
                <button
                  onClick={handleCopy}
                  className="text-blue-400 hover:text-blue-300 text-sm font-medium flex-shrink-0"
                >
                  Copy Link
                </button>
              </div>
              <button
                onClick={onClose}
                className="w-full bg-gray-700 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
              >
                Done
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
