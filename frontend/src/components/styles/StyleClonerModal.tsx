import React, { useState, useEffect } from 'react';
import { useFocusTrap } from '@/lib/useFocusTrap';

export interface StyleClonerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onClone: (file: File) => void;
}

export const StyleClonerModal: React.FC<StyleClonerModalProps> = ({ isOpen, onClose, onClone }) => {
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
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

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setReferenceFile(e.target.files[0]);
    }
  };

  const handleClone = () => {
    if (referenceFile) {
      onClone(referenceFile);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div 
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="style-cloner-title"
        className="bg-neutral-900 border border-neutral-700 w-full max-w-lg rounded-xl shadow-2xl p-6 flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-6">
          <h2 id="style-cloner-title" className="text-xl font-semibold text-neutral-100">Style Cloner</h2>
          <button 
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-100 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
            aria-label="Close modal"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <p className="text-neutral-400 text-sm mb-6">
          Upload a reference video (like a TikTok reel or YouTube Short). We'll analyze its pacing, transitions, and editing style to apply to your project.
        </p>

        <div className="flex flex-col border-2 border-dashed border-neutral-600 rounded-lg p-6 bg-neutral-800/50 mb-6">
          <label 
            className="flex flex-col items-center justify-center w-full h-40 cursor-pointer hover:bg-neutral-800 transition-colors rounded-lg focus-within:ring-2 focus-within:ring-blue-500"
          >
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              <svg className="w-10 h-10 mb-4 text-blue-500" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 4v16m8-8H4" />
              </svg>
              <p className="mb-2 text-sm text-neutral-300 font-medium">Select Reference Video</p>
              <p className="text-xs text-neutral-500">MP4 or MOV, up to 100MB</p>
            </div>
            <input type="file" className="sr-only" accept="video/*" onChange={handleFileUpload} aria-label="Select reference video" />
          </label>
        </div>

        {referenceFile && (
          <div className="flex items-center gap-3 p-3 bg-neutral-800 rounded mb-6 border border-neutral-700">
            <svg className="w-8 h-8 text-blue-400 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 6a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
            </svg>
            <div className="truncate flex-1">
              <p className="text-sm font-medium text-neutral-200 truncate">{referenceFile.name}</p>
              <p className="text-xs text-neutral-500">{(referenceFile.size / (1024 * 1024)).toFixed(2)} MB</p>
            </div>
            <button 
              className="text-neutral-400 hover:text-red-400 p-1"
              onClick={() => setReferenceFile(null)}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        )}

        <div className="flex justify-end gap-3 mt-auto">
          <button 
            className="px-4 py-2 text-sm font-medium text-neutral-300 bg-transparent hover:bg-neutral-800 rounded transition-colors"
            onClick={onClose}
          >
            Cancel
          </button>
          <button 
            className={`px-4 py-2 text-sm font-medium rounded transition-colors ${
              referenceFile 
                ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20' 
                : 'bg-neutral-800 text-neutral-500 cursor-not-allowed'
            }`}
            disabled={!referenceFile}
            onClick={handleClone}
          >
            Analyze & Clone Style
          </button>
        </div>
      </div>
    </div>
  );
};
